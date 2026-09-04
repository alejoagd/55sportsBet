"""
apply_espn_crests.py
Escribe logo_url en teams para Copa Libertadores, Copa Sudamericana y el
Mundial 2026, a partir del JSON generado por scripts/fetch_espn_crests.py
(corrido en GitHub Actions, ver el input `fetch_espn_crests` del workflow
update-predictions.yml).

Libertadores/Sudamericana: los equipos ya están linkeados a ESPN vía
team_external_ids (fueron cargados por update_competitions_espn_sync.py),
así que el match es directo por espn_id -> team_id, sin ambigüedad.

Mundial: los equipos (selecciones) se cargaron por un script separado sin
guardar su espn_id, así que acá el match es por nombre (WC_NAME_MAPPING
cuando el nombre de ESPN no coincide exacto con el de la BD).

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
    "fifa.world": "Mundial 2026",
}
SLUG_SEASON_ID = {
    "conmebol.libertadores": 105,
    "conmebol.sudamericana": 106,
    "fifa.world": 76,
}

# ESPN displayName -> nombre en nuestra BD, solo para las selecciones del
# Mundial cuyo nombre no coincide exacto (confirmado corriendo primero en
# dry-run y viendo qué quedó "sin encontrar").
WC_NAME_MAPPING: dict[str, str] = {
    "United States": "USA",
    "South Korea": "Korea Republic",
    "Ivory Coast": "Ivory Coast",
}


def apply_by_espn_id(conn, slug: str, teams: list[dict], apply: bool) -> None:
    updated = not_found = 0
    for t in teams:
        row = conn.execute(
            text("SELECT team_id FROM team_external_ids WHERE source='espn' AND external_id=:eid"),
            {"eid": t["espn_id"]},
        ).fetchone()
        if not row:
            print(f"   ❌ espn_id={t['espn_id']} ({t['name']}) sin team_external_ids")
            not_found += 1
            continue
        print(f"   ✅ {t['name']:<30} {t['logo']}")
        if apply:
            conn.execute(text("UPDATE teams SET logo_url = :logo WHERE id = :tid"), {"logo": t["logo"], "tid": row[0]})
        updated += 1
    print(f"   -> {updated} {'actualizados' if apply else 'para actualizar'}, {not_found} sin encontrar")


def apply_by_name(conn, slug: str, teams: list[dict], apply: bool) -> None:
    season_id = SLUG_SEASON_ID[slug]
    db_teams = {
        row.name: row.id
        for row in conn.execute(
            text("""
                SELECT DISTINCT t.id, t.name FROM teams t
                JOIN matches m ON t.id IN (m.home_team_id, m.away_team_id)
                WHERE m.season_id = :sid
            """),
            {"sid": season_id},
        ).fetchall()
    }
    updated = not_found = 0
    for t in teams:
        db_name = WC_NAME_MAPPING.get(t["name"], t["name"])
        team_id = db_teams.get(db_name)
        if team_id is None:
            print(f"   ❌ {db_name!r} (de '{t['name']}') no existe en la BD para esta competencia")
            not_found += 1
            continue
        print(f"   ✅ {db_name:<30} {t['logo']}")
        if apply:
            conn.execute(text("UPDATE teams SET logo_url = :logo WHERE id = :tid"), {"logo": t["logo"], "tid": team_id})
        updated += 1
    print(f"   -> {updated} {'actualizados' if apply else 'para actualizar'}, {not_found} sin encontrar")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica escudos de ESPN para Libertadores/Sudamericana/Mundial")
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
            if slug == "fifa.world":
                apply_by_name(conn, slug, teams, args.apply)
            else:
                apply_by_espn_id(conn, slug, teams, args.apply)

    if not args.apply:
        print("\nDRY-RUN — nada se escribió. Revisar el reporte y correr con --apply cuando esté OK.")
    print("\nListo.")


if __name__ == "__main__":
    main()
