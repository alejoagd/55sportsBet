"""
Backfill histórico de las 5 competencias sudamericanas desde ESPN.

Por qué: el plan Free de API-Football solo permite 2022-2024 (ver
api_football_client.ALLOWED_HISTORICAL_SEASONS), así que faltaba 2025 y todo lo
anterior a 2022. Con tan poca historia, los enfrentamientos directos (H2H) de
la mayoría de partidos de Liga Argentina o Betplay tenían 1 o 2 partidos.
ESPN (misma API core que ya usa el sync diario de 2026) trae calendario y
resultados de años anteriores sin key.

Decisiones:
- 2022-2024 y el año en curso NO se cargan por defecto: ya vienen de
  API-Football / del sync diario, y ESPN da la hora en UTC; si la fecha difiere
  un día de la que guardó API-Football, el respaldo (season, local, visita,
  fecha) de match_upsert no lo reconocería y duplicaría el partido.
- Solo se guardan partidos con marcador: un evento sin goles en una temporada
  vieja es un partido suspendido o cancelado, y dejarlo como "pendiente" lo
  mostraría como próximo partido.
- Sin zonas (group_name): el historial se usa para H2H y tendencias, no para
  tablas de posiciones de temporadas pasadas.
- Es idempotente (upsert por espn_event_id): se puede repetir o reanudar.

Uso (por defecto SIMULA: baja de ESPN y cuenta, pero no escribe):
  python -m src.ingest.load_espn_history --key copa_libertadores --years 2025
  python -m src.ingest.load_espn_history --years 2025 2013-2021 --apply

Se niega a correr contra una BD que no sea local, salvo --allow-remote.
"""
from __future__ import annotations
import argparse
import sys
import time
from datetime import date

from sqlalchemy import text

from src.db import engine
from src.ingest.competitions_config import COMPETITIONS, get_or_create_league, get_or_create_season
from src.ingest.db_retry import run_with_retry
from src.ingest.espn_core_client import fetch_scoreboard_range
from src.ingest.match_upsert import upsert_match
from src.ingest.stage_mapping import map_stage
from src.ingest.team_identity import TeamResolver

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}
YA_CARGADOS = {2022, 2023, 2024, date.today().year}


def parse_years(tokens: list[str]) -> list[int]:
    """['2025', '2013-2021'] -> [2013, ..., 2021, 2025]."""
    years: set[int] = set()
    for t in tokens:
        if "-" in t:
            a, b = t.split("-", 1)
            years.update(range(int(a), int(b) + 1))
        else:
            years.add(int(t))
    return sorted(years)


def load_year(comp: dict, year: int, apply: bool) -> dict:
    t0 = time.time()
    fixtures = fetch_scoreboard_range(comp["espn_slug"], date(year, 1, 1), date(year, 12, 31))
    played = [f for f in fixtures if f.get("date") and f["home_goals"] is not None and f["away_goals"] is not None]
    res = {"fetched": len(fixtures), "played": len(played), "inserted": 0, "updated": 0, "skipped": 0,
           "secs": round(time.time() - t0)}
    if not apply or not played:
        return res

    def _do():
        with engine.begin() as conn:
            league_id = get_or_create_league(conn, comp["name"], comp["country"])
            season_id = get_or_create_season(conn, league_id, year)
            resolver = TeamResolver(conn)
            counts = {"inserted": 0, "updated": 0, "skipped": 0}
            for fx in played:
                home_id = resolver.resolve(fx["home_name"], league_id, "espn", fx["home_espn_id"], fx.get("home_logo"))
                away_id = resolver.resolve(fx["away_name"], league_id, "espn", fx["away_espn_id"], fx.get("away_logo"))
                stage = "regular" if comp["kind"] == "league" else map_stage(fx["round_label"])
                _, action = upsert_match(
                    conn, season_id=season_id, match_date=fx["date"], home_id=home_id, away_id=away_id,
                    home_goals=fx["home_goals"], away_goals=fx["away_goals"], stage=stage,
                    round_label=fx["round_label"], group_name=None,
                    espn_event_id=fx["espn_event_id"], kickoff_at=fx.get("kickoff_at"),
                )
                counts[action] += 1
            return counts

    res.update(run_with_retry(_do))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", nargs="+", choices=[c["key"] for c in COMPETITIONS], help="Solo estas competencias")
    ap.add_argument("--years", nargs="+", required=True, help="Años o rangos, p. ej. 2025 2013-2021")
    ap.add_argument("--apply", action="store_true", help="Escribe (por defecto solo simula)")
    ap.add_argument("--include-loaded", action="store_true",
                    help="Permite años ya cargados por otra fuente (2022-2024 y el actual): riesgo de duplicados")
    ap.add_argument("--allow-remote", action="store_true", help="Permite correr contra una BD no local")
    args = ap.parse_args()

    host = engine.url.host
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"⛔ La BD configurada es '{host}' (no local). Abortado: usa --allow-remote solo si es intencional.")
        return 2
    years = parse_years(args.years)
    omitidos = [y for y in years if y in YA_CARGADOS]
    if omitidos and not args.include_loaded:
        print(f"ℹ️  Se omiten {omitidos}: ya los cubre otra fuente (usa --include-loaded para forzarlo).")
        years = [y for y in years if y not in YA_CARGADOS]
    print(f"BD: {host or 'socket local'}/{engine.url.database} · modo: {'APLICAR' if args.apply else 'SIMULACIÓN'} · años: {years}")

    for comp in [c for c in COMPETITIONS if not args.key or c["key"] in args.key]:
        for year in years:
            r = load_year(comp, year, args.apply)
            print(f"{comp['name']:<18} {year}: ESPN {r['fetched']:>4} · con marcador {r['played']:>4}"
                  + (f" · +{r['inserted']} nuevos, {r['updated']} actualizados, {r['skipped']} sin cambios" if args.apply else "")
                  + f"  ({r['secs']}s)", flush=True)
    if not args.apply:
        print("\nℹ️  Simulación: no se escribió nada. Repite con --apply para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
