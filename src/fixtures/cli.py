from __future__ import annotations

import pandas as pd
from datetime import date as Datetype
from datetime import datetime
from pathlib import Path
import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import SessionLocal,engine
from src.models import Team, League, Match
import os
from sqlalchemy import create_engine, text
from src.config import settings


app = typer.Typer(help="Alta masiva de fixtures (partidos futuros)")

from enum import Enum

class IfExists(str, Enum):
    skip = "skip"
    update = "update"
    error = "error"


# ----------------- helpers -----------------

def _read_csv_flex(path: str) -> pd.DataFrame:
    """
    Lee el CSV detectando separador y normaliza cabeceras.
    Acepta: (date,home,away) o (Date,HomeTeam,AwayTeam), con o sin BOM,
    con espacios y mayúsculas/minúsculas varias.
    """
    # Detecta separador automáticamente (Excel ES suele usar ';')
    df = pd.read_csv(path, sep=None, engine="python", dtype=str)
    # normaliza headers
    cols = [c.replace("\ufeff", "").strip().lower() for c in df.columns]
    df.columns = cols
    # renombres aceptados -> estándar
    mapping = {
        "hometeam": "home",
        "awayteam": "away",
        "local": "home",
        "visitante": "away",
        "home team": "home",
        "away team": "away",
    }
    df = df.rename(columns=mapping)
    # obligatorias
    if not {"date", "home", "away"}.issubset(df.columns):
        raise typer.BadParameter(
            f"El CSV debe tener columnas (date,home,away) o (Date,HomeTeam,AwayTeam). "
            f"Cabeceras leídas: {list(df.columns)}"
        )
    return df[["date", "home", "away"]]

