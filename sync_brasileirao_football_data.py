"""
sync_brasileirao_football_data.py
Sync diario (calendario + resultados) de Brasileirao vía football-data.org
(competition id 2013, plan free) — reemplaza a ESPN solo para esta liga.

ESPN devuelve 403 Forbidden en el 100% de los pedidos desde GitHub Actions
para las 5 competencias de update_competitions_espn_sync.py desde el
2026-08-04 (bloqueo del lado de ESPN, no de nuestro código). De esas 5,
Brasileirao es la única que aparece en el catálogo del plan free de
football-data.org (mismo proveedor y API key que ya usamos para Premier
League/La Liga/Serie A/Bundesliga) — Liga Argentina, Liga Betplay y Copa
Sudamericana no están en su catálogo, y Copa Libertadores solo en un plan
pago. Esas 4 siguen sin fuente automática hasta resolver algo aparte.

Uso:
  python sync_brasileirao_football_data.py            # dry-run
  python sync_brasileirao_football_data.py --apply
"""
from __future__ import annotations
import argparse
import os
from datetime import datetime

import requests

from src.db import engine
from src.ingest.competitions_config import get_competition, get_or_create_league, get_or_create_season
from src.ingest.team_identity import TeamResolver
from src.ingest.match_upsert import upsert_match
from src.ingest.db_retry import run_with_retry

COMPETITION_ID = 2013  # football-data.org: Campeonato Brasileiro Série A
CURRENT_YEAR = datetime.now().year


def fetch_matches(api_key: str) -> list[dict]:
    resp = requests.get(
        f"https://api.football-data.org/v4/competitions/{COMPETITION_ID}/matches",
        headers={"X-Auth-Token": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync de Brasileirao vía football-data.org")
    parser.add_argument("--apply", action="store_true", help="Escribe en la BD (si no se pasa, solo muestra un resumen)")
    args = parser.parse_args()

    api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")
    if not api_key:
        raise SystemExit("FOOTBALL_DATA_ORG_KEY no configurada")

    comp = get_competition("brasileirao")
    matches = fetch_matches(api_key)
    print(f"{len(matches)} partidos encontrados en football-data.org para {comp['name']}")

    if not args.apply:
        for m in matches[:5]:
            print(f"  [DRY] {m['utcDate']} {m['homeTeam']['name']} vs {m['awayTeam']['name']} status={m['status']}")
        if len(matches) > 5:
            print(f"  ... y {len(matches) - 5} más")
        print("\nDRY-RUN — nada se escribió. Correr con --apply para sincronizar de verdad.")
        return

    def _do():
        with engine.begin() as conn:
            league_id = get_or_create_league(conn, comp["name"], comp["country"])
            season_id = get_or_create_season(conn, league_id, CURRENT_YEAR)
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

    inserted, updated, skipped = run_with_retry(_do)
    print(f"✅ insertados={inserted} actualizados={updated} sin_cambios={skipped}")


if __name__ == "__main__":
    main()
