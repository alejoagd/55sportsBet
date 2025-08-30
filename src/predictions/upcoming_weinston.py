# src/predictions/upcoming_weinston.py
from __future__ import annotations
import math
from typing import List, Tuple, Dict
from sqlalchemy import text
from .upcoming_core import load_team_strengths, load_team_stat_profiles

def _poisson_pmf(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def _aggregate_probs(lh: float, la: float, max_goals: int = 12) -> Dict[str, float]:
    p_h = [_poisson_pmf(lh, k) for k in range(max_goals + 1)]
    p_a = [_poisson_pmf(la, k) for k in range(max_goals + 1)]
    rem_h = 1.0 - sum(p_h); rem_a = 1.0 - sum(p_a)
    if rem_h > 1e-12: p_h[-1] += rem_h
    if rem_a > 1e-12: p_a[-1] += rem_a

    home = draw = away = over25 = btts = 0.0
    for i, ph in enumerate(p_h):
        for j, pa in enumerate(p_a):
            pij = ph * pa
            if i > j: home += pij
            elif i == j: draw += pij
            else: away += pij
            if i + j >= 3: over25 += pij
            if i >= 1 and j >= 1: btts += pij

    return {"pH": home, "pD": draw, "pA": away, "pO25": over25, "pBTTS": btts}

def predict_and_upsert_weinston(conn, season_id: int, match_ids: List[int], threshold: float = 0.5) -> None:
    # 1) λ desde Poisson (si existen); si faltan, calculamos con strengths
    q_lam = text("""
        SELECT match_id, expected_home_goals, expected_away_goals
        FROM poisson_predictions
        WHERE match_id = ANY(:ids)
    """)
    lam_by_mid: Dict[int, Tuple[float, float]] = {
        int(mid): (float(ehg), float(eag))
        for mid, ehg, eag in conn.execute(q_lam, {"ids": match_ids})
        if ehg is not None and eag is not None
    }
    missing = [m for m in match_ids if m not in lam_by_mid]
    if missing:
        strengths, lg_home_gf, lg_away_gf, HFA = load_team_strengths(conn, season_id)
        q_m = text("SELECT id, home_team_id, away_team_id FROM matches WHERE id = ANY(:ids)")
        for mid, h, a in conn.execute(q_m, {"ids": missing}).fetchall():
            sh = strengths.get(h); sa = strengths.get(a)
            if sh and sa:
                lh = lg_home_gf * sh["attack_home"] * sa["defense_away"] * HFA
                la = lg_away_gf * sa["attack_away"] * sh["defense_home"]
            else:
                lh = lg_home_gf * HFA; la = lg_away_gf
            lam_by_mid[int(mid)] = (float(lh), float(la))

    # 2) Perfiles de stats (histórico)
    profiles, league_means = load_team_stat_profiles(conn, n_recent=20)

    def _exp_stat(stat: str, home_id: int, away_id: int):
        """
        Combina perfil ofensivo del local (home_for) con defensivo del visitante (away_against) y viceversa.
        60% for + 40% against; fallback a promedio liga si falta.
        """
        # Home esperado
        ph = profiles.get(home_id, {}).get(stat, {})
        pa = profiles.get(away_id, {}).get(stat, {})
        lg = league_means.get(stat, 0.0)
        home_val = 0.6 * float(ph.get("home_for", lg)) + 0.4 * float(pa.get("away_against", lg))
        # Away esperado
        ph2 = profiles.get(away_id, {}).get(stat, {})
        pa2 = profiles.get(home_id, {}).get(stat, {})
        away_val = 0.6 * float(ph2.get("away_for", lg)) + 0.4 * float(pa2.get("home_against", lg))
        return home_val, away_val

    upsert = text("""
        INSERT INTO weinston_predictions
            (match_id,
             local_goals, away_goals, result_1x2, over_2, both_score,
             shots_home, shots_away, shots_target_home, shots_target_away,
             fouls_home, fouls_away, cards_home, cards_away,
             corners_home, corners_away, win_corners)
        VALUES
            (:mid, :lg, :ag, :r1x2, :over2, :btts,
             :sh, :sa, :sth, :sta, :fh, :fa, :ch, :ca, :coh, :coa, :wc)
        ON CONFLICT (match_id) DO UPDATE SET
            local_goals = EXCLUDED.local_goals,
            away_goals  = EXCLUDED.away_goals,
            result_1x2  = EXCLUDED.result_1x2,
            over_2      = EXCLUDED.over_2,
            both_score  = EXCLUDED.both_score,
            shots_home  = EXCLUDED.shots_home,
            shots_away  = EXCLUDED.shots_away,
            shots_target_home = EXCLUDED.shots_target_home,
            shots_target_away = EXCLUDED.shots_target_away,
            fouls_home  = EXCLUDED.fouls_home,
            fouls_away  = EXCLUDED.fouls_away,
            cards_home  = EXCLUDED.cards_home,
            cards_away  = EXCLUDED.cards_away,
            corners_home = EXCLUDED.corners_home,
            corners_away = EXCLUDED.corners_away,
            win_corners  = EXCLUDED.win_corners
    """)

    # 3) Proceso por match
    q_ids = text("SELECT id, home_team_id, away_team_id FROM matches WHERE id = ANY(:ids)")
    for mid, home_id, away_id in conn.execute(q_ids, {"ids": match_ids}).fetchall():
        lh, la = lam_by_mid[int(mid)]
        pr = _aggregate_probs(lh, la)

        # goles esperados para tu esquema (guardamos los λ)
        lg, ag = float(lh), float(la)

        # resultado 1X2
        if pr["pH"] >= pr["pD"] and pr["pH"] >= pr["pA"]:
            r1x2 = 1
        elif pr["pD"] >= pr["pH"] and pr["pD"] >= pr["pA"]:
            r1x2 = 0
        else:
            r1x2 = 2

        over2 = "OVER" if pr["pO25"] >= threshold else "UNDER"
        btts  = "YES"  if pr["pBTTS"] >= threshold else "NO"

        # Estadísticas adicionales (basadas en perfiles históricos)
        sh, sa   = _exp_stat("shots", home_id, away_id)
        sth, sta = _exp_stat("shots_target", home_id, away_id)
        fh, fa   = _exp_stat("fouls", home_id, away_id)
        ch, ca   = _exp_stat("cards", home_id, away_id)
        coh, coa = _exp_stat("corners", home_id, away_id)
        wc = "HOME" if coh > coa else ("AWAY" if coa > coh else "TIE")

        conn.execute(upsert, {
            "mid": int(mid),
            "lg": lg, "ag": ag,
            "r1x2": int(r1x2),
            "over2": over2, "btts": btts,
            "sh": float(sh), "sa": float(sa),
            "sth": float(sth), "sta": float(sta),
            "fh": float(fh), "fa": float(fa),
            "ch": float(ch), "ca": float(ca),
            "coh": float(coh), "coa": float(coa),
            "wc": wc,
        })
