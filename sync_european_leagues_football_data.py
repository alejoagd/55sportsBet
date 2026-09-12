"""
sync_european_leagues_football_data.py
Sync de respaldo (calendario + resultados) para Premier League, La Liga,
Serie A y Bundesliga vía football-data.org — mismo proveedor y API key que
ya usamos para los escudos y para Brasileirao (sync_brasileirao_football_data.py).

Estas 4 ligas normalmente cargan resultados vía CSV de football-data.co.uk
(scripts/download-latest-data.py). Este script sirve de fuente alternativa
para cuando ese sitio esté caído, y de redundancia normal en adelante.

IMPORTANTE — por qué NO se resuelve equipos por nombre (incidente 2026-09-11):
la primera versión usaba TeamResolver, que matchea por nombre normalizado y
crea un equipo nuevo si no encuentra uno igual. football-data.org devuelve
nombres oficiales completos ("Manchester United FC") que nunca coinciden con
los nombres cortos que ya usa la BD, cargados por años desde football-data.co.uk
("Man United") — eso creó 74 equipos y 1444 partidos duplicados en la primera
corrida. Ahora los equipos se resuelven SOLO por un mapeo explícito y fijo
(TEAM_ID_MAP, id numérico de football-data.org -> id ya existente en la BD).
Un equipo que no esté en el mapeo se SALTA con un warning; nunca se crea un
equipo nuevo automáticamente para estas 4 ligas.

Uso:
  python sync_european_leagues_football_data.py --dump-teams   # ver equipos+ids de la API (no toca la BD, no requiere .env.production)
  python sync_european_leagues_football_data.py                # dry-run (requiere .env.production para comparar)
  python sync_european_leagues_football_data.py --apply
  python sync_european_leagues_football_data.py --apply --leagues PL,BL1
"""
from __future__ import annotations
import argparse
import os
from datetime import date, datetime

import requests

# código football-data.org -> (nombre exacto en tabla leagues, país)
LEAGUES = {
    "PL": ("Premier League", "England"),
    "PD": ("La Liga", "Spain"),
    "SA": ("Serie A", "Italy"),
    "BL1": ("Bundesliga", "Germany"),
}

# Mapeo explícito y fijo: id numérico de equipo en football-data.org -> id de
# equipo YA EXISTENTE en nuestra BD (con el nombre corto de football-data.co.uk).
# Se completa una sola vez con --dump-teams + los ids reales de la BD.
# Vacío a propósito hasta completarlo: con el mapeo vacío, sync_league salta
# TODOS los partidos (unmapped) sin escribir nada — seguro por diseño, nunca
# usar una heurística de nombre acá otra vez (ver incidente 2026-09-11 arriba).
TEAM_ID_MAP: dict[int, int] = {}


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


def dump_teams(api_key: str, codes: list[str]) -> None:
    """Solo lectura: imprime id+nombre de cada equipo visto en football-data.org
    para estas competencias, sin tocar la BD (no requiere .env.production)."""
    for code in codes:
        name, _ = LEAGUES[code]
        matches = fetch_matches(api_key, code)
        seen: dict[int, str] = {}
        for m in matches:
            for side in ("homeTeam", "awayTeam"):
                t = m[side]
                if t.get("id") is not None:
                    seen[t["id"]] = t["name"]
        print(f"\n{name} ({code}): {len(seen)} equipos")
        for tid, tname in sorted(seen.items(), key=lambda kv: kv[1]):
            print(f"  {tid}\t{tname}")


def sync_league(conn, competition_code: str, matches: list[dict], year_start: int) -> dict:
    from src.ingest.competitions_config import get_or_create_league, get_or_create_season
    from src.ingest.match_upsert import upsert_match
    from sqlalchemy import text

    name, country = LEAGUES[competition_code]
    league_id = get_or_create_league(conn, name, country)
    season_id = get_or_create_season(conn, league_id, year_start)

    inserted = updated = skipped = 0
    unmapped: set[tuple[int, str]] = set()

    for m in matches:
        home = m["homeTeam"]
        away = m["awayTeam"]
        if home.get("id") is None or away.get("id") is None:
            continue

        home_id = TEAM_ID_MAP.get(home["id"])
        away_id = TEAM_ID_MAP.get(away["id"])
        if home_id is None:
            unmapped.add((home["id"], home["name"]))
        if away_id is None:
            unmapped.add((away["id"], away["name"]))
        if home_id is None or away_id is None:
            continue  # nunca crear un equipo nuevo acá — ver docstring del módulo

        utc_date = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        status = m.get("status")

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

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "unmapped": unmapped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync de respaldo de las 4 grandes ligas europeas vía football-data.org")
    parser.add_argument("--apply", action="store_true", help="Escribe en la BD (si no se pasa, solo muestra un resumen)")
    parser.add_argument("--dump-teams", action="store_true", help="Solo imprime equipos+ids de football-data.org, no toca la BD")
    parser.add_argument("--leagues", default="all", help="Códigos football-data.org separados por coma (PL,PD,SA,BL1) o 'all'")
    args = parser.parse_args()

    api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")
    if not api_key:
        raise SystemExit("FOOTBALL_DATA_ORG_KEY no configurada")

    codes = list(LEAGUES.keys()) if args.leagues.lower() == "all" else [c.strip() for c in args.leagues.split(",")]

    if args.dump_teams:
        dump_teams(api_key, codes)
        return

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

    from src.db import engine
    from src.ingest.db_retry import run_with_retry

    def _do():
        results = {}
        with engine.begin() as conn:
            for code in codes:
                results[code] = sync_league(conn, code, fetched[code], year_start)
        return results

    results = run_with_retry(_do)
    all_unmapped: set[tuple[int, str]] = set()
    for code in codes:
        name, _ = LEAGUES[code]
        r = results[code]
        print(f"✅ {name}: insertados={r['inserted']} actualizados={r['updated']} sin_cambios={r['skipped']}")
        all_unmapped |= r["unmapped"]

    if all_unmapped:
        print(f"\n⚠️  {len(all_unmapped)} equipos de football-data.org sin mapear (sus partidos se saltaron, no se creó nada):")
        for tid, tname in sorted(all_unmapped, key=lambda x: x[1]):
            print(f"   {tid}\t{tname}")


if __name__ == "__main__":
    main()
