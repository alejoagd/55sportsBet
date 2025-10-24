# src/predictions/upcoming_weinston.py
from __future__ import annotations
import math
from typing import List, Tuple, Dict
from sqlalchemy import text

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

def _load_weinston_ratings(conn, season_id: int) -> Dict[int, Dict[str, float]]:
    """Carga los ratings de Weinston desde weinston_ratings"""
    q = text("""
        SELECT team_id, atk_home, def_home, atk_away, def_away
        FROM weinston_ratings
        WHERE season_id = :season_id
    """)
    ratings = {}
    for row in conn.execute(q, {"season_id": season_id}):
        ratings[int(row.team_id)] = {
            "atk_home": float(row.atk_home),
            "def_home": float(row.def_home),
            "atk_away": float(row.atk_away),
            "def_away": float(row.def_away),
        }
    return ratings

def _load_league_params(conn, season_id: int) -> Tuple[float, float, float]:
    """Carga mu_home, mu_away, home_adv desde weinston_params"""
    try:
        q = text("""
            SELECT mu_home, mu_away, home_adv 
            FROM weinston_params 
            WHERE season_id = :sid
        """)
        row = conn.execute(q, {"sid": season_id}).fetchone()
        
        if row and row.mu_home is not None:
            return float(row.mu_home), float(row.mu_away), float(row.home_adv)
    except Exception as e:
        print(f"⚠️  Error al cargar parámetros: {e}")
    
    print(f"⚠️  No hay parámetros Weinston para season {season_id}, usando fallback...")
    try:
        q_fb = text("""
            SELECT 
                COALESCE(AVG(home_goals), 1.3) as avg_h, 
                COALESCE(AVG(away_goals), 1.1) as avg_a
            FROM matches
            WHERE season_id = :sid 
              AND home_goals IS NOT NULL 
              AND away_goals IS NOT NULL
        """)
        row_fb = conn.execute(q_fb, {"sid": season_id}).fetchone()
        mu_home = float(row_fb.avg_h) if row_fb else 1.3
        mu_away = float(row_fb.avg_a) if row_fb else 1.1
        home_adv = 1.2
        print(f"   Fallback: μ_home={mu_home:.2f}, μ_away={mu_away:.2f}, HFA={home_adv:.2f}")
        return mu_home, mu_away, home_adv
    except Exception as e:
        print(f"⚠️  Error en fallback: {e}, usando defaults")
        return 1.3, 1.1, 1.2

