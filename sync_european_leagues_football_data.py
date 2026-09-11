"""
sync_european_leagues_football_data.py
Sync de respaldo (calendario + resultados) para Premier League, La Liga,
Serie A y Bundesliga vía football-data.org — mismo proveedor y API key que
ya usamos para los escudos y para Brasileirao (sync_brasileirao_football_data.py).

Estas 4 ligas normalmente cargan resultados vía CSV de football-data.co.uk
(scripts/download-latest-data.py), pero ese sitio lleva caído desde el
2026-09-05 (503 / timeout total en las 4 URLs). football-data.org cubre
estas 4 competencias en su plan free, así que este script sirve de fuente
alternativa mientras football-data.co.uk no se recupera. No reemplaza el
CSV de forma permanente: si football-data.co.uk vuelve, ambos pueden
convivir porque upsert_match() matchea por equipos/fecha, no por fuente.

Uso:
  python sync_european_leagues_football_data.py            # dry-run
  python sync_european_leagues_football_data.py --apply
  python sync_european_leagues_football_data.py --apply --leagues PL,BL1
"""
from __future__ import annotations
import argparse
import os
from datetime import date, datetime

import requests

from src.db import engine
from src.ingest.competitions_config import get_or_create_league, get_or_create_season
from src.ingest.team_identity import TeamResolver
from src.ingest.match_upsert import upsert_match
from src.ingest.db_retry import run_with_retry

# código football-data.org -> (nombre exacto en tabla leagues, país)
LEAGUES = {
    "PL": ("Premier League", "England"),
    "PD": ("La Liga", "Spain"),
    "SA": ("Serie A", "Italy"),
    "BL1": ("Bundesliga", "Germany"),
}


def current_season_year_start() -> int:
    """Año de inicio de temporada europea (arranca jul/ago) para la fecha de hoy."""
    today = date.today()
    return today.year if today.month >= 7 else today.year - 1


def fetch_matches(api_key: str, competition_code: str) -> list[dict]:
    resp = requests.get(
        f"https://api.football-data.org/v4/competitions/{competition_code}/matches",
        headers={"X-Auth-Token": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def sync_league(conn, competition_code: str, matches: list[dict], year_start: int) -> tuple[int, int, int]:
    name, country = LEAGUES[competition_code]
    league_id = get_or_create_league(conn, name, country)
    season_id = get_or_create_season(conn, league_id, year_start)
    resolver = TeamResolver(conn)

    inserted = updated = skipped = 0
    for m in matches:
        home = m["homeTeam"]
        away = m["awayTeam"]
        if home.get("id") is None or away.get("id") is None:
            continue

        utc_date = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        status = m.get("status")

        home_id = resolver.resolve(home["name"], league_id, "football_data_org", home["id"], home.get("crest"))
        away_id = resolver.resolve(away["name"], league_id, "football_data_org", away["id"], away.get("crest"))

        score = (m.get("score") or {}).get("fullTime") or {}
        home_goals = score.get("home") if status == "FINISHED" else None
        away_goals = score.get("away") if status == "FINISHED" else None
        kickoff_at = utc_date if status in ("TIMED", "FINISHED", "IN_PLAY", "PAUSED") else None

        _, action = upsert_match(
            conn,
            season_id=season_id,
            match_date=utc_date.date(),
            home_id=home_id,
            away_id=away_id,
            home_goals=home_goals,
            away_goals=away_goals,
            stage="regular",
            kickoff_at=kickoff_at,
        )
        if action == "inserted":
            inserted += 1
        elif action == "updated":
            updated += 1
        else:
            skipped += 1
    return inserted, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync de respaldo de las 4 grandes ligas europeas vía football-data.org")
    parser.add_argument("--apply", action="store_true", help="Escribe en la BD (si no se pasa, solo muestra un resumen)")
    parser.add_argument("--leagues", default="all", help="Códigos football-data.org separados por coma (PL,PD,SA,BL1) o 'all'")
    args = parser.parse_args()

    api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")
    if not api_key:
        raise SystemExit("FOOTBALL_DATA_ORG_KEY no configurada")

    codes = list(LEAGUES.keys()) if args.leagues.lower() == "all" else [c.strip() for c in args.leagues.split(",")]
    year_start = current_season_year_start()

    fetched: dict[str, list[dict]] = {}
    for code in codes:
        name, _ = LEAGUES[code]
        matches = fetch_matches(api_key, code)
        fetched[code] = matches
        print(f"{name} ({code}): {len(matches)} partidos encontrados en football-data.org")

    if not args.apply:
        for code in codes:
            name, _ = LEAGUES[code]
            matches = fetched[code]
            finished = [m for m in matches if m.get("status") == "FINISHED"]
            print(f"\n{name}: {len(finished)} finalizados, último = "
                  f"{max((m['utcDate'] for m in finished), default='—')}")
            for m in matches[:3]:
                print(f"  [DRY] {m['utcDate']} {m['homeTeam']['name']} vs {m['awayTeam']['name']} status={m['status']}")
        print("\nDRY-RUN — nada se escribió. Correr con --apply para sincronizar de verdad.")
        return

    def _do():
        totals = {}
        with engine.begin() as conn:
            for code in codes:
                totals[code] = sync_league(conn, code, fetched[code], year_start)
        return totals

    totals = run_with_retry(_do)
    for code in codes:
        name, _ = LEAGUES[code]
        inserted, updated, skipped = totals[code]
        print(f"✅ {name}: insertados={inserted} actualizados={updated} sin_cambios={skipped}")


if __name__ == "__main__":
    main()