def _parse_date(s: str, *, dayfirst: bool) -> DateType | None:
    dt = pd.to_datetime(s, dayfirst=dayfirst, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date()

def _get_or_create_league(s, name: str) -> int:
    row = s.execute(select(League).where(League.name == name)).scalar_one_or_none()
    if row:
        return row.id
    lg = League(name=name)
    s.add(lg)
    s.flush()
    return lg.id

def _get_or_create_team(s, name: str, league_id: int) -> int:
    tid = _get_team_id(s, name)
    if tid:
        return tid
    tm = Team(name=name, league_id=league_id)
    s.add(tm)
    s.flush()
    return tm.id

def _get_team_id(s, name: str) -> int | None:
    row = s.execute(select(Team).where(Team.name == name)).scalar_one_or_none()
    return row.id if row else None

def _ensure_team(s: Session, name: str, league: str | None) -> int:
    tid = _find_team_id(s, name)
    if tid is not None:
        return tid
    if not league:
        raise typer.BadParameter(f"Equipo '{name}' no existe. Pasa --league para crearlo automáticamente.")
    lid = _get_or_create_league(s, league)
    t = Team(name=name.strip(), league_id=lid)
    s.add(t)
    s.flush()
    return t.id

def _upsert_match_basic(
    s: Session,
    dt: DateType,
    home_id: int,
    away_id: int,
    season_id: int | None,
    if_exists: str,
) -> str:
    """Crea el partido si no existe; si existe respeta la política if_exists.
    Devuelve 'created' | 'updated' | 'skipped'"""
    q = (
        s.query(Match)
        .filter(
            Match.date == dt,
            Match.home_team_id == home_id,
            Match.away_team_id == away_id,
        )
        .one_or_none()
    )

    if q:
        if if_exists == "skip":
            return "skipped"
        if if_exists == "error":
            raise typer.BadParameter(
                f"Fixture duplicado {dt} H={home_id} vs A={away_id}"
            )
        # update: hoy solo actualizamos season_id si viene
        if season_id is not None and q.season_id != season_id:
            q.season_id = season_id
            s.flush()
            return "updated"
        return "skipped"

    m = Match(
        season_id=season_id,
        date=dt,
        home_team_id=home_id,
        away_team_id=away_id,
        # los goles/resultados se cargarán cuando se juegue
        home_goals=None,
        away_goals=None,
        fulltime_result=None,
        halftime_homegoal=None,
        halftime_awaygoal=None,
        halftime_result=None,
        referee=None,
    )
    s.add(m)
    # no hace falta flush() para devolver id aquí
    return "created"

def _upsert_match(s, date_: datetime, home_id: int, away_id: int, season_id: int | None) -> int:
    existing = (
        s.execute(
            select(Match).where(
                Match.date == date_.date(),
                Match.home_team_id == home_id,
                Match.away_team_id == away_id,
            )
        ).scalar_one_or_none()
    )
    if existing:
        if season_id is not None:
            existing.season_id = season_id
        s.flush()
        return existing.id
    mt = Match(
        season_id=season_id,
        date=date_.date(),
        home_team_id=home_id,
        away_team_id=away_id,
    )
    s.add(mt)
    s.flush()
    return mt.id


_IF_EXISTS_CHOICES  = {"skip", "update", "error"}

def _norm_if_exists(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in _IF_EXISTS_CHOICES:
        raise typer.BadParameter(
            f"if-exists debe ser uno de: {', '.join(sorted(_IF_EXISTS_CHOICES))}"
        )
    return v



# ----------------- comandos -----------------

@app.command()
def add(
    date_str: str = typer.Argument(..., help="Fecha (ej: 2025-05-25)"),
    home: str = typer.Argument(..., help="Nombre exacto equipo local"),
    away: str = typer.Argument(..., help="Nombre exacto equipo visitante"),
    season_id: int = typer.Option(..., help="Season ID"),
    if_exists: IfExists = typer.Option("skip", case_sensitive=False, help="skip|update|error"),
    create_teams: bool = typer.Option(False, help="Crear equipos si no existen"),
    league: str | None = typer.Option(None, help="Liga para crear equipos (si create_teams)"),
    dayfirst: bool = typer.Option(False, help="True si usas dd/mm/yyyy"),
):
    """Crea/actualiza un partido."""
    d = _parse_date(date_str, dayfirst)

    with SessionLocal() as s:
        if create_teams:
            hid = _ensure_team(s, home, league)
            aid = _ensure_team(s, away, league)
        else:
            hid = _find_team_id(s, home)
            aid = _find_team_id(s, away)
            if hid is None:
                raise typer.BadParameter(f"Equipo no encontrado: {home}")
            if aid is None:
                raise typer.BadParameter(f"Equipo no encontrado: {away}")

        st, mid = _upsert_match_basic(s, d, hid, aid, season_id, if_exists)
        s.commit()
        typer.echo(f"{st.upper()}: match_id={mid} {home} vs {away} ({d})")


@app.command("bulk")
def bulk(
    csv: str = typer.Argument(..., help="CSV con columnas: date,home,away (o home_team,away_team)"),
    season_id: int = typer.Option(..., help="Season ID que asignar a los partidos"),
    league: str = typer.Option("Premier League", help="(Informativo) Liga de los equipos"),
    create_teams: bool = typer.Option(False, help="(IGNORADO) No se crean equipos, deben existir"),
    dayfirst: bool = typer.Option(True, "--dayfirst/--no-dayfirst", help="True si el CSV trae dd/mm/yyyy"),
):
    """
    Carga masivamente fixtures (fecha + nombres de equipos) y hace upsert en matches.
    Los equipos deben existir previamente en la BD.
    """
    # 1) Leer CSV (usa tu helper existente)
    df = _read_csv_flex(csv)

    # 2) Normalizar columnas
    df.columns = df.columns.str.strip().str.lower()
    # Unificar a home_team / away_team
    if {"home_team", "away_team"}.issubset(df.columns):
        pass
    elif {"home", "away"}.issubset(df.columns):
        df = df.rename(columns={"home": "home_team", "away": "away_team"})
    else:
        raise ValueError(
            "El CSV debe traer columnas 'home_team' y 'away_team' (o 'home' y 'away'). "
            f"Columnas actuales: {list(df.columns)}"
        )

    # 3) Parsear fecha
    df["date"] = pd.to_datetime(df["date"], dayfirst=dayfirst, errors="coerce")

    # 4) Validación de equipos contra BD
    from sqlalchemy import create_engine, text
    from src.config import settings

    def _norm(s: str) -> str:
        """Normaliza nombre de equipo: lowercase, sin espacios extras, sin acentos"""
        if not s:
            return ""
        
        import unicodedata
        
        # Lowercase y strip
        s = s.strip().lower()
        
        # Remover acentos
        s = ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Normalizar espacios múltiples
        s = ' '.join(s.split())
        
        return s

    engine = create_engine(settings.sqlalchemy_url)

    with engine.connect() as conn:
        # Obtener league_id del season
        league_query = text("""
            SELECT league_id FROM seasons WHERE id = :season_id
        """)
        league_id = conn.execute(league_query, {"season_id": season_id}).scalar()
        
        if not league_id:
            raise ValueError(f"season_id={season_id} no tiene league_id asignado")
        
        # Cargar equipos de esa liga
        query = text("""
            SELECT DISTINCT t.id, t.name
            FROM teams t
            JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            JOIN seasons s ON s.id = m.season_id
            WHERE s.league_id = :league_id
            ORDER BY t.name
        """)
        rows = conn.execute(query, {"league_id": league_id}).fetchall()
        
    team_id_by_name = {_norm(name): tid for tid, name in rows}

    # ═══════════════════════════════════════════════════════════
    # DEBUG: Mostrar mapeo completo
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print(f"  MAPEO DE EQUIPOS (Total: {len(team_id_by_name)})")
    print("="*70)
    for name, tid in sorted(team_id_by_name.items()):
        print(f"  '{name}' → {tid}")
    print("="*70 + "\n")

    # DEBUG: Verificar equipos específicos del CSV
    test_teams = ['villarreal', 'mallorca', 'real sociedad', 'alaves']
    print("🔍 VERIFICACIÓN DE EQUIPOS DEL CSV:")
    for team in test_teams:
        if team in team_id_by_name:
            print(f"  ✅ '{team}' → ID {team_id_by_name[team]}")
        else:
            print(f"  ❌ '{team}' → NO ENCONTRADO")
            # Buscar similares
            similares = [k for k in team_id_by_name.keys() if team[:4] in k or k[:4] in team]
            if similares:
                print(f"     Similares: {similares}")
    print("="*70 + "\n")
    # ═══════════════════════════════════════════════════════════
    
    print(f"\n✅ {len(team_id_by_name)} equipos de {league} mapeados")
    print(f"   Liga ID: {league_id}, Season ID: {season_id}")

    unknown = []
    for idx, row in df.iterrows():
        h = team_id_by_name.get(_norm(row["home_team"]))
        a = team_id_by_name.get(_norm(row["away_team"]))
        if h is None or a is None:
            unknown.append((idx, row["home_team"], row["away_team"], row["date"]))

    if unknown:
        lines = "\n".join([f"- fila {i}: {h} vs {a} ({d})" for i, h, a, d in unknown])
        raise ValueError(
            "Se encontraron equipos no registrados en la base de datos.\n"
            "Corrige los nombres en el CSV y vuelve a ejecutar el bulk:\n" + lines
        )

    # 5) Mapear IDs para el insert
    df["home_team_id"] = df["home_team"].apply(lambda x: team_id_by_name[_norm(x)])
    df["away_team_id"] = df["away_team"].apply(lambda x: team_id_by_name[_norm(x)])

    # (Compatibilidad por si en algún lugar viejo se usa 'home'/'away')
    if "home" not in df.columns:
        df["home"] = df["home_team"]
    if "away" not in df.columns:
        df["away"] = df["away_team"]

    # 6) Upsert en matches usando IDs (sin crear equipos)
    inserted = updated = skipped = 0
    with SessionLocal() as s:
        for _, r in df.iterrows():
            dt = r["date"]
            if pd.isna(dt):
                skipped += 1
                continue

            home_id = int(r["home_team_id"])
            away_id = int(r["away_team_id"])

            # ¿existe ya el match?
            existing = (
                s.execute(
                    select(Match.id).where(
                        Match.date == dt.date(),
                        Match.home_team_id == home_id,
                        Match.away_team_id == away_id,
                    )
                ).scalar_one_or_none()
            )

            _ = _upsert_match(s, dt, home_id, away_id, season_id)
            if existing:
                updated += 1
            else:
                inserted += 1

        s.commit()

    typer.echo(
        f"OK bulk fixtures → matches | insertados={inserted}, actualizados={updated}, omitidos={skipped}"
    )



@app.command("round")
def add_round(
    date_str: str = typer.Argument(..., help="Fecha común (ej: 2025-05-25)"),
    season_id: int = typer.Option(..., help="Season ID"),
    pairs: list[str] = typer.Option(..., help='Parejas "Local,Visitante" repetibles', metavar='"Local,Visitante"'),
    if_exists: IfExists = typer.Option("skip", case_sensitive=False),
    create_teams: bool = typer.Option(False, help="Crear equipos si no existen"),
    league: str | None = typer.Option(None, help="Liga para crear equipos (si create_teams=True)"),
    dayfirst: bool = typer.Option(False, help="True si dd/mm/yyyy"),
):
    """Crea una jornada completa en una línea."""
    d = _parse_date(date_str, dayfirst)
    ins = upd = skip = 0

    with SessionLocal() as s:
        for p in pairs:
            try:
                home_name, away_name = [x.strip() for x in p.split(",", 1)]
            except ValueError:
                raise typer.BadParameter(f"Par inválido: {p!r}. Usa 'Local,Visitante'.")

            if create_teams:
                hid = _ensure_team(s, home_name, league)
                aid = _ensure_team(s, away_name, league)
            else:
                hid = _find_team_id(s, home_name)
                aid = _find_team_id(s, away_name)
                if hid is None or aid is None:
                    raise typer.BadParameter(f"Equipo no encontrado: {p!r}")

            st, _mid = _upsert_match_basic(s, d, hid, aid, season_id, if_exists)
            if st == "inserted":
                ins += 1
            elif st == "updated":
                upd += 1
            else:
                skip += 1

        s.commit()

    typer.echo(f"OK round {d}: inserted={ins} updated={upd} skipped={skip}")


@app.command("derive-weinston-picks")
def derive_weinston_picks(
    season_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
):
    sql = """
    UPDATE weinston_predictions wp
    SET
      result_1x2 = CASE
                     WHEN wp.local_goals IS NULL OR wp.away_goals IS NULL THEN NULL
                     WHEN wp.local_goals >  wp.away_goals THEN 1
                     WHEN wp.local_goals <  wp.away_goals THEN 2
                     ELSE 0
                   END,
      over_2 = CASE
                 WHEN wp.local_goals IS NULL OR wp.away_goals IS NULL THEN NULL
                 WHEN (wp.local_goals + wp.away_goals) > 2.5 THEN 'OVER' ELSE 'UNDER'
               END,
      both_score = CASE
                     WHEN wp.local_goals IS NULL OR wp.away_goals IS NULL THEN NULL
                     WHEN wp.local_goals >= 0.5 AND wp.away_goals >= 0.5 THEN 'YES' ELSE 'NO'
                   END
    FROM matches m
    WHERE m.id = wp.match_id
      AND m.season_id = :season_id
      AND (:date_from IS NULL OR m.date >= :date_from::date)
      AND (:date_to   IS NULL OR m.date <= :date_to::date);
    """
    with engine.begin() as con:
        con.execute(text(sql), {"season_id": season_id, "date_from": date_from, "date_to": date_to})
    typer.echo("Picks de Weinston derivados desde goles esperados.")


if __name__ == "__main__":
    app()