def _load_team_stat_profiles(conn, season_id: int, n_recent: int = 20) -> Tuple[Dict, Dict]:
    """
    Carga perfiles estadísticos de equipos.
    IMPORTANTE: Usa home_shots, away_shots, etc. (nombres correctos de tu esquema)
    """
    profiles = {}
    
    q = text("""
        WITH team_stats AS (
            SELECT 
                m.home_team_id as team_id,
                'home' as location,
                ms.home_shots as shots_for,
                ms.away_shots as shots_against,
                ms.home_shots_on_target as shots_target_for,
                ms.away_shots_on_target as shots_target_against,
                ms.home_fouls as fouls_for,
                ms.away_fouls as fouls_against,
                (COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as cards_for,
                (COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0)) as cards_against,
                ms.home_corners as corners_for,
                ms.away_corners as corners_against,
                m.date
            FROM matches m
            JOIN match_stats ms ON ms.match_id = m.id
            WHERE m.season_id = :sid
              AND m.home_goals IS NOT NULL
            
            UNION ALL
            
            SELECT 
                m.away_team_id as team_id,
                'away' as location,
                ms.away_shots as shots_for,
                ms.home_shots as shots_against,
                ms.away_shots_on_target as shots_target_for,
                ms.home_shots_on_target as shots_target_against,
                ms.away_fouls as fouls_for,
                ms.home_fouls as fouls_against,
                (COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0)) as cards_for,
                (COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as cards_against,
                ms.away_corners as corners_for,
                ms.home_corners as corners_against,
                m.date
            FROM matches m
            JOIN match_stats ms ON ms.match_id = m.id
            WHERE m.season_id = :sid
              AND m.away_goals IS NOT NULL
        ),
        recent_stats AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY team_id, location ORDER BY date DESC) as rn
            FROM team_stats
        )
        SELECT 
            team_id,
            location,
            AVG(shots_for) as avg_shots_for,
            AVG(shots_against) as avg_shots_against,
            AVG(shots_target_for) as avg_shots_target_for,
            AVG(shots_target_against) as avg_shots_target_against,
            AVG(fouls_for) as avg_fouls_for,
            AVG(fouls_against) as avg_fouls_against,
            AVG(cards_for) as avg_cards_for,
            AVG(cards_against) as avg_cards_against,
            AVG(corners_for) as avg_corners_for,
            AVG(corners_against) as avg_corners_against
        FROM recent_stats
        WHERE rn <= :n_recent
        GROUP BY team_id, location
    """)
    
    rows = conn.execute(q, {"sid": season_id, "n_recent": n_recent}).fetchall()
    
    for row in rows:
        team_id = int(row.team_id)
        location = row.location
        
        if team_id not in profiles:
            profiles[team_id] = {
                "shots": {}, "shots_target": {}, "fouls": {}, "cards": {}, "corners": {}
            }
        
        prefix = "home" if location == "home" else "away"
        
        profiles[team_id]["shots"][f"{prefix}_for"] = float(row.avg_shots_for or 0)
        profiles[team_id]["shots"][f"{prefix}_against"] = float(row.avg_shots_against or 0)
        profiles[team_id]["shots_target"][f"{prefix}_for"] = float(row.avg_shots_target_for or 0)
        profiles[team_id]["shots_target"][f"{prefix}_against"] = float(row.avg_shots_target_against or 0)
        profiles[team_id]["fouls"][f"{prefix}_for"] = float(row.avg_fouls_for or 0)
        profiles[team_id]["fouls"][f"{prefix}_against"] = float(row.avg_fouls_against or 0)
        profiles[team_id]["cards"][f"{prefix}_for"] = float(row.avg_cards_for or 0)
        profiles[team_id]["cards"][f"{prefix}_against"] = float(row.avg_cards_against or 0)
        profiles[team_id]["corners"][f"{prefix}_for"] = float(row.avg_corners_for or 0)
        profiles[team_id]["corners"][f"{prefix}_against"] = float(row.avg_corners_against or 0)
    
    q_league = text("""
        SELECT 
            AVG(ms.home_shots) as avg_shots,
            AVG(ms.home_shots_on_target) as avg_shots_target,
            AVG(ms.home_fouls) as avg_fouls,
            AVG(COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as avg_cards,
            AVG(ms.home_corners) as avg_corners
        FROM match_stats ms
        JOIN matches m ON m.id = ms.match_id
        WHERE m.season_id = :sid
    """)
    
    row_league = conn.execute(q_league, {"sid": season_id}).fetchone()
    
    league_means = {
        "shots": float(row_league.avg_shots or 12.0),
        "shots_target": float(row_league.avg_shots_target or 4.0),
        "fouls": float(row_league.avg_fouls or 11.0),
        "cards": float(row_league.avg_cards or 2.0),
        "corners": float(row_league.avg_corners or 5.0)
    }
    
    return profiles, league_means

def _exp_stat(stat: str, home_id: int, away_id: int, profiles: Dict, league_means: Dict) -> Tuple[float, float]:
    """Combina ataque y defensa: 60% for + 40% against"""
    lg = league_means.get(stat, 0.0)
    
    home_profile = profiles.get(home_id, {}).get(stat, {})
    away_profile = profiles.get(away_id, {}).get(stat, {})
    
    home_for = float(home_profile.get("home_for", lg))
    away_against = float(away_profile.get("away_against", lg))
    home_val = 0.6 * home_for + 0.4 * away_against
    
    away_for = float(away_profile.get("away_for", lg))
    home_against = float(home_profile.get("home_against", lg))
    away_val = 0.6 * away_for + 0.4 * home_against
    
    return home_val, away_val

def _calculate_weinston_lambdas(
    home_team_id: int, away_team_id: int,
    ratings: Dict[int, Dict[str, float]],
    mu_home: float, mu_away: float, home_adv: float
) -> Tuple[float, float]:
    """Calcula λ usando ratings de Weinston"""
    home_ratings = ratings.get(home_team_id, {
        "atk_home": 1.0, "def_home": 1.0, "atk_away": 1.0, "def_away": 1.0
    })
    away_ratings = ratings.get(away_team_id, {
        "atk_home": 1.0, "def_home": 1.0, "atk_away": 1.0, "def_away": 1.0
    })
    
    lam_home = mu_home * home_ratings["atk_home"] * away_ratings["def_away"] * home_adv
    lam_away = mu_away * away_ratings["atk_away"] * home_ratings["def_home"]
    
    return float(lam_home), float(lam_away)

