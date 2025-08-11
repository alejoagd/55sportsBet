from __future__ import annotations
from scipy.stats import poisson
from sqlalchemy.orm import Session

from src.models import Match, PoissonPrediction

# --- helpers ---

def xi(goals_for_avg: float, goals_against_avg: float, home: bool) -> float:
    home_adv = 1.1 if home else 1.0
    return max(0.01, goals_for_avg * goals_against_avg * 0.5 * home_adv)


def outcome_probs(lmb_home: float, lmb_away: float, max_goals: int = 10) -> tuple[float, float, float]:
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
    m: Match = session.get(Match, match_id)
    assert m, f"Match {match_id} no existe"

    # medias simples de GF/GC por equipo usando últimos 5 partidos
    def avg_for_against(team_id: int) -> tuple[float, float]:
        rows = (
            session.query(Match)
            .filter((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
            .order_by(Match.date.desc())
            .limit(5)
            .all()
        )
        if not rows:
            return 1.2, 1.2
        gf, ga = [], []
        for mt in rows:
            if mt.home_team_id == team_id:
                gf.append(mt.home_goals or 0)
                ga.append(mt.away_goals or 0)
            else:
                gf.append(mt.away_goals or 0)
                ga.append(mt.home_goals or 0)
        return (float(sum(gf)/len(gf)), float(sum(ga)/len(ga)))

    gf_h, ga_h = avg_for_against(m.home_team_id)
    gf_a, ga_a = avg_for_against(m.away_team_id)

    lmb_home = xi(gf_h, ga_a, home=True)
    lmb_away = xi(gf_a, ga_h, home=False)

    ph, pd, pa = outcome_probs(lmb_home, lmb_away)
    over, under = over_under_25(lmb_home, lmb_away)
    btts_y, btts_n = both_teams_score(lmb_home, lmb_away)

    return PoissonPrediction(
        match_id=m.id,
        prob_home_win=float(ph),
        prob_draw=float(pd),
        prob_away_win=float(pa),
        over_2=float(over),
        under_2=float(under),
        both_score=float(btts_y),
        both_Noscore=float(btts_n),
    )


def upsert_prediction(session: Session, pred: PoissonPrediction):
    session.query(PoissonPrediction).filter_by(match_id=pred.match_id).delete()
    session.add(pred)