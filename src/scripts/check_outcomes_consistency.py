"""
Verifica (solo lectura) que los aciertos guardados en prediction_outcomes coincidan con
el resultado real del partido.

Por qué: evaluate() calculó durante meses los aciertos con los goles predichos de
Weinston en vez de los reales (colisión del nombre `away_goals` en el SELECT) y
nadie lo notó, porque la pantalla de Evolución mostraba porcentajes plausibles.
Este chequeo recalcula 1X2, Over 2.5 y BTTS desde `matches` y cuenta las filas que
discrepan. Termina con código 1 si hay alguna, para poder usarlo como guardia.

Uso:
  python -m src.scripts.check_outcomes_consistency
  ENV_FILE=.env.production python -m src.scripts.check_outcomes_consistency
"""
from __future__ import annotations
import sys

from sqlalchemy import text

from src.db import engine

CHECK = """
SELECT po.model, count(*) AS n,
  sum((po.hit_1x2 IS DISTINCT FROM (po.pick_1x2 = CASE WHEN m.home_goals > m.away_goals THEN '1'
        WHEN m.home_goals < m.away_goals THEN '2' ELSE 'X' END))::int) AS x12_mal,
  sum((po.hit_over25 IS DISTINCT FROM (po.pick_over25 = CASE WHEN m.home_goals + m.away_goals >= 3
        THEN 'OVER' ELSE 'UNDER' END))::int) AS over_mal,
  sum((po.hit_btts IS DISTINCT FROM (po.pick_btts = CASE WHEN m.home_goals > 0 AND m.away_goals > 0
        THEN 'YES' ELSE 'NO' END))::int) AS btts_mal
FROM prediction_outcomes po JOIN matches m ON m.id = po.match_id
WHERE m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
GROUP BY po.model ORDER BY po.model
"""

HUERFANAS = """
SELECT count(*) FROM prediction_outcomes po
WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.id = po.match_id)
"""


def main() -> int:
    print(f"BD: {engine.url.host or 'socket local'}/{engine.url.database} (solo lectura)")
    malas = 0
    with engine.connect() as conn:
        for modelo, n, x12, over, btts in conn.execute(text(CHECK)).all():
            print(f"  {modelo:<9} filas={n:<6} 1X2 mal={x12}  O/U mal={over}  BTTS mal={btts}")
            malas += (x12 or 0) + (over or 0) + (btts or 0)
        huerfanas = conn.execute(text(HUERFANAS)).scalar_one()
        print(f"  filas de prediction_outcomes sin partido: {huerfanas}")
    ok = malas == 0 and huerfanas == 0
    print("✅ Consistente." if ok else "⛔ Hay aciertos que no coinciden con el resultado real.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
