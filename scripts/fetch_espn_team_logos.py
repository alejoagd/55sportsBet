"""
Descarga de ESPN (nombre + escudo) los equipos vistos en el scoreboard de
las 4 ligas europeas originales (Premier League, La Liga, Serie A,
Bundesliga), y los guarda en un JSON.

Separado a propósito de backfill_team_logos_top5.py: este script solo
necesita salida a internet (para correr en GitHub Actions), el matching
contra nuestros nombres de equipo + la escritura en la BD se hace aparte,
localmente, con:
    python backfill_team_logos_top5.py --from-json data/espn_team_logos.json --apply

Uso:
    python scripts/fetch_espn_team_logos.py
"""
from __future__ import annotations
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest.espn_competition_client import fetch_scoreboard_range

LEAGUES = [
    {"league_id": 1, "name": "Premier League", "espn_slug": "eng.1"},
    {"league_id": 2, "name": "La Liga", "espn_slug": "esp.1"},
    {"league_id": 3, "name": "Serie A", "espn_slug": "ita.1"},
    {"league_id": 4, "name": "Bundesliga", "espn_slug": "ger.1"},
]


def fetch_teams_for_league(slug: str) -> list[dict]:
    start = date.today() - timedelta(days=60)
    end = date.today() + timedelta(days=30)
    fixtures = fetch_scoreboard_range(slug, start, end)

    seen: dict[int, dict] = {}
    for fx in fixtures:
        for prefix in ("home", "away"):
            eid = fx[f"{prefix}_espn_id"]
            if eid not in seen:
                seen[eid] = {"espn_id": eid, "name": fx[f"{prefix}_name"], "logo": fx.get(f"{prefix}_logo")}
    return list(seen.values())


def main() -> None:
    out: dict[str, list[dict]] = {}
    for league in LEAGUES:
        print(f"Descargando {league['name']} ({league['espn_slug']})...")
        teams = fetch_teams_for_league(league["espn_slug"])
        print(f"  {len(teams)} equipos vistos")
        out[str(league["league_id"])] = teams

    output_path = Path("data/espn_team_logos.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Guardado en {output_path}")


if __name__ == "__main__":
    main()
