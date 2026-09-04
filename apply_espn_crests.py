"""
apply_espn_crests.py
Escribe logo_url en teams para Copa Libertadores y Copa Sudamericana, a
partir del JSON generado por scripts/fetch_espn_crests.py (corrido en
GitHub Actions, ver el input `fetch_espn_crests` del workflow
update-predictions.yml).

Los equipos ya están linkeados a ESPN vía team_external_ids (fueron
cargados por update_competitions_espn_sync.py), así que el match es
directo por espn_id -> team_id, sin ambigüedad de nombres.

(El Mundial no necesita esto: su tabla de posiciones ya muestra bandera
por selección vía TEAM_FLAG en el frontend, no depende de logo_url.)

Uso:
  python apply_espn_crests.py data/espn_crests.json                # dry-run
  python apply_espn_crests.py data/espn_crests.json --apply
"""
from __future__ import annotations
import argparse
import json

from sqlalchemy import text

from src.db import engine

SLUG_LABELS = {
    "conmebol.libertadores": "Copa Libertadores",
    "conmebol.sudamericana": "Copa Sudamericana",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica escudos de ESPN para Libertadores/Sudamericana")
    parser.add_argument("json_path", help="Ruta al JSON generado por fetch_espn_crests.py")
    parser.add_argument("--apply", action="store_true", help="Escribe logo_url (si no se pasa, solo imprime el reporte)")
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        data = json.load(f)

    with engine.begin() as conn:
        for slug, teams in data.items():
            print(f"\n{'='*70}\n  {SLUG_LABELS.get(slug, slug)}\n{'='*70}")
            if not teams:
                print("   (sin datos en el JSON para esta competencia)")
                continue

            updated = not_found = no_logo = 0
            for t in teams:
                if not t.get("logo"):
                    no_logo += 1
                    continue
                row = conn.execute(
                    text("SELECT team_id FROM team_external_ids WHERE source='espn' AND external_id=:eid"),
                    {"eid": t["espn_id"]},
                ).fetchone()
                if not row:
                    print(f"   ❌ espn_id={t['espn_id']} ({t['name']}) sin team_external_ids")
                    not_found += 1
                    continue
                print(f"   ✅ {t['name']:<30} {t['logo']}")
                if args.apply:
                    conn.execute(text("UPDATE teams SET logo_url = :logo WHERE id = :tid"), {"logo": t["logo"], "tid": row[0]})
                updated += 1

            print(f"   -> {updated} {'actualizados' if args.apply else 'para actualizar'}, {not_found} sin encontrar, {no_logo} sin logo en ESPN")

    if not args.apply:
        print("\nDRY-RUN — nada se escribió. Revisar el reporte y correr con --apply cuando esté OK.")
    print("\nListo.")


if __name__ == "__main__":
    main()