def predict_and_upsert_weinston(conn, season_id: int, match_ids: List[int], threshold: float = 0.5) -> None:
    ratings = _load_weinston_ratings(conn, season_id)
    mu_home, mu_away, home_adv = _load_league_params(conn, season_id)
    
    try:
        profiles, league_means = _load_team_stat_profiles(conn, season_id, n_recent=20)
        use_profiles = True
        print(f"✓ Perfiles estadísticos cargados para {len(profiles)} equipos")
    except Exception as e:
        print(f"⚠️  No se pudieron cargar perfiles: {e}")
        print(f"⚠️  Usando estimaciones basadas en lambdas")
        profiles, league_means = {}, {}
        use_profiles = False
    
    q_matches = text("SELECT id, home_team_id, away_team_id FROM matches WHERE id = ANY(:ids)")
    matches = conn.execute(q_matches, {"ids": match_ids}).fetchall()

    upsert = text("""
        INSERT INTO weinston_predictions
            (match_id, local_goals, away_goals, result_1x2, over_2, both_score,
             shots_home, shots_away, shots_target_home, shots_target_away,
             fouls_home, fouls_away, cards_home, cards_away,
             corners_home, corners_away, win_corners)
        VALUES
            (:mid, :lg, :ag, :r1x2, :over2, :btts,
             :sh, :sa, :sth, :sta, :fh, :fa, :ch, :ca, :coh, :coa, :wc)
        ON CONFLICT (match_id) DO UPDATE SET
            local_goals = EXCLUDED.local_goals, away_goals = EXCLUDED.away_goals,
            result_1x2 = EXCLUDED.result_1x2, over_2 = EXCLUDED.over_2, both_score = EXCLUDED.both_score,
            shots_home = EXCLUDED.shots_home, shots_away = EXCLUDED.shots_away,
            shots_target_home = EXCLUDED.shots_target_home, shots_target_away = EXCLUDED.shots_target_away,
            fouls_home = EXCLUDED.fouls_home, fouls_away = EXCLUDED.fouls_away,
            cards_home = EXCLUDED.cards_home, cards_away = EXCLUDED.cards_away,
            corners_home = EXCLUDED.corners_home, corners_away = EXCLUDED.corners_away,
            win_corners = EXCLUDED.win_corners
    """)

    for mid, home_id, away_id in matches:
        lh, la = _calculate_weinston_lambdas(home_id, away_id, ratings, mu_home, mu_away, home_adv)
        pr = _aggregate_probs(lh, la)

        if pr["pH"] >= pr["pD"] and pr["pH"] >= pr["pA"]:
            r1x2 = 1
        elif pr["pD"] >= pr["pH"] and pr["pD"] >= pr["pA"]:
            r1x2 = 0
        else:
            r1x2 = 2

        over2 = "OVER" if pr["pO25"] >= threshold else "UNDER"
        btts  = "YES"  if pr["pBTTS"] >= threshold else "NO"

        if use_profiles and profiles:
            sh, sa   = _exp_stat("shots", home_id, away_id, profiles, league_means)
            sth, sta = _exp_stat("shots_target", home_id, away_id, profiles, league_means)
            fh, fa   = _exp_stat("fouls", home_id, away_id, profiles, league_means)
            ch, ca   = _exp_stat("cards", home_id, away_id, profiles, league_means)
            coh, coa = _exp_stat("corners", home_id, away_id, profiles, league_means)
        else:
            sh = round(lh * 9 + 3, 2); sa = round(la * 9 + 3, 2)
            sth = round(lh * 3.5 + 1, 2); sta = round(la * 3.5 + 1, 2)
            fh = round(lh * 5 + 7, 2); fa = round(la * 5 + 7, 2)
            ch = round(lh * 0.8 + 1, 2); ca = round(la * 0.8 + 1, 2)
            coh = round(lh * 3.5 + 2, 2); coa = round(la * 3.5 + 2, 2)
        
        wc = "HOME" if coh > coa else ("AWAY" if coa > coh else "TIE")

        conn.execute(upsert, {
            "mid": int(mid), "lg": lh, "ag": la, "r1x2": int(r1x2),
            "over2": over2, "btts": btts,
            "sh": float(sh), "sa": float(sa),
            "sth": float(sth), "sta": float(sta),
            "fh": float(fh), "fa": float(fa),
            "ch": float(ch), "ca": float(ca),
            "coh": float(coh), "coa": float(coa),
            "wc": wc,
        })