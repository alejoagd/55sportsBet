#!/usr/bin/env python
"""
Descarga escudos (crest/logo) de ESPN para las 3 competencias que todavía
no tienen escudo en la BD: Copa Libertadores, Copa Sudamericana y el
Mundial 2026 (ver conversación sobre escudos en tabla de posiciones).

A diferencia de fetch_football_data_org_logos.py (equipos de clubes
europeos, autenticado), acá se reusa el cliente ESPN público que ya usa
update_competitions_espn_sync.py para cargar el calendario de estas 3
competencias — cada partido trae el logo del equipo local/visitante
(`home_logo`/`away_logo`), así que basta con recorrer el calendario ya
cargado y juntar un logo por equipo (por espn_team_id).

Uso:
    python scripts/fetch_espn_crests.py
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ingest.espn_competition_client import fetch_scoreboard_range

# Rango de fechas de cada competencia (visto en la BD: MIN/MAX date de sus
# partidos), con un pequeño margen para no perder el primer/último partido.
COMPETITIONS = {
    "conmebol.libertadores": (date(2026, 1, 25), date(2026, 8, 25)),
    "conmebol.sudamericana": (date(2026, 2, 25), date(2026, 8, 25)),
    "fifa.world": (date(2026, 6, 5), date(2026, 7, 25)),
}


def main() -> None:
    out: dict[str, list[dict]] = {}
    for slug, (date_from, date_to) in COMPETITIONS.items():
        print(f"Descargando {slug} ({date_from} a {date_to})...")
        fixtures = fetch_scoreboard_range(slug, date_from, date_to)
        teams: dict[int, dict] = {}
        for fx in fixtures:
            if fx.get("home_logo"):
                teams[fx["home_espn_id"]] = {
                    "espn_id": fx["home_espn_id"], "name": fx["home_name"], "logo": fx["home_logo"],
                }
            if fx.get("away_logo"):
                teams[fx["away_espn_id"]] = {
                    "espn_id": fx["away_espn_id"], "name": fx["away_name"], "logo": fx["away_logo"],
                }
        print(f"  {len(fixtures)} partidos -> {len(teams)} equipos únicos con logo")
        out[slug] = list(teams.values())

    output_path = Path("data/espn_crests.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado en {output_path}")


if __name__ == "__main__":
    main()
