"""
Corrige fechas incorrectas de los partidos del Mundial 2026 (season_id=76).

Ejecutar en Render Shell:
  python fix_wc2026_dates.py

Para revisar qué cambiaría sin tocar la BD:
  python fix_wc2026_dates.py --dry-run
"""
from __future__ import annotations
import sys
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76

# ── Correcciones confirmadas ─────────────────────────────────────────────────
# Formato: (home_team, away_team, fecha_incorrecta, fecha_correcta)
# Añade más líneas si encuentras otros partidos con fechas erróneas.
FIXES: list[tuple[str, str, str, str]] = [
    ("Qatar",   "Switzerland", "2026-06-12", "2026-06-13"),
    ("Mexico",  "South Korea", "2026-06-17", "2026-06-18"),
    ("Brazil",        "Haiti",     "2026-06-18", "2026-06-19"),
    ("United States", "Australia",  "2026-06-18", "2026-06-19"),
    ("Germany",       "Curacao",    "2026-06-13", "2026-06-14"),
    ("Germany",       "Ivory Coast",  "2026-06-19", "2026-06-20"),
    ("Netherlands",   "Sweden",       "2026-06-19", "2026-06-20"),
    ("Belgium",       "Iran",         "2026-06-20", "2026-06-21"),
    ("Spain",         "Saudi Arabia", "2026-06-20", "2026-06-21"),
    ("France",        "Iraq",         "2026-06-21", "2026-06-22"),
    ("Argentina",     "Austria",      "2026-06-21", "2026-06-22"),
    ("Portugal",      "Uzbekistan",   "2026-06-22", "2026-06-23"),
    ("England",       "Ghana",        "2026-06-22", "2026-06-23"),
    # Añade aquí más correcciones si encuentras otras fechas erróneas:
    # ("TeamA", "TeamB", "2026-06-XX", "2026-06-YY"),
]


def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "APLICANDO CAMBIOS"
    print(f"{'='*60}")
    print(f"  Fix fechas WC 2026 — {mode}")
    print(f"{'='*60}\n")

    with engine.begin() as conn:
        for home, away, old_date, new_date in FIXES:
            row = conn.execute(text("""
                SELECT m.id, m.date, ht.name as home_team, at.name as away_team
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE m.season_id = :sid
                  AND ht.name = :home
                  AND at.name = :away
            """), {"sid": WC_2026_SEASON_ID, "home": home, "away": away}).fetchone()

            if not row:
                print(f"  ⚠️  No encontrado: {home} vs {away}")
                continue

            current = str(row.date)
            if current != old_date:
                print(f"  ℹ️  {home} vs {away}: fecha actual={current} "
                      f"(esperada {old_date}), se dejará como está")
                continue

            print(f"  {'[DRY]' if dry_run else '✅'} {home} vs {away}: "
                  f"{old_date} → {new_date}")

            if not dry_run:
                conn.execute(text("""
                    UPDATE matches SET date = :new_date
                    WHERE id = :mid
                """), {"new_date": new_date, "mid": row.id})

    print(f"\n{'='*60}")
    if dry_run:
        print("  Dry run completado. Nada fue modificado.")
    else:
        print("  Fechas corregidas en BD.")
    print(f"{'='*60}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
