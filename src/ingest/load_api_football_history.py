# src/ingest/load_api_football_history.py
"""
Backfill histórico (temporadas 2022-2024, único rango permitido en el plan
Free de api-sports.io) para cualquiera de las 5 competencias nuevas. Alimenta
el entrenamiento de Poisson/Weinston con resultados reales pasados.

El calendario/resultados de la temporada EN CURSO se sincronizan aparte desde
ESPN (ver update_competitions_espn_sync.py) — este script NO toca eso.

Uso:
  python -m src.ingest.load_api_football_history run --key brasileirao
  python -m src.ingest.load_api_football_history run --key copa_libertadores --seasons 2023 2024
  python -m src.ingest.load_api_football_history run --all --dry-run
"""
from __future__ import annotations
import typer
from sqlalchemy import text

from src.db import engine
from src.ingest.api_football_client import APIFootballClient, ALLOWED_HISTORICAL_SEASONS
from src.ingest.competitions_config import COMPETITIONS, get_competition, get_or_create_league, get_or_create_season
from src.ingest.team_identity import TeamResolver
from src.ingest.stage_mapping import map_stage
from src.ingest.match_upsert import upsert_match
from src.ingest.db_retry import run_with_retry

app = typer.Typer(help="Backfill histórico API-Football para las 5 competencias nuevas")


def _load_one(client: APIFootballClient, comp: dict, seasons: list[int], dry_run: bool) -> None:
    print(f"\n{'='*70}")
    print(f"  {comp['name']} (API-Football league_id={comp['api_football_league_id']})")
    print(f"{'='*70}")

    with engine.begin() as conn:
        league_id = get_or_create_league(conn, comp["name"], comp["country"])

        for year in seasons:
            season_id = get_or_create_season(conn, league_id, year)
            print(f"\n📥 Temporada {year} (season_id={season_id})...")

            fixtures = client.get_fixtures(comp["api_football_league_id"], year)
            print(f"   {len(fixtures)} fixtures descargados")

            group_by_af_team: dict[int, str] = {}
            if comp["kind"] == "cup":
                groups = client.get_standings(comp["api_football_league_id"], year)
                for group in groups:
                    for row in group:
                        group_by_af_team[row["team"]["id"]] = row["group"].replace("Group ", "")
                if groups:
                    print(f"   {len(groups)} grupos encontrados ({sum(len(g) for g in groups)} equipos)")

            resolver = TeamResolver(conn)
            inserted = updated = skipped = 0

            for fx in fixtures:
                home = fx["teams"]["home"]
                away = fx["teams"]["away"]
                round_label = fx["league"]["round"]
                stage = map_stage(round_label)
                match_date = fx["fixture"]["date"][:10]

                if dry_run:
                    continue

                home_id = resolver.resolve(home["name"], league_id, "api_football", home["id"])
                away_id = resolver.resolve(away["name"], league_id, "api_football", away["id"])

                group_name = None
                if stage == "group":
                    group_name = group_by_af_team.get(home["id"]) or group_by_af_team.get(away["id"])

                _, action = upsert_match(
                    conn,
                    season_id=season_id,
                    match_date=match_date,
                    home_id=home_id,
                    away_id=away_id,
                    home_goals=fx["goals"]["home"],
                    away_goals=fx["goals"]["away"],
                    stage=stage,
                    round_label=round_label,
                    group_name=group_name,
                    api_football_fixture_id=fx["fixture"]["id"],
                )
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1
                else:
                    skipped += 1

            if dry_run:
                print(f"   [DRY RUN] {len(fixtures)} fixtures se procesarían (sin escribir)")
            else:
                print(f"   ✅ insertados={inserted} actualizados={updated} sin_cambios={skipped}")


@app.command()
def run(
    key: str = typer.Option(None, help="Clave de una sola competencia (ver competitions_config.COMPETITIONS)"),
    all: bool = typer.Option(False, "--all", help="Procesar las 5 competencias"),
    seasons: list[int] = typer.Option(list(ALLOWED_HISTORICAL_SEASONS), help="Temporadas a cargar"),
    dry_run: bool = typer.Option(False, help="Solo mostrar conteos, sin escribir en BD"),
):
    bad_seasons = [s for s in seasons if s not in ALLOWED_HISTORICAL_SEASONS]
    if bad_seasons:
        raise typer.BadParameter(
            f"Temporadas no soportadas por el plan Free: {bad_seasons}. "
            f"Solo {ALLOWED_HISTORICAL_SEASONS} están disponibles."
        )

    if not key and not all:
        raise typer.BadParameter("Especifica --key <competencia> o --all")

    comps = COMPETITIONS if all else [get_competition(key)]
    client = APIFootballClient()

    for comp in comps:
        run_with_retry(lambda comp=comp: _load_one(client, comp, seasons, dry_run))

    print(f"\n{'='*70}\n  ✅ Backfill histórico completo\n{'='*70}")


if __name__ == "__main__":
    app()
