"""
Ingesta UNIFICADA desde un CSV (estilo football-data.co.uk: Div, Date, Time, HomeTeam,
AwayTeam, FTHG, FTAG, HTHG, HTAG, FTR, HTR, Referee, HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR, ...).

Puebla varias tablas:
- leagues (si no existe)
- teams (con league_id)
- matches (incluye home/away_goals, FTR, HTHG/HTAG/HTR, referee, season_id opcional)
- match_stats (stats de disparos, faltas, corners, tarjetas y totales)

Uso:
  python -m src.ingest.load_unified run data/raw/"E0 (61).csv" --league "Premier League" --div E0 --season-id 2024
"""
from __future__ import annotations
import pandas as pd
import typer
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.models import League, Team, Match, MatchStats

app = typer.Typer(help="Cargar un CSV unificado y poblar multiples tablas")

# Mapeo directo CSV -> columnas de match_stats (goles van a matches)
STATS_MAP = {
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellow_cards",
    "AY": "away_yellow_cards",
    "HR": "home_red_cards",
    "AR": "away_red_cards",
}

# Totales computados desde columnas del CSV
TOTALS_FORMULAS = {
    "total_goals": ("FTHG", "FTAG"),
    "total_shots": ("HS", "AS"),
    "total_shots_on_target": ("HST", "AST"),
    "total_fouls": ("HF", "AF"),
    "total_corners": ("HC", "AC"),
    "total_cardshome": ("HY", "HR"),
    "total_cardsaway": ("AY", "AR"),
}


def _get_or_create_league(s: Session, name: str) -> int:
    row = s.execute(select(League).where(League.name == name)).scalar_one_or_none()
    if row:
        return row.id
    lg = League(name=name)
    s.add(lg)
    s.flush()
    return lg.id


def _get_or_create_team(s: Session, name: str, league_id: int) -> int:
    row = s.execute(select(Team).where(Team.name == name)).scalar_one_or_none()
    if row:
        if getattr(row, "league_id", None) is None:
            row.league_id = league_id
            s.flush()
        return row.id
    tm = Team(name=name, league_id=league_id)
    s.add(tm)
    s.flush()
    return tm.id


def _to_int(x):
    try:
        return int(x)
    except Exception:
        return None


def _upsert_match(s: Session, date: datetime, home_id: int, away_id: int, row: dict, season_id: int | None) -> int:
    existing = (
        s.execute(
            select(Match).where(
                Match.date == date.date(),
                Match.home_team_id == home_id,
                Match.away_team_id == away_id,
            )
        ).scalar_one_or_none()
    )

    payload = {
        "season_id": season_id,
        "date": date.date(),
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_goals": _to_int(row.get("FTHG")),
        "away_goals": _to_int(row.get("FTAG")),
        "fulltime_result": (str(row.get("FTR")).strip() if pd.notna(row.get("FTR")) else None),
        "halftime_homegoal": _to_int(row.get("HTHG")),
        "halftime_awaygoal": _to_int(row.get("HTAG")),
        "halftime_result": (str(row.get("HTR")).strip() if pd.notna(row.get("HTR")) else None),
        "referee": (str(row.get("Referee")).strip() if pd.notna(row.get("Referee")) else None),
    }

    if existing:
        for k, v in payload.items():
            if v is not None:
                setattr(existing, k, v)
        s.flush()
        return existing.id
    else:
        mt = Match(**payload)
        s.add(mt)
        s.flush()
        return mt.id


def _upsert_match_stats(s: Session, match_id: int, row: dict):
    ms = s.execute(select(MatchStats).where(MatchStats.match_id == match_id)).scalar_one_or_none()
    payload: dict[str, int | None] = {"match_id": match_id}

    for src, dst in STATS_MAP.items():
        if src in row and pd.notna(row[src]):
            payload[dst] = _to_int(row[src])

    for dst, (a, b) in TOTALS_FORMULAS.items():
        va = _to_int(row.get(a)) if a in row and pd.notna(row.get(a)) else None
        vb = _to_int(row.get(b)) if b in row and pd.notna(row.get(b)) else None
        if va is not None or vb is not None:
            payload[dst] = (va or 0) + (vb or 0)

    if "total_cardshome" in payload or "total_cardsaway" in payload:
        payload["total_cards"] = (payload.get("total_cardshome") or 0) + (payload.get("total_cardsaway") or 0)

    if ms:
        for k, v in payload.items():
            if k != "match_id" and v is not None:
                setattr(ms, k, v)
    else:
        s.add(MatchStats(**payload))


@app.command()
def run(
    csv: str = typer.Argument(..., help="Ruta al CSV (E0 xx).csv"),
    league: str = typer.Option("Premier League", help="Nombre de la liga"),
    div: str = typer.Option("E0", help="Código de la columna Div (p.ej. E0)"),
    season_id: int | None = typer.Option(None, help="season_id a asignar (opcional)"),
    dayfirst: bool = typer.Option(True, help="Fechas dd/mm/yyyy"),
):
    df = pd.read_csv(csv)

    if "Div" in df.columns and div:
        df = df[df["Div"] == div].copy()

    if "Date" not in df.columns:
        raise typer.BadParameter("CSV debe incluir columna 'Date'")
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=dayfirst, errors="coerce")

    with SessionLocal() as s:
        lg_id = _get_or_create_league(s, league)
        team_cache: dict[str, int] = {}

        for _, r in df.iterrows():
            hname = str(r["HomeTeam"]).strip()
            aname = str(r["AwayTeam"]).strip()
            if not hname or not aname or pd.isna(r["Date"]):
                continue

            if hname not in team_cache:
                team_cache[hname] = _get_or_create_team(s, hname, lg_id)
            if aname not in team_cache:
                team_cache[aname] = _get_or_create_team(s, aname, lg_id)

            mid = _upsert_match(s, r["Date"], team_cache[hname], team_cache[aname], r, season_id)
            _upsert_match_stats(s, mid, r)

        s.commit()
        typer.echo(f"OK: cargado {len(df)} filas (liga={league}, div={div}, season_id={season_id})")

if __name__ == "__main__":
    app()