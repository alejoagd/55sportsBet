from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from scipy.optimize import minimize, LinearConstraint, Bounds
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.models import Match, Team
from sqlalchemy import text
from src.db import SessionLocal

@dataclass
class FitResult:
    team_ids: list[int]
    atk_home: np.ndarray; def_home: np.ndarray
    atk_away: np.ndarray; def_away: np.ndarray
    mu_home: float; mu_away: float; home_adv: float
    loss: float


def _pf(v):
    # python float desde numpy / None
    """Devuelve float nativo de Python (no numpy) o None."""
    if v is None:
        return None
    # Maneja numpy scalars, pandas, etc.
    try:
        # si v es numpy scalar → .item() → float nativo
        return float(getattr(v, "item", lambda: v)())
    except Exception:
        # última opción: forzar a través de np.asarray
        return float(np.asarray(v).astype(float).item())

def save_ratings(season_id: int, team_ids, atk_home, def_home, atk_away, def_away):
    # 0) Obtener league_id del season
    with SessionLocal() as s:
        league_id = s.execute(
            text("SELECT league_id FROM seasons WHERE id = :sid"),
            {"sid": season_id}
        ).scalar()
    
    # 1) normaliza a listas de float nativo
    to_py = lambda arr: [ _pf(x) for x in list(arr) ]
    # ... resto del código igual ...
    
    # 2) arma los registros con tipos puros
    rows = [
        {
            "season_id": int(season_id),
            "team_id": tid,
            "league_id": int(league_id),  # ← AGREGAR ESTO
            "atk_home": atk_home[i],
            "def_home": def_home[i],
            "atk_away": atk_away[i],
            "def_away": def_away[i],
        }
        for i, tid in enumerate(team_ids)
    ]

    upsert_sql = text("""
        INSERT INTO weinston_ratings (season_id, team_id, league_id, atk_home, def_home, atk_away, def_away)
        VALUES (:season_id, :team_id, :league_id, :atk_home, :def_home, :atk_away, :def_away)
        ON CONFLICT (season_id, team_id) DO UPDATE
        SET league_id = EXCLUDED.league_id,  -- ← AGREGAR ESTO
            atk_home = EXCLUDED.atk_home,
            def_home = EXCLUDED.def_home,
            atk_away = EXCLUDED.atk_away,
            def_away = EXCLUDED.def_away
    """)

    print("ROW SAMPLE:", rows[0])
    print("TYPES:", {k: type(v).__name__ for k, v in rows[0].items()})

    with SessionLocal() as s, s.begin():
        s.execute(upsert_sql, rows)


def _league_means(s: Session, season_id: int):
    mh, ma = s.query(func.avg(Match.home_goals), func.avg(Match.away_goals))\
              .filter(Match.season_id==season_id).one()
    return float(mh or 1.3), float(ma or 1.1)


def _dataset(s: Session, season_id: int):
    """
    Obtiene dataset de entrenamiento filtrando SOLO equipos de la liga correspondiente.
    
    ✅MULTI-LIGA: Ahora obtiene team_ids solo de los equipos que participan 
    en partidos de este season_id, evitando mezclar ligas.

    """
    # Obtener partidos terminados del season
    rows = s.query(Match.home_team_id, Match.away_team_id,
                   Match.home_goals, Match.away_goals)\
            .filter(Match.season_id==season_id,
                    Match.home_goals.isnot(None),
                    Match.away_goals.isnot(None)).all()
    
    # ✅ CORRECCIÓN: Obtener SOLO equipos que participan en esta temporada
    # Unión de equipos locales y visitantes de este season_id
    team_ids_query = s.query(Team.id)\
        .filter(Team.id.in_(
            s.query(Match.home_team_id).filter(Match.season_id==season_id)
            .union(
                s.query(Match.away_team_id).filter(Match.season_id==season_id)
            )
        ))\
        .order_by(Team.id)
    
    team_ids = [t.id for t in team_ids_query]
    
    # Validación: asegurar que tenemos al menos algunos equipos
    if len(team_ids) < 2:
        raise ValueError(f"season_id={season_id} tiene menos de 2 equipos. Verifica los datos.")
    
    print(f"📊 Dataset: {len(team_ids)} equipos únicos para season_id={season_id}")
    
    # Crear índice de equipos
    idx = {tid:i for i,tid in enumerate(team_ids)}
    
    # Arrays de índices y goles
    H = np.array([idx[r[0]] for r in rows])
    A = np.array([idx[r[1]] for r in rows])
    HG = np.array([r[2] for r in rows], float)
    AG = np.array([r[3] for r in rows], float)
    
    return team_ids, H, A, HG, AG


