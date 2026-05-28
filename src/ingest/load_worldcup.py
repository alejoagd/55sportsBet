"""
Ingesta de datos históricos de la FIFA World Cup desde WorldCupMatches.csv (Kaggle).

Columnas del CSV:
  Year, Datetime, Stage, Stadium, City,
  Home Team Name, Home Team Goals, Away Team Goals, Away Team Name,
  Win conditions, Attendance, Half-time Home Goals, Half-time Away Goals,
  Referee, Assistant 1, Assistant 2, RoundID, MatchID,
  Home Team Initials, Away Team Initials

Puebla:
  - leagues  (1 registro: "FIFA World Cup")
  - seasons  (1 por cada año de copa: 1930, 1934, ..., 2022)
  - teams    (selecciones nacionales)
  - matches  (resultados históricos)

Uso:
  python -m src.ingest.load_worldcup run data/raw/worldcup/WorldCupMatches.csv
"""
from __future__ import annotations

import pandas as pd
import typer
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.models import League, Team, Match

app = typer.Typer(help="Cargar datos históricos de la FIFA World Cup")

LEAGUE_NAME = "FIFA World Cup"


def _get_or_create_league(s: Session) -> int:
    row = s.execute(select(League).where(League.name == LEAGUE_NAME)).scalar_one_or_none()
    if row:
        return row.id
    league = League(name=LEAGUE_NAME)
    s.add(league)
    s.flush()
    print(f"  Liga creada: {LEAGUE_NAME} (id={league.id})")
    return league.id


def _get_or_create_season(s: Session, league_id: int, year: int) -> int:
    row = s.execute(
        text("SELECT id FROM seasons WHERE league_id = :lid AND year_start = :ys"),
        {"lid": league_id, "ys": year}
    ).fetchone()
    if row:
        return row.id
    s.execute(
        text("""
            INSERT INTO seasons (league_id, year_start, year_end)
            VALUES (:lid, :ys, :ye)
        """),
        {"lid": league_id, "ys": year, "ye": year}
    )
    s.flush()
    row = s.execute(
        text("SELECT id FROM seasons WHERE league_id = :lid AND year_start = :ys"),
        {"lid": league_id, "ys": year}
    ).fetchone()
    print(f"  Temporada creada: World Cup {year} (id={row.id})")
    return row.id


def _get_or_create_team(s: Session, name: str, league_id: int) -> int:
    name = name.strip()
    row = s.execute(select(Team).where(Team.name == name)).scalars().first()
    if row:
        return row.id
    team = Team(name=name, league_id=league_id)
    s.add(team)
    s.flush()
    return team.id


def _parse_date(datetime_str: str, year: int):
    """Parsea la fecha del CSV (ej: '13 Jul 1930 - 15:00')."""
    if pd.isna(datetime_str):
        return None
    try:
        dt_clean = str(datetime_str).strip().split(" - ")[0].strip()
        for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(dt_clean, fmt).date()
            except ValueError:
                continue
        # Fallback: usar solo el año
        return datetime(year, 6, 1).date()
    except Exception:
        return datetime(year, 6, 1).date()


def _to_int(val):
    try:
        v = int(float(val))
        return v if v >= 0 else None
    except Exception:
        return None


def _fulltime_result(hg, ag):
    if hg is None or ag is None:
        return None
    if hg > ag:
        return "H"
    elif ag > hg:
        return "A"
    return "D"


def _halftime_result(hg, ag):
    if hg is None or ag is None:
        return None
    if hg > ag:
        return "H"
    elif ag > hg:
        return "A"
    return "D"


@app.command()
def run(
    csv_path: str = typer.Argument(..., help="Ruta al WorldCupMatches.csv"),
    dry_run: bool = typer.Option(False, help="Solo mostrar estadísticas sin insertar"),
):
    df = pd.read_csv(csv_path, encoding="utf-8")
    print(f"\n📂 Archivo cargado: {csv_path}")
    print(f"   Filas totales: {len(df)}")
    print(f"   Columnas: {list(df.columns)}\n")

    # Normalizar nombres de columnas (quitar espacios)
    df.columns = [c.strip() for c in df.columns]

    # Filtrar filas vacías (sin equipos)
    df = df.dropna(subset=["Home Team Name", "Away Team Name"])
    print(f"   Filas con datos válidos: {len(df)}\n")

    if dry_run:
        print("🔍 DRY RUN — no se insertará nada")
        years = sorted(df["Year"].dropna().unique())
        print(f"   Años de Copas del Mundo encontrados: {years}")
        return

    inserted = 0
    updated = 0
    errors = 0

    with SessionLocal() as s:
        league_id = _get_or_create_league(s)
        season_cache: dict[int, int] = {}
        team_cache: dict[str, int] = {}

        for _, row in df.iterrows():
            try:
                year = int(row["Year"])
                home_name = str(row["Home Team Name"]).strip()
                away_name = str(row["Away Team Name"]).strip()

                # Obtener/crear temporada
                if year not in season_cache:
                    season_cache[year] = _get_or_create_season(s, league_id, year)
                season_id = season_cache[year]

                # Obtener/crear equipos
                if home_name not in team_cache:
                    team_cache[home_name] = _get_or_create_team(s, home_name, league_id)
                if away_name not in team_cache:
                    team_cache[away_name] = _get_or_create_team(s, away_name, league_id)

                home_id = team_cache[home_name]
                away_id = team_cache[away_name]

                match_date = _parse_date(row.get("Datetime"), year)

                home_goals = _to_int(row.get("Home Team Goals"))
                away_goals = _to_int(row.get("Away Team Goals"))
                ht_home = _to_int(row.get("Half-time Home Goals"))
                ht_away = _to_int(row.get("Half-time Away Goals"))
                referee = str(row.get("Referee", "")).strip() or "Sin arbitro"

                # Buscar partido existente
                existing = s.execute(
                    select(Match).where(
                        Match.date == match_date,
                        Match.home_team_id == home_id,
                        Match.away_team_id == away_id,
                    )
                ).scalars().first()

                payload = {
                    "season_id": season_id,
                    "date": match_date,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "fulltime_result": _fulltime_result(home_goals, away_goals),
                    "halftime_homegoal": ht_home,
                    "halftime_awaygoal": ht_away,
                    "halftime_result": _halftime_result(ht_home, ht_away),
                    "referee": referee,
                }

                if existing:
                    for k, v in payload.items():
                        if v is not None:
                            setattr(existing, k, v)
                    updated += 1
                else:
                    s.add(Match(**payload))
                    inserted += 1

            except Exception as e:
                print(f"  ⚠️  Error en fila {_}: {e}")
                errors += 1
                continue

        s.commit()

    print(f"\n✅ Carga completada:")
    print(f"   Partidos insertados : {inserted}")
    print(f"   Partidos actualizados: {updated}")
    print(f"   Errores             : {errors}")
    print(f"   Temporadas creadas  : {len(season_cache)}")
    print(f"   Equipos cargados    : {len(team_cache)}")


if __name__ == "__main__":
    app()
