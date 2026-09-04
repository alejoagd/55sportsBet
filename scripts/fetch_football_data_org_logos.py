#!/usr/bin/env python
"""
Descarga escudo (crest) de cada equipo de las 4 ligas europeas originales
desde football-data.org (misma API/key ya usada por
download-fixtures-final.py para el calendario) y los guarda en JSON,
mapeados directamente al nombre exacto que usa nuestra BD vía el mismo
TEAM_NAME_MAPPING ya verificado en ese script — a diferencia del intento
con ESPN (bloqueado/rate-limitado para estas 4 ligas de alto tráfico),
esta API es autenticada y el nombre ya viene 1:1 mapeado, sin necesidad
de fuzzy matching.

Uso (requiere FOOTBALL_DATA_ORG_KEY):
    python scripts/fetch_football_data_org_logos.py
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import requests

# `download-fixtures-final.py` no es un módulo importable por el guion en el
# nombre ("import download-fixtures-final" es un SyntaxError) — se carga por
# ruta de archivo en vez de por nombre, para reusar su TEAM_NAME_MAPPING ya
# verificado sin duplicarlo.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "download_fixtures_final", Path(__file__).resolve().parent / "download-fixtures-final.py"
)
_dff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dff)

LEAGUE_MAPPING = _dff.LEAGUE_MAPPING  # {'E0': {'id':2021,'name':'Premier League'}, ...}
TEAM_NAME_MAPPING = _dff.TEAM_NAME_MAPPING  # nombre API -> nombre BD, ya verificado

CSV_CODE_TO_LEAGUE_ID = {"E0": 1, "SP1": 2, "D1": 4, "I1": 3}

API_BASE_URL = "https://api.football-data.org/v4"


def fetch_teams(api_key: str, competition_id: int) -> list[dict]:
    headers = {"X-Auth-Token": api_key}
    url = f"{API_BASE_URL}/competitions/{competition_id}/teams"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("teams", [])


def main() -> None:
    api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")
    if not api_key:
        print("❌ Falta FOOTBALL_DATA_ORG_KEY")
        sys.exit(1)

    out: dict[str, list[dict]] = {}
    for csv_code, info in LEAGUE_MAPPING.items():
        league_id = CSV_CODE_TO_LEAGUE_ID[csv_code]
        print(f"Descargando equipos de {info['name']} (competition_id={info['id']})...")
        try:
            teams = fetch_teams(api_key, info["id"])
        except Exception as e:
            print(f"  ❌ Error: {e}")
            out[str(league_id)] = []
            continue

        mapped = []
        for t in teams:
            api_name = t.get("name")
            crest = t.get("crest")
            db_name = TEAM_NAME_MAPPING.get(api_name)
            if not db_name:
                print(f"  ⚠️  Sin mapeo para '{api_name}' — se omite (agregar a TEAM_NAME_MAPPING si hace falta)")
                continue
            if not crest:
                print(f"  ⚠️  '{api_name}' no trae escudo")
                continue
            mapped.append({"db_name": db_name, "api_name": api_name, "crest": crest})

        print(f"  {len(mapped)}/{len(teams)} equipos con escudo y nombre mapeado")
        out[str(league_id)] = mapped

    output_path = Path("data/football_data_org_logos.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado en {output_path}")


if __name__ == "__main__":
    main()
