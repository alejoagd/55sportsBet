"""
apply_team_logos.py
Escribe logo_url en la tabla teams a partir del JSON generado por
scripts/fetch_football_data_org_logos.py (corrido en GitHub Actions, ver
el input `fetch_team_logos` del workflow update-predictions.yml).

A diferencia del intento anterior con ESPN (fuzzy matching por similitud
de nombre, nunca llegó a aplicarse porque ESPN bloquea/rate-limita estas
4 ligas de alto tráfico), acá el nombre ya viene mapeado 1:1 al nombre
exacto de nuestra BD (mismo TEAM_NAME_MAPPING que ya usa
download-fixtures-final.py para cargar el calendario) — no hace falta
puntaje de confianza, es un UPDATE directo por nombre exacto + league_id.

Uso:
  python apply_team_logos.py data/football_data_org_logos.json                # dry-run
  python apply_team_logos.py data/football_data_org_logos.json --apply
"""
from __future__ import annotations
import argparse
import json

from sqlalchemy import text

from src.db import engine

LEAGUE_NAMES = {1: "Premier League", 2: "La Liga", 3: "Serie A", 4: "Bundesliga"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica escudos descargados de football-data.org")
    parser.add_argument("json_path", help="Ruta al JSON generado por fetch_football_data_org_logos.py")
    parser.add_argument("--apply", action="store_true", help="Escribe logo_url (si no se pasa, solo imprime el reporte)")
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        data = json.load(f)

    for league_id_str, teams in data.items():
        league_id = int(league_id_str)
        print(f"\n{'='*70}\n  {LEAGUE_NAMES.get(league_id, league_id)}\n{'='*70}")

        if not teams:
            print("   (sin datos en el JSON para esta liga)")
            continue

        with engine.begin() as conn:
            db_teams = {
                row.name: row.id
                for row in conn.execute(
                    text("SELECT id, name FROM teams WHERE league_id = :lid"), {"lid": league_id}
                ).fetchall()
            }

        updated = not_found = 0
        for t in teams:
            db_name = t["db_name"]
            crest = t["crest"]
            team_id = db_teams.get(db_name)
            if team_id is None:
                print(f"   ❌ {db_name!r} (de '{t['api_name']}') no existe en la BD para esta liga")
                not_found += 1
                continue

            print(f"   ✅ {db_name:<30} {crest}")
            if args.apply:
                with engine.begin() as conn:
                    conn.execute(text("UPDATE teams SET logo_url = :logo WHERE id = :tid"), {"logo": crest, "tid": team_id})
            updated += 1

        print(f"   -> {updated} {'actualizados' if args.apply else 'para actualizar'}, {not_found} sin encontrar en la BD")

    if not args.apply:
        print("\nDRY-RUN — nada se escribió. Revisar el reporte y correr con --apply cuando esté OK.")
    print("\nListo.")


if __name__ == "__main__":
    main()
