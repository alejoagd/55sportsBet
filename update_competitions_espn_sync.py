"""
update_competitions_espn_sync.py
Sync diario (calendario + resultados) de la temporada EN CURSO para las 5
competencias nuevas (Brasileirao, Liga Argentina, Liga Betplay, Copa
Libertadores, Copa Sudamericana), vía ESPN (público, sin autenticación).

El backfill histórico (2022-2024, vía API-Football) es un proceso aparte, ver
src/ingest/load_api_football_history.py — este script SOLO mantiene al día la
temporada actual: calendario futuro, resultados, y para las 2 copas, la ronda
(`stage`/`round_label`) y el grupo (`group_name`) de cada partido.

Fuente ESPN: usa src/ingest/espn_core_client.py (sports.core.api.espn.com),
NO espn_competition_client.py (site.api.espn.com) — esa segunda superficie
devuelve 403 Forbidden en el 100% de los pedidos desde GitHub Actions desde
2026-08-04. La core API sí responde, con la misma forma de datos, aunque
requiere más pedidos por partido (ver docstring de espn_core_client.py) y
por ahora no distingue bien la ronda de las 2 copas (fase de grupos vs
eliminatoria) — round_label queda con el texto crudo de ESPN ("1st Leg",
etc.) en vez de un nombre de ronda, así que esas 2 caen a stage="regular".
Brasileirao no pasa por acá — se sincroniza aparte vía football-data.org
(sync_brasileirao_football_data.py).

Uso:
  python update_competitions_espn_sync.py
  python update_competitions_espn_sync.py --key copa_libertadores --dry-run
  python update_competitions_espn_sync.py --days-back 5 --days-forward 21
"""
from __future__ import annotations
import sys
import argparse
from datetime import date, timedelta

from src.db import engine
from src.ingest.competitions_config import COMPETITIONS, get_competition, get_or_create_league, get_or_create_season
from src.ingest.espn_core_client import fetch_scoreboard_range, fetch_groups
from src.ingest.team_identity import TeamResolver
from src.ingest.stage_mapping import map_stage
from src.ingest.match_upsert import upsert_match
from src.ingest.db_retry import run_with_retry

CURRENT_YEAR = date.today().year


def _sync_one(comp: dict, start: date, end: date, dry_run: bool) -> None:
    print(f"\n{'='*70}")
    print(f"  {comp['name']} (ESPN slug={comp['espn_slug']})")
    print(f"{'='*70}")

    fixtures = fetch_scoreboard_range(comp["espn_slug"], start, end)
    print(f"   {len(fixtures)} fixtures encontrados ({start} → {end})")

    # Se pide siempre, no solo para copas: varias ligas domésticas (Liga
    # Argentina, Liga Betplay) también dividen la temporada en zonas/grupos
    # (Grupo A / Grupo B), no son todas tabla única. Si la competencia no
    # tiene grupos reales, fetch_groups devuelve {} y no cambia nada.
    groups: dict[int, str] = fetch_groups(comp["espn_slug"])
    if groups:
        print(f"   {len(set(groups.values()))} grupo(s) activo(s) ({len(groups)} equipos)")

    if dry_run:
        for fx in fixtures[:5]:
            print(f"   [DRY] {fx['date']}  {fx['home_name']} vs {fx['away_name']}  "
                  f"({fx['home_goals']}-{fx['away_goals']})  ronda={fx['round_label']}")
        if len(fixtures) > 5:
            print(f"   ... y {len(fixtures) - 5} más")
        return

    def _do():
        with engine.begin() as conn:
            league_id = get_or_create_league(conn, comp["name"], comp["country"])
            season_id = get_or_create_season(conn, league_id, CURRENT_YEAR)
            resolver = TeamResolver(conn)

            inserted = updated = skipped = 0
            for fx in fixtures:
                if not fx["date"]:
                    continue
                home_id = resolver.resolve(fx["home_name"], league_id, "espn", fx["home_espn_id"], fx.get("home_logo"))
                away_id = resolver.resolve(fx["away_name"], league_id, "espn", fx["away_espn_id"], fx.get("away_logo"))

                if comp["kind"] == "league":
                    stage = "regular"
                    # Ojo: algunas ligas con zonas (Liga Argentina) tienen
                    # partidos interzonales (Grupo A vs Grupo B). Si local y
                    # visitante quedan en zonas distintas, el partido no
                    # pertenece a ninguna de las dos — dejarlo en None evita
                    # contaminar la zona real de cualquiera de los 2 equipos.
                    home_group = groups.get(fx["home_espn_id"])
                    away_group = groups.get(fx["away_espn_id"])
                    group_name = home_group if home_group == away_group else None
                else:
                    # La ronda que entrega ESPN (series.title / season.slug) manda:
                    # es la fuente de verdad. El endpoint de standings puede seguir
                    # listando a los equipos en su grupo histórico incluso durante
                    # la eliminatoria, así que solo se usa para rellenar group_name
                    # cuando la propia ronda ya dice que es fase de grupos — nunca
                    # para reclasificar un partido de knockout como "group".
                    stage = map_stage(fx["round_label"])
                    group_name = groups.get(fx["home_espn_id"]) if stage == "group" else None

                _, action = upsert_match(
                    conn,
                    season_id=season_id,
                    match_date=fx["date"],
                    home_id=home_id,
                    away_id=away_id,
                    home_goals=fx["home_goals"],
                    away_goals=fx["away_goals"],
                    stage=stage,
                    round_label=fx["round_label"],
                    group_name=group_name,
                    espn_event_id=fx["espn_event_id"],
                    kickoff_at=fx.get("kickoff_at"),
                )
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1
                else:
                    skipped += 1
            return inserted, updated, skipped

    inserted, updated, skipped = run_with_retry(_do)
    print(f"   ✅ insertados={inserted} actualizados={updated} sin_cambios={skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync diario ESPN de las 5 competencias nuevas")
    parser.add_argument("--key", help="Sincronizar solo una competencia (ver competitions_config.py)")
    parser.add_argument("--days-back", type=int, default=5, help="Días hacia atrás a revisar")
    parser.add_argument("--days-forward", type=int, default=21, help="Días hacia adelante a revisar")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Brasileirao se sincroniza aparte vía football-data.org
    # (sync_brasileirao_football_data.py) — ESPN bloquea (403) esta y las
    # otras 4 competencias desde GitHub Actions desde 2026-08-04, y de las 5
    # Brasileirao es la única con una fuente alternativa gratuita disponible.
    comps = [get_competition(args.key)] if args.key else [c for c in COMPETITIONS if c["key"] != "brasileirao"]
    start = date.today() - timedelta(days=args.days_back)
    end = date.today() + timedelta(days=args.days_forward)

    mode = "DRY RUN" if args.dry_run else "SINCRONIZANDO"
    print("=" * 70)
    print(f"  Sync ESPN — {mode}")
    print(f"  Competencias: {', '.join(c['name'] for c in comps)}")
    print("=" * 70)

    for comp in comps:
        _sync_one(comp, start, end, args.dry_run)

    print(f"\n{'='*70}\n  ✅ Sync completo\n{'='*70}")


if __name__ == "__main__":
    main()
