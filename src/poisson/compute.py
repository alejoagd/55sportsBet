from __future__ import annotations
from math import isfinite
from scipy.stats import poisson
from sqlalchemy.orm import Session
from sqlalchemy import func

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


def _inv(prob: float | None) -> float | None:
    """Retorna 1/prob si prob>0, si no, None."""
    if prob is None:
        return None
    try:
        v = 1.0 / float(prob)
        return float(v) if isfinite(v) else None
    except ZeroDivisionError:
        return None


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

    avg_h, avg_a = _league_avgs(session, m.season_id)

    gfph, gcph = _home_rates(session, m.home_team_id, m.season_id)  # local
    gfpa, gcpa = _away_rates(session, m.away_team_id, m.season_id)  # visitante

        # índices
    IAL = (gfph / avg_h) if avg_h else 1.0
    IDL = (gcph / avg_a) if avg_a else 1.0
    IAV = (gfpa / avg_a) if avg_a else 1.0
    IDV = (gcpa / avg_h) if avg_h else 1.0

    # goles esperados (clamp mínimo)
    exp_home = max(0.01, IAL * IDV * avg_h)
    exp_away = max(0.01, IAV * IDL * avg_a)

    # usa EH/EA como lambdas Poisson
    ph, pd, pa = outcome_probs(exp_home, exp_away)
    over, under = over_under_25(exp_home, exp_away)
    btts_y, btts_n = both_teams_score(exp_home, exp_away)

    return PoissonPrediction(
        match_id=m.id,
        expected_home_goals=exp_home,
        expected_away_goals=exp_away,
        prob_home_win=float(ph),
        prob_draw=float(pd),
        prob_away_win=float(pa),
        over_2=float(over),
        under_2=float(under),
        both_score=float(btts_y),
        both_Noscore=float(btts_n),
        # cuotas mínimas
        min_odds_1=_inv(ph),
        min_odds_X=_inv(pd),
        min_odds_2=_inv(pa),
        min_odds_over25=_inv(over),
        min_odds_under25=_inv(under),
        min_odds_btts_yes=_inv(btts_y),
        min_odds_btts_no=_inv(btts_n),
    )

def _league_avgs(session: Session, season_id: int | None):
    q = session.query(func.avg(Match.home_goals), func.avg(Match.away_goals))
    if season_id is not None:
        q = q.filter(Match.season_id == season_id)
    avg_h, avg_a = q.one()
    # valores de respaldo si aún no hay datos
    return float(avg_h or 1.2), float(avg_a or 1.2)

def _home_rates(session: Session, team_id: int, season_id: int | None):
    q = session.query(
        func.coalesce(func.sum(Match.home_goals), 0),
        func.coalesce(func.sum(Match.away_goals), 0),
        func.count(Match.id),
    ).filter(Match.home_team_id == team_id)
    if season_id is not None:
        q = q.filter(Match.season_id == season_id)
    gf, gc, gp = q.one()
    gp = gp or 1
    return float(gf)/gp, float(gc)/gp  # (GF/L por partido, GC/L por partido)

def _away_rates(session: Session, team_id: int, season_id: int | None):
    q = session.query(
        func.coalesce(func.sum(Match.away_goals), 0),
        func.coalesce(func.sum(Match.home_goals), 0),
        func.count(Match.id),
    ).filter(Match.away_team_id == team_id)
    if season_id is not None:
        q = q.filter(Match.season_id == season_id)
    gf, gc, gp = q.one()
    gp = gp or 1
    return float(gf)/gp, float(gc)/gp  # (GF/V por partido, GC/V por partido)


def upsert_prediction(session: Session, pred: PoissonPrediction):
    session.query(PoissonPrediction).filter_by(match_id=pred.match_id).delete()
    session.add(pred)