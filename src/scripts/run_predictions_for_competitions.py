# src/scripts/run_predictions_for_competitions.py
"""
Genera predicciones Poisson/Weinston para las 5 competencias nuevas
(Brasileirao, Liga Argentina, Liga Betplay, Copa Libertadores, Copa
Sudamericana), resolviendo el season_id de la temporada actual por nombre de
liga en vez de hardcodearlo — evita que el workflow de GitHub Actions dependa
de IDs de BD que pueden variar entre entornos.

Reentrena Weinston (ratings por equipo + parámetros de liga) antes de
predecir. A diferencia de las 4 ligas europeas originales, que tienen su
propio paso de retrain en update-predictions.yml, este script nunca
disparaba un entrenamiento — weinston_ratings quedaba vacío para las 5
competencias y, sin rating propio, todos los equipos caían al mismo valor
neutro: la predicción de Weinston terminaba siendo idéntica (mismo 1X2,
mismo marcador) para absolutamente todos los partidos de una liga.

Uso:
  python -m src.scripts.run_predictions_for_competitions
"""
from __future__ import annotations
from datetime import date
from sqlalchemy import text

from src.db import engine, SessionLocal
from src.ingest.competitions_config import COMPETITIONS
from src.predictions.league_context import LeagueContext
from src.predictions.upcoming_poisson import predict_and_upsert_poisson
from src.predictions.upcoming_weinston import predict_and_upsert_weinston
from src.weinston.fit import fit_weinston, save_ratings, save_league_params

CURRENT_YEAR = date.today().year


def _retrain_weinston(season_id: int, league_name: str) -> None:
    with SessionLocal() as s:
        try:
            result = fit_weinston(s, season_id)
        except ValueError as e:
            print(f"   ⚠️  No se pudo reentrenar Weinston para {league_name}: {e}")
            return
    save_ratings(
        season_id=season_id,
        team_ids=result.team_ids,
        atk_home=result.atk_home,
        def_home=result.def_home,
        atk_away=result.atk_away,
        def_away=result.def_away,
    )
    save_league_params(
        season_id=season_id,
        mu_home=result.mu_home,
        mu_away=result.mu_away,
        home_adv=result.home_adv,
        loss=result.loss,
    )
    print(f"   ✅ Weinston reentrenado para {league_name} ({len(result.team_ids)} equipos)")


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

            _retrain_weinston(season_id, comp["name"])

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