def fit_weinston(s: Session, season_id: int) -> FitResult:
    team_ids, H, A, HG, AG = _dataset(s, season_id)
    n = len(team_ids)
    mh, ma = _league_means(s, season_id)
    x0 = np.r_[np.ones(n), np.ones(n), np.ones(n), np.ones(n), mh, ma, 1.2]

    def unp(x):
        aL=x[0:n]; dH=x[3*n:4*n]; aA=x[2*n:3*n]; dA=x[n:2*n]
        mu_h=max(0.1,min(5.0,x[4*n])); mu_a=max(0.1,min(5.0,x[4*n+1])); hadv=max(0.5,min(4.0,x[4*n+2]))
        return aL.clip(0.1,10), dH.clip(0.1,10), aA.clip(0.1,10), dA.clip(0.1,10), mu_h, mu_a, hadv

    def loss(x):
        aL,dH,aA,dA,mu_h,mu_a,hadv = unp(x)
        lam_h = mu_h * aL[H] * dA[A] * hadv
        lam_a = mu_a * aA[A] * dH[H]
        lam_h = np.clip(lam_h, 1e-6, 50); lam_a = np.clip(lam_a, 1e-6, 50)
        nll = np.sum(lam_h - HG*np.log(lam_h) + lam_a - AG*np.log(lam_a))
        reg = 1e-3*(np.sum((aL-1)**2)+np.sum((aA-1)**2)+np.sum((dH-1)**2)+np.sum((dA-1)**2))
        return nll + reg

    Aeq = np.zeros((4, x0.size))
    n4 = n
    Aeq[0, 0:n] = 1/n;        Aeq[1, n:2*n] = 1/n
    Aeq[2, 2*n:3*n] = 1/n;    Aeq[3, 3*n:4*n] = 1/n
    lc  = LinearConstraint(Aeq, [1,1,1,1], [1,1,1,1])
    bnd = Bounds(np.r_[np.full(4*n,0.1), 0.1,0.1,0.5], np.r_[np.full(4*n,10), 5.0,5.0,4.0])

    res = minimize(loss, x0, method="trust-constr", constraints=[lc], bounds=bnd,
                   options={"gtol":1e-6,"xtol":1e-6,"maxiter":500})
    aL,dH,aA,dA,mu_h,mu_a,hadv = unp(res.x)
    
    return FitResult(team_ids, aL, dH, aA, dA, float(mu_h), float(mu_a), float(hadv), float(res.fun))


def save_league_params(season_id: int, mu_home: float, mu_away: float, home_adv: float, loss: float):
    """
    Guarda/actualiza los parámetros de liga calculados por fit_weinston.
    Mantiene UN ÚNICO registro por season_id.
    
    Args:
        season_id: ID de la temporada
        mu_home: Promedio de goles esperados en casa (μ_home)
        mu_away: Promedio de goles esperados visitante (μ_away)
        home_adv: Ventaja de local (home advantage)
        loss: Valor de la función de pérdida (para monitoreo)
    """
    upsert_sql = text("""
        INSERT INTO weinston_params (season_id, mu_home, mu_away, home_adv, loss, updated_at)
        VALUES (:season_id, :mu_home, :mu_away, :home_adv, :loss, NOW())
        ON CONFLICT (season_id) DO UPDATE SET
            mu_home = EXCLUDED.mu_home,
            mu_away = EXCLUDED.mu_away,
            home_adv = EXCLUDED.home_adv,
            loss = EXCLUDED.loss,
            updated_at = NOW()
    """)
    
    with SessionLocal() as s, s.begin():
        s.execute(upsert_sql, {
            "season_id": int(season_id),
            "mu_home": float(mu_home),
            "mu_away": float(mu_away),
            "home_adv": float(home_adv),
            "loss": float(loss)
        })
    
    print(f"✅ Parámetros guardados: μ_home={mu_home:.3f}, μ_away={mu_away:.3f}, HFA={home_adv:.3f}, loss={loss:.2f}")