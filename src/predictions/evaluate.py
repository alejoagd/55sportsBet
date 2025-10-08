from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from math import sqrt
from sqlalchemy import text
from src.db import engine

def _res_1x2(hg: int, ag: int) -> str:
    if hg > ag: return "1"
    if hg < ag: return "2"
    return "X"

def _over25(hg: int, ag: int) -> str:
    return "OVER" if (hg + ag) > 2 else "UNDER"

def _btts(hg: int, ag: int) -> str:
    return "YES" if (hg > 0 and ag > 0) else "NO"

def _argmax_1x2(ph: float, px: float, pa: float) -> str:
    m = max(ph, px, pa)
    if m == ph: return "1"
    if m == px: return "X"
    return "2"

def evaluate(
    season_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    pick_over_thresh: float = 0.5,
    pick_btts_thresh: float = 0.5,
    only_matches: Optional[List[int]] = None,
) -> Dict[str, int]:
    """
    Crea/actualiza prediction_outcomes para ambos modelos.
    Umbrales para Poisson:
      - Over/Under: OVER si pp.over_2 >= pick_over_thresh
      - BTTS: YES si pp.both_score >= pick_btts_thresh
    """
    base = """
    SELECT
      m.id AS mid, m.season_id, m.date, m.home_goals, m.away_goals,

      -- Poisson
      pp.prob_home_win, pp.prob_draw, pp.prob_away_win,
      pp.over_2, pp.under_2, pp.both_score, pp.both_noscore,

      -- Weinston
      wp.local_goals, wp.away_goals,
      wp.result_1x2,                  -- 1: home, 0: draw?, 2: away
      wp.over_2 AS win_over2,         -- 'OVER'/'UNDER'
      wp.both_score AS win_btts       -- 'YES'/'NO'
    FROM matches m
    LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
    LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
    WHERE m.season_id = :season_id
      AND m.home_goals IS NOT NULL
      AND m.away_goals IS NOT NULL
    """
    params: Dict[str, Any] = {"season_id": season_id}
    if date_from:
        base += " AND m.date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        base += " AND m.date <= :date_to"
        params["date_to"] = date_to
    if only_matches:
        base += " AND m.id = ANY(:ids)"
        params["ids"] = only_matches
    base += " ORDER BY m.date, m.id"

    upsert = text("""
      INSERT INTO prediction_outcomes (
        match_id, model,
        pick_1x2, hit_1x2,
        pick_over25, hit_over25,
        pick_btts, hit_btts,
        abs_err_home_goals, abs_err_away_goals, rmse_goals,
        updated_at
      )
      VALUES (
        :mid, :model,
        :p1x2, :h1x2,
        :pover, :hover,
        :pbtts, :hbtts,
        :ae_h, :ae_a, :rmse,
        now()
      )
      ON CONFLICT (match_id, model) DO UPDATE SET
        pick_1x2 = EXCLUDED.pick_1x2,
        hit_1x2 = EXCLUDED.hit_1x2,
        pick_over25 = EXCLUDED.pick_over25,
        hit_over25 = EXCLUDED.hit_over25,
        pick_btts = EXCLUDED.pick_btts,
        hit_btts = EXCLUDED.hit_btts,
        abs_err_home_goals = EXCLUDED.abs_err_home_goals,
        abs_err_away_goals = EXCLUDED.abs_err_away_goals,
        rmse_goals = EXCLUDED.rmse_goals,
        updated_at = now();
    """)

    counters = {"poisson": 0, "weinston": 0}

    with engine.begin() as conn:
        rows = conn.execute(text(base), params).mappings().all()
        for r in rows:
            mid = r["mid"]
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
            act_1x2 = _res_1x2(hg, ag)
            act_over = _over25(hg, ag)
            act_btts = _btts(hg, ag)

            # --- POISSON ---
            if r["prob_home_win"] is not None:
                ph = float(r["prob_home_win"] or 0.0)
                px = float(r["prob_draw"] or 0.0)
                pa = float(r["prob_away_win"] or 0.0)
                p_over = float(r["over_2"] or 0.0)
                p_btts = float(r["both_score"] or 0.0)

                pick_1x2 = _argmax_1x2(ph, px, pa)
                pick_over = "OVER" if p_over >= pick_over_thresh else "UNDER"
                pick_btts = "YES" if p_btts >= pick_btts_thresh else "NO"

                conn.execute(upsert, {
                    "mid": mid, "model": "poisson",
                    "p1x2": pick_1x2, "h1x2": (pick_1x2 == act_1x2),
                    "pover": pick_over, "hover": (pick_over == act_over),
                    "pbtts": pick_btts, "hbtts": (pick_btts == act_btts),
                    "ae_h": None, "ae_a": None, "rmse": None
                })
                counters["poisson"] += 1

            # --- WEINSTON ---
            if r["local_goals"] is not None:
                lh = float(r["local_goals"] or 0.0)
                la = float(r["away_goals"] or 0.0)
                # mapear enteros a '1','X','2'
                wr = r["result_1x2"]
                if wr is None:
                    pick_w_1x2 = None
                else:
                    pick_w_1x2 = "1" if wr == 1 else ("2" if wr == 2 else "X")
                pick_w_over = (r["win_over2"] or "").upper() or None
                pick_w_btts = (r["win_btts"] or "").upper() or None

                ae_h = abs(lh - hg)
                ae_a = abs(la - ag)
                rmse = sqrt(((lh - hg) ** 2 + (la - ag) ** 2) / 2.0)

                conn.execute(upsert, {
                    "mid": mid, "model": "weinston",
                    "p1x2": pick_w_1x2, "h1x2": (pick_w_1x2 == act_1x2) if pick_w_1x2 else None,
                    "pover": pick_w_over, "hover": (pick_w_over == act_over) if pick_w_over else None,
                    "pbtts": pick_w_btts, "hbtts": (pick_w_btts == act_btts) if pick_w_btts else None,
                    "ae_h": ae_h, "ae_a": ae_a, "rmse": rmse
                })
                counters["weinston"] += 1

    return counters
