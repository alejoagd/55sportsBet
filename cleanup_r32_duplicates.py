"""
cleanup_r32_duplicates.py
Elimina partidos R32 duplicados causados por diferencia horaria UTC vs local.

ESPN devuelve el mismo partido bajo dos consultas de fecha (ej: 29 jun local = 30 jun UTC),
lo que puede insertar el mismo partido dos veces con fechas distintas.

Este script mantiene el registro con la fecha MÁS TEMPRANA (fecha local US) y elimina el duplicado.

Uso:
  python cleanup_r32_duplicates.py
  python cleanup_r32_duplicates.py --dry-run
"""
from __future__ import annotations
import sys
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76
WC_R32_START = "2026-06-28"


def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "ELIMINANDO DUPLICADOS"
    print("=" * 60)
    print(f"  WC 2026 R32 Cleanup — {mode}")
    print("=" * 60)

    with engine.begin() as conn:
        # Encontrar grupos de partidos con los mismos equipos en el período R32
        dupes = conn.execute(text("""
            SELECT th.name AS home, ta.name AS away,
                   array_agg(m.id ORDER BY m.date, m.id)   AS ids,
                   array_agg(m.date::text ORDER BY m.date) AS dates,
                   array_agg(m.home_goals ORDER BY m.date) AS goals
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            WHERE m.season_id = :sid AND m.date >= :start
            GROUP BY th.name, ta.name
            HAVING COUNT(*) > 1
        """), {"sid": WC_2026_SEASON_ID, "start": WC_R32_START}).fetchall()

        if not dupes:
            print("\n✅ No se encontraron duplicados.")
            return

        print(f"\n🔍 Duplicados encontrados: {len(dupes)}\n")
        total_deleted = 0

        for row in dupes:
            print(f"  {row.home} vs {row.away}")
            print(f"    Fechas: {row.dates}")
            print(f"    IDs:    {row.ids}")
            print(f"    Goles:  {row.goals}")

            # Estrategia: mantener el primero (fecha más temprana = fecha local US)
            # Eliminar todos los demás (fechas UTC)
            ids_to_delete = row.ids[1:]  # todos excepto el primero (más temprano)

            for del_id in ids_to_delete:
                label = "[DRY]" if dry_run else "🗑️ "
                idx = row.ids.index(del_id)
                print(f"    {label} Eliminando id={del_id} (fecha={row.dates[idx]})")
                if not dry_run:
                    # Eliminar predicciones asociadas primero
                    conn.execute(text(
                        "DELETE FROM poisson_predictions WHERE match_id = :mid"
                    ), {"mid": del_id})
                    conn.execute(text(
                        "DELETE FROM weinston_predictions WHERE match_id = :mid"
                    ), {"mid": del_id})
                    # Eliminar match_stats si existe
                    conn.execute(text(
                        "DELETE FROM match_stats WHERE match_id = :mid"
                    ), {"mid": del_id})
                    conn.execute(text(
                        "DELETE FROM matches WHERE id = :mid"
                    ), {"mid": del_id})
                total_deleted += 1
            print()

    print("=" * 60)
    print(f"  Duplicados eliminados: {total_deleted}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
