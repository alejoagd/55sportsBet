#!/usr/bin/env python
"""
Descarga escudos (crest/logo) de ESPN para Copa Libertadores y Copa
Sudamericana (equipos que quedaron sin escudo tras el backfill de las 4
ligas europeas — ver conversación sobre escudos en tabla de posiciones).

IMPORTANTE — por qué usa el endpoint de standings y no el de scoreboard:
un primer intento recorrió el calendario día por día (fetch_scoreboard_range,
~450 pedidos en una sola corrida) y ESPN devolvió 403 Forbidden en el 100%
de los pedidos. El sync automático que sí funciona en este mismo repo
(update_competitions_espn_sync.py, corre varias veces al día sin problema)
solo pide una ventana de ±26 días — muchísimo menos volumen. Para no repetir
el bloqueo, este script pide 1 sola vez el endpoint de standings por
competencia (mismo mecanismo que fetch_groups() en espn_competition_client,
pero acá además se guarda el logo de cada equipo si el JSON lo trae).

Uso:
    python scripts/fetch_espn_crests.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ingest.espn_competition_client import STANDINGS_BASE, HEADERS
import requests

SLUGS = ["conmebol.libertadores", "conmebol.sudamericana"]


def fetch_teams_with_logo(slug: str) -> list[dict]:
    resp = requests.get(f"{STANDINGS_BASE}/{slug}/standings", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    teams: dict[int, dict] = {}
    for child in data.get("children", []):
        entries = (child.get("standings") or {}).get("entries", [])
        for entry in entries:
            team = entry.get("team") or {}
            team_id = team.get("id")
            if not team_id:
                continue
            logo = team.get("logo")
            if not logo:
                logos = team.get("logos") or []
                logo = logos[0].get("href") if logos else None
            teams[int(team_id)] = {
                "espn_id": int(team_id),
                "name": team.get("displayName") or team.get("name"),
                "logo": logo,
            }
    return list(teams.values())


def main() -> None:
    out: dict[str, list[dict]] = {}
    for slug in SLUGS:
        print(f"Descargando standings de {slug}...")
        try:
            teams = fetch_teams_with_logo(slug)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            out[slug] = []
            continue
        with_logo = [t for t in teams if t["logo"]]
        print(f"   {len(teams)} equipos, {len(with_logo)} con logo")
        out[slug] = teams

    output_path = Path("data/espn_crests.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado en {output_path}")


if __name__ == "__main__":
    main()
