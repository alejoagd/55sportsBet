"""
Completa el error de goles (abs_err_home/away y rmse_goals) de Poisson en
prediction_outcomes.

Por qué: evaluate.py guardaba esos campos en NULL para Poisson (solo Weinston
tenía), así que la métrica "RMSE Goles" no se podía comparar entre modelos. Los
goles esperados de Poisson ya están en poisson_predictions.

Qué hace: SOLO rellena las filas de Poisson con rmse_goals NULL, con la misma
fórmula que Weinston: sqrt(((esp_local - gol_local)² + (esp_visit - gol_visit)²) / 2).
No cambia ningún valor ya guardado ni toca hit_*/pick_*. Antes de escribir
compara la fórmula contra las filas que ya tenían valor, para confirmar que
coincide.

Uso (por defecto SIMULA y no escribe):
  python -m src.scripts.backfill_poisson_rmse
  python -m src.scripts.backfill_poisson_rmse --apply

Se niega a correr contra una BD que no sea local, salvo --allow-remote.
"""
from __future__ import annotations
import argparse
import sys

from sqlalchemy import text

from src.db import engine

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}

# Universo: filas de Poisson con partido terminado y goles esperados guardados
_BASE = """
    FROM prediction_outcomes po
    JOIN poisson_predictions pp ON pp.match_id = po.match_id
    JOIN matches m ON m.id = po.match_id
    WHERE po.model = 'poisson'
      AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
      AND pp.expected_home_goals IS NOT NULL AND pp.expected_away_goals IS NOT NULL
"""
_RMSE = ("SQRT((POWER(pp.expected_home_goals - m.home_goals, 2) "
         "+ POWER(pp.expected_away_goals - m.away_goals, 2)) / 2.0)")


def count_missing(conn) -> int:
    return conn.execute(text(f"SELECT COUNT(*) {_BASE} AND po.rmse_goals IS NULL")).scalar_one()


def check_consistency(conn) -> tuple[int, float]:
    """(filas que ya tenían rmse, mayor diferencia contra la fórmula)."""
    row = conn.execute(text(f"""
        SELECT COUNT(*), COALESCE(MAX(ABS(po.rmse_goals - {_RMSE})), 0)
        {_BASE} AND po.rmse_goals IS NOT NULL
    """)).one()
    return row[0], float(row[1])


def fill_missing(conn) -> int:
    res = conn.execute(text(f"""
        UPDATE prediction_outcomes po
        SET abs_err_home_goals = ABS(pp.expected_home_goals - m.home_goals),
            abs_err_away_goals = ABS(pp.expected_away_goals - m.away_goals),
            rmse_goals = {_RMSE},
            updated_at = now()
        FROM poisson_predictions pp, matches m
        WHERE po.model = 'poisson' AND po.rmse_goals IS NULL
          AND pp.match_id = po.match_id AND m.id = po.match_id
          AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
          AND pp.expected_home_goals IS NOT NULL AND pp.expected_away_goals IS NOT NULL
    """))
    return res.rowcount


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Escribe los cambios (por defecto solo simula)")
    ap.add_argument("--allow-remote", action="store_true", help="Permite correr contra una BD no local")
    args = ap.parse_args()

    host = engine.url.host
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"⛔ La BD configurada es '{host}' (no local). Abortado: usa --allow-remote solo si es intencional.")
        return 2
    print(f"BD: {host or 'socket local'}/{engine.url.database} · modo: {'APLICAR' if args.apply else 'SIMULACIÓN'}")

    with engine.begin() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) {_BASE}")).scalar_one()
        with_value, max_diff = check_consistency(conn)
        missing = count_missing(conn)
        print(f"Filas de Poisson con partido terminado y goles esperados: {total}")
        print(f"  ya tenían rmse: {with_value} (mayor diferencia contra la fórmula: {max_diff:.6f})")
        print(f"  sin rmse (se rellenarán): {missing}")
        if max_diff > 1e-3:
            print("⛔ La fórmula NO coincide con los valores ya guardados: no se escribe nada. Revisar antes de seguir.")
            return 1
        if args.apply and missing:
            n = fill_missing(conn)
            print(f"✅ Filas actualizadas: {n}")
        elif not args.apply:
            print("ℹ️  Simulación: no se escribió nada. Repite con --apply para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
