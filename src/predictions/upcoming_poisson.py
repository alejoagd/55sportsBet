from __future__ import annotations
import math
from typing import List, Tuple, Dict
from sqlalchemy import text
from .upcoming_core import load_team_strengths

def _poisson_pmf(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def _aggregate_probs(lh: float, la: float, max_goals: int = 12) -> Dict[str, float]:
    """Suma de la matriz Poisson truncada (0..max_goals) con cola en el último bucket."""
    p_h = [_poisson_pmf(lh, k) for k in range(max_goals + 1)]
    p_a = [_poisson_pmf(la, k) for k in range(max_goals + 1)]
    rem_h = 1.0 - sum(p_h)
    rem_a = 1.0 - sum(p_a)
    if rem_h > 1e-12:
        p_h[-1] += rem_h
    if rem_a > 1e-12:
        p_a[-1] += rem_a

    home = draw = away = over25 = btts = 0.0
    for i, ph in enumerate(p_h):
        for j, pa in enumerate(p_a):
            pij = ph * pa
            if i > j:
                home += pij
            elif i == j:
                draw += pij
            else:
                away += pij
            if i + j >= 3:  # umbral 2.5
                over25 += pij
            if i >= 1 and j >= 1:
                btts += pij

    under25 = max(0.0, 1.0 - over25)
    nbtts = max(0.0, 1.0 - btts)
    return {
        "pH": home, "pD": draw, "pA": away,
        "pO25": over25, "pU25": under25,
        "pBTTS": btts, "pNBTS": nbtts,
    }

def predict_and_upsert_poisson(conn, season_id: int, match_ids: List[int]) -> None:
    strengths, lg_home_gf, lg_away_gf, HFA = load_team_strengths(conn, season_id)

    q_matches = text("""
        SELECT id, home_team_id, away_team_id
        FROM matches
        WHERE id = ANY(:ids)
    """)
    rows = conn.execute(q_matches, {"ids": match_ids}).fetchall()

    upsert = text("""
        INSERT INTO poisson_predictions
            (match_id,
             expected_home_goals, expected_away_goals,
             prob_home_win, prob_draw, prob_away_win,
             over_2, under_2, both_score, both_noscore)
        VALUES
            (:mid, :ehg, :eag, :pH, :pD, :pA, :pO25, :pU25, :pBTTS, :pNBTS)
        ON CONFLICT (match_id) DO UPDATE SET
            expected_home_goals = EXCLUDED.expected_home_goals,
            expected_away_goals = EXCLUDED.expected_away_goals,
            prob_home_win       = EXCLUDED.prob_home_win,
            prob_draw           = EXCLUDED.prob_draw,
            prob_away_win       = EXCLUDED.prob_away_win,
            over_2              = EXCLUDED.over_2,
            under_2             = EXCLUDED.under_2,
            both_score          = EXCLUDED.both_score,
            both_noscore        = EXCLUDED.both_noscore
    """)

    for mid, h, a in rows:
        sh = strengths.get(h); sa = strengths.get(a)
        if not sh or not sa:
            lam_h = lg_home_gf * HFA
            lam_a = lg_away_gf
        else:
            lam_h = lg_home_gf * sh["attack_home"] * sa["defense_away"] * HFA
            lam_a = lg_away_gf * sa["attack_away"] * sh["defense_home"]

        probs = _aggregate_probs(lam_h, lam_a)

        conn.execute(upsert, {
            "mid": int(mid),
            "ehg": float(lam_h), "eag": float(lam_a),
            **probs
        })
