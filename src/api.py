# api.py
from __future__ import annotations
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from src.config import settings  # usa tu settings.sqlalchemy_url
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from src.predictions.evaluate import evaluate
from src.predictions.metrics import metrics_by_model

app = FastAPI(title="Predictions API")

# CORS dev-friendly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)

@app.get("/api/predictions")
def get_predictions(
    season_id: int = Query(..., description="Season ID"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> List[Dict[str, Any]]:
    sql = """
    SELECT
      m.id                              AS match_id,
      m.date                            AS date,
      th.name                           AS home_team,
      ta.name                           AS away_team,

      -- Poisson
      pp.expected_home_goals,
      pp.expected_away_goals,
      pp.prob_home_win,
      pp.prob_draw,
      pp.prob_away_win,
      pp.over_2        AS poisson_over_2,
      pp.under_2       AS poisson_under_2,
      pp.both_score    AS poisson_both_score,
      pp.both_noscore  AS poisson_both_noscore,

      -- Weinston
      wp.local_goals,
      wp.away_goals,
      wp.result_1x2,
      wp.over_2        AS wein_over_2,
      wp.both_score    AS wein_both_score,
      wp.shots_home, wp.shots_away,
      wp.shots_target_home, wp.shots_target_away,
      wp.fouls_home, wp.fouls_away,
      wp.cards_home, wp.cards_away,
      wp.corners_home, wp.corners_away,
      wp.win_corners

    FROM matches m
    JOIN teams th ON th.id = m.home_team_id
    JOIN teams ta ON ta.id = m.away_team_id
    LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
    LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
    WHERE m.season_id = :season_id
    """
    params = {"season_id": season_id}
    if date_from:
        sql += " AND m.date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += " AND m.date <= :date_to"
        params["date_to"] = date_to
    sql += " ORDER BY m.date, m.id"

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/api/metrics")
def get_metrics(
    season_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sql = """
    SELECT
      po.model,
      COUNT(*) AS n,
      AVG(CASE WHEN po.hit_1x2 THEN 1 ELSE 0 END)::float AS acc_1x2,
      AVG(CASE WHEN po.hit_over25 THEN 1 ELSE 0 END)::float AS acc_over25,
      AVG(CASE WHEN po.hit_btts THEN 1 ELSE 0 END)::float AS acc_btts,
      AVG(po.rmse_goals)::float AS rmse_goals
    FROM prediction_outcomes po
    JOIN matches m ON m.id = po.match_id
    WHERE m.season_id = :season_id
    """
    params: Dict[str, Any] = {"season_id": season_id}
    if date_from:
        sql += " AND m.date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += " AND m.date <= :date_to"
        params["date_to"] = date_to
    sql += " GROUP BY po.model ORDER BY po.model"
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]

@app.post("/predictions/evaluate")
def run_evaluate(
    season_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    pick_over_thresh: float = 0.5,
    pick_btts_thresh: float = 0.5,
):
    counters = evaluate(
        season_id=season_id,
        date_from=date_from,
        date_to=date_to,
        pick_over_thresh=pick_over_thresh,
        pick_btts_thresh=pick_btts_thresh,
        only_matches=None,
    )
    return {"status": "ok", "counters": counters}

@app.get("/predictions/metrics")
def get_metrics(    
    season_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    rows = metrics_by_model(season_id=season_id, date_from=date_from, date_to=date_to)
    return {"season_id": season_id, "date_from": date_from, "date_to": date_to, "metrics": rows}
