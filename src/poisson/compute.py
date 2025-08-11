from __future__ import annotations
import numpy as np
from scipy.stats import poisson
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Tuple

from src.db import SessionLocal
from src.models import Match, MatchStats, PoissonPrediction, Team

# --- helpers ---

def xi(goals_for_avg: float, goals_against_avg: float, home: bool) -> float:
    home_adv = 1.1 if home else 1.0
    return max(0.01, goals_for_avg * goals_against_avg * 0.5 * home_adv)


def outcome_probs(lmb_home: float, lmb_away: float, max_goals: int = 10) -> tuple[float, float, float]:
    # P(H), P(D), P(A)
    p_home = p_draw = p_away = 0.0
    for hg in range(0, max_goals + 1):
        for ag in range(0, max_goals + 1):
            p = poisson.pmf(hg, lmb_home) * poisson.pmf(ag, lmb_away)
            if hg > ag:
                p_home += p
            elif hg == ag:
                p_draw += p
            else:
                p_away += p
    return p_home, p_draw, p_away


def over_under_25(lmb_home: float, lmb_away: float, max_goals: int = 10) -> tuple[float, float]:
    over = under = 0.0
    for hg in range(0, max_goals + 1):
        for ag in range(0, max_goals + 1):
            p = poisson.pmf(hg, lmb_home) * poisson.pmf(ag, lmb_away)
            if hg + ag > 2:
                over += p
            else:
                under += p
    return over, under


def both_teams_score(lmb_home: float, lmb_away: float, max_goals: int = 10) -> tuple[float, float]:
    yes = no = 0.0
    for hg in range(0, max_goals + 1):
        for ag in range(0, max_goals + 1):
            p = poisson.pmf(hg, lmb_home) * poisson.pmf(ag, lmb_away)
            if hg > 0 and ag > 0:
                yes += p
            else:
                no += p
    return yes, no


def compute_for_match(session: Session, match_id: int) -> PoissonPrediction:
    # estimar lambdas desde medias recientes; puedes refinar con tus métricas
    # para demo: usa 5 últimos partidos por equipo si existen en match_stats
    m: Match = session.get(Match, match_id)
    assert m, f"Match {match_id} no existe"

    # media simple de GF/GC por equipo (últimos 5)
    def avg_for_against(team_id: int, home: bool) -> tuple[float, float]:
        q = (
            session.query(MatchStats)
            .join(Match, MatchStats.match_id == Match.id)
            .filter((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
            .order_by(Match.date.desc())
            .limit(5)
        )
        rows = q.all()
        if not rows:
            return 1.2, 1.2  # fallback
        gf = []
        ga = []
        for r in rows:
            # necesitamos saber si el team fue home o away en ese match
            mt = session.get(Match, r.match_id)
            if mt.home_team_id == team_id:
                gf.append(r.home_goals or 0)
                ga.append(r.away_goals or 0)
            else:
                gf.append(r.away_goals or 0)
                ga.append(r.home_goals or 0)
        return (np.mean(gf) if gf else 1.2, np.mean(ga) if ga else 1.2)

    gf_h, ga_h = avg_for_against(m.home_team_id, home=True)
    gf_a, ga_a = avg_for_against(m.away_team_id, home=False)

    lmb_home = xi(gf_h, ga_a, home=True)
    lmb_away = xi(gf_a, ga_h, home=False)

    ph, pd, pa = outcome_probs(lmb_home, lmb_away)
    over, under = over_under_25(lmb_home, lmb_away)
    btts_y, btts_n = both_teams_score(lmb_home, lmb_away)

    pred = PoissonPrediction(
        match_id=m.id,
        prob_home_win=float(ph),
        prob_draw=float(pd),
        prob_away_win=float(pa),
        over_2=float(over),
        under_2=float(under),
        both_score=float(btts_y),
        both_Noscore=float(btts_n),
    )
    return pred


def upsert_prediction(session: Session, pred: PoissonPrediction):
    # sencillamente borra y vuelve a insertar si ya existe (ajusta a ON CONFLICT si tienes unique)
    session.query(PoissonPrediction).filter_by(match_id=pred.match_id).delete()
    session.add(pred)