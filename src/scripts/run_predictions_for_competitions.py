# src/scripts/run_predictions_for_competitions.py
"""
Genera predicciones Poisson/Weinston para las 5 competencias nuevas
(Brasileirao, Liga Argentina, Liga Betplay, Copa Libertadores, Copa
Sudamericana), resolviendo el season_id de la temporada actual por nombre de
liga en vez de hardcodearlo — evita que el workflow de GitHub Actions dependa
de IDs de BD que pueden variar entre entornos.

Uso:
  python -m src.scripts.run_predictions_for_competitions
"""
from __future__ import annotations
from datetime import date
from sqlalchemy import text

from src.db import engine
from src.ingest.competitions_config import COMPETITIONS
from src.predictions.league_context import LeagueContext
from src.predictions.upcoming_poisson import predict_and_upsert_poisson
from src.predictions.upcoming_weinston import predict_and_upsert_weinston

CURRENT_YEAR = date.today().year


def main() -> None:
    with engine.begin() as conn:
        for comp in COMPETITIONS:
            row = conn.execute(
                text("""
                    SELECT s.id FROM seasons s
                    JOIN leagues l ON l.id = s.league_id
                    WHERE l.name = :name AND s.year_start = :year
                """),
                {"name": comp["name"], "year": CURRENT_YEAR},
            ).fetchone()
            if not row:
                print(f"⚠️  Sin temporada {CURRENT_YEAR} para {comp['name']}, se omite")
                continue
            season_id = row.id

            match_rows = conn.execute(
                text("""
                    SELECT id FROM matches
                    WHERE season_id = :sid AND home_goals IS NULL AND away_goals IS NULL
                """),
                {"sid": season_id},
            ).fetchall()
            if not match_rows:
                print(f"ℹ️  {comp['name']}: sin partidos pendientes")
                continue
            match_ids = [r.id for r in match_rows]

            print(f"\n🎯 {comp['name']} (season_id={season_id}): {len(match_ids)} partido(s) pendiente(s)")
            league_ctx = LeagueContext.from_season(conn, season_id)
            predict_and_upsert_poisson(conn, season_id, match_ids, league_ctx=league_ctx)
            predict_and_upsert_weinston(conn, season_id, match_ids, league_ctx=league_ctx)
            print(f"   ✅ predicciones generadas")


if __name__ == "__main__":
    main()
