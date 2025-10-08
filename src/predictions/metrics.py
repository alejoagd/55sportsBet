# src/predictions/metrics.py
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from src.db import engine

def metrics_by_model(
    season_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sql = """
    SELECT
      po.model,

      COUNT(*) FILTER (WHERE po.hit_1x2 IS NOT NULL)                 AS decided_1x2,
      COUNT(*) FILTER (WHERE po.hit_1x2 IS TRUE)                     AS hits_1x2,
      CASE WHEN COUNT(*) FILTER (WHERE po.hit_1x2 IS NOT NULL) > 0
           THEN AVG((po.hit_1x2)::int)::float ELSE NULL END         AS acc_1x2,

      COUNT(*) FILTER (WHERE po.hit_over25 IS NOT NULL)              AS decided_over25,
      COUNT(*) FILTER (WHERE po.hit_over25 IS TRUE)                  AS hits_over25,
      CASE WHEN COUNT(*) FILTER (WHERE po.hit_over25 IS NOT NULL) > 0
           THEN AVG((po.hit_over25)::int)::float ELSE NULL END      AS acc_over25,

      COUNT(*) FILTER (WHERE po.hit_btts IS NOT NULL)                AS decided_btts,
      COUNT(*) FILTER (WHERE po.hit_btts IS TRUE)                    AS hits_btts,
      CASE WHEN COUNT(*) FILTER (WHERE po.hit_btts IS NOT NULL) > 0
           THEN AVG((po.hit_btts)::int)::float ELSE NULL END        AS acc_btts,

      AVG(po.rmse_goals)                                            AS avg_rmse_goals
    FROM prediction_outcomes po
    JOIN matches m ON m.id = po.match_id
    WHERE m.season_id = :season_id
      AND (:date_from IS NULL OR m.date >= :date_from)
      AND (:date_to   IS NULL OR m.date <= :date_to)
    GROUP BY po.model
    ORDER BY po.model;
    """
    with engine.begin() as conn:
        rows = conn.execute(
            text(sql),
            {"season_id": season_id, "date_from": date_from, "date_to": date_to}
        ).mappings().all()
        return [dict(r) for r in rows]
