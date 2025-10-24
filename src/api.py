# api.py
from __future__ import annotations
from fastapi import FastAPI, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from src.config import settings
from src.predictions.evaluate import evaluate
from src.predictions.metrics import metrics_by_model
import math

app = FastAPI(title="Predictions API")

# CORS dev-friendly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear engine directamente
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
def get_predictions_metrics(
    season_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    rows = metrics_by_model(season_id=season_id, date_from=date_from, date_to=date_to)
    return {"season_id": season_id, "date_from": date_from, "date_to": date_to, "metrics": rows}


# ===== ROUTER PARA ENDPOINTS DE EVOLUCIÓN =====
router = APIRouter()


@router.get("/api/predictions/evolution")
def get_metrics_evolution(
    season_id: int = Query(..., description="ID de la temporada"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    window_type: str = Query("gameweek", description="Tipo de ventana: gameweek, weekly, monthly, rolling_5, rolling_10")
):
    """
    Retorna la evolución de métricas de ambos modelos a lo largo del tiempo.
    
    Tipos de ventana:
    - gameweek: Agrupa por jornada (cada ~10 partidos)
    - weekly: Agrupa por semana
    - monthly: Agrupa por mes
    - rolling_5: Ventana móvil de últimos 5 partidos
    - rolling_10: Ventana móvil de últimos 10 partidos
    """
    
    if window_type == "gameweek":
        query = text("""
            WITH match_with_gameweek AS (
                SELECT 
                    m.id as match_id,
                    m.date,
                    ROW_NUMBER() OVER (PARTITION BY m.season_id ORDER BY m.date) as match_number,
                    FLOOR((ROW_NUMBER() OVER (PARTITION BY m.season_id ORDER BY m.date) - 1) / 10) + 1 as gameweek
                FROM matches m
                WHERE m.season_id = :season_id
                  AND m.home_goals IS NOT NULL
                  AND (:date_from IS NULL OR m.date >= :date_from)
                  AND (:date_to IS NULL OR m.date <= :date_to)
            ),
            metrics_by_gameweek AS (
                SELECT 
                    po.model,
                    mw.gameweek,
                    MIN(mw.date) as period_start,
                    MAX(mw.date) as period_end,
                    COUNT(*) as total_matches,
                    
                    -- 1X2
                    COUNT(*) FILTER (WHERE po.hit_1x2 IS NOT NULL) as decided_1x2,
                    AVG((po.hit_1x2)::int) FILTER (WHERE po.hit_1x2 IS NOT NULL) as acc_1x2,
                    
                    -- Over/Under
                    COUNT(*) FILTER (WHERE po.hit_over25 IS NOT NULL) as decided_over25,
                    AVG((po.hit_over25)::int) FILTER (WHERE po.hit_over25 IS NOT NULL) as acc_over25,
                    
                    -- BTTS
                    COUNT(*) FILTER (WHERE po.hit_btts IS NOT NULL) as decided_btts,
                    AVG((po.hit_btts)::int) FILTER (WHERE po.hit_btts IS NOT NULL) as acc_btts,
                    
                    -- RMSE
                    AVG(po.rmse_goals) as avg_rmse
                    
                FROM prediction_outcomes po
                JOIN match_with_gameweek mw ON mw.match_id = po.match_id
                GROUP BY po.model, mw.gameweek
                ORDER BY mw.gameweek, po.model
            )
            SELECT 
                model,
                gameweek as period,
                period_start::text as period_start,
                period_end::text as period_end,
                total_matches,
                decided_1x2,
                ROUND((acc_1x2 * 100)::numeric, 1) as acc_1x2_pct,
                decided_over25,
                ROUND((acc_over25 * 100)::numeric, 1) as acc_over25_pct,
                decided_btts,
                ROUND((acc_btts * 100)::numeric, 1) as acc_btts_pct,
                ROUND(avg_rmse::numeric, 3) as avg_rmse
            FROM metrics_by_gameweek
            ORDER BY period, model
        """)
    
    elif window_type == "weekly":
        query = text("""
            WITH metrics_by_week AS (
                SELECT 
                    po.model,
                    DATE_TRUNC('week', m.date) as week_start,
                    COUNT(*) as total_matches,
                    AVG((po.hit_1x2)::int) FILTER (WHERE po.hit_1x2 IS NOT NULL) as acc_1x2,
                    AVG((po.hit_over25)::int) FILTER (WHERE po.hit_over25 IS NOT NULL) as acc_over25,
                    AVG((po.hit_btts)::int) FILTER (WHERE po.hit_btts IS NOT NULL) as acc_btts,
                    AVG(po.rmse_goals) as avg_rmse
                FROM prediction_outcomes po
                JOIN matches m ON m.id = po.match_id
                WHERE m.season_id = :season_id
                  AND (:date_from IS NULL OR m.date >= :date_from)
                  AND (:date_to IS NULL OR m.date <= :date_to)
                GROUP BY po.model, week_start
            )
            SELECT 
                model,
                week_start::text as period,
                week_start::text as period_start,
                (week_start + INTERVAL '6 days')::date::text as period_end,
                total_matches,
                ROUND((acc_1x2 * 100)::numeric, 1) as acc_1x2_pct,
                ROUND((acc_over25 * 100)::numeric, 1) as acc_over25_pct,
                ROUND((acc_btts * 100)::numeric, 1) as acc_btts_pct,
                ROUND(avg_rmse::numeric, 3) as avg_rmse
            FROM metrics_by_week
            ORDER BY period, model
        """)
    
    elif window_type in ["rolling_5", "rolling_10"]:
        window_size = 5 if window_type == "rolling_5" else 10
        query = text(f"""
            WITH ordered_matches AS (
                SELECT 
                    po.match_id,
                    po.model,
                    m.date,
                    po.hit_1x2,
                    po.hit_over25,
                    po.hit_btts,
                    po.rmse_goals,
                    ROW_NUMBER() OVER (PARTITION BY po.model ORDER BY m.date) as rn
                FROM prediction_outcomes po
                JOIN matches m ON m.id = po.match_id
                WHERE m.season_id = :season_id
                  AND (:date_from IS NULL OR m.date >= :date_from)
                  AND (:date_to IS NULL OR m.date <= :date_to)
            ),
            rolling_metrics AS (
                SELECT 
                    model,
                    rn as period,
                    date,
                    AVG((hit_1x2)::int) OVER (
                        PARTITION BY model 
                        ORDER BY rn 
                        ROWS BETWEEN {window_size - 1} PRECEDING AND CURRENT ROW
                    ) as acc_1x2,
                    AVG((hit_over25)::int) OVER (
                        PARTITION BY model 
                        ORDER BY rn 
                        ROWS BETWEEN {window_size - 1} PRECEDING AND CURRENT ROW
                    ) as acc_over25,
                    AVG((hit_btts)::int) OVER (
                        PARTITION BY model 
                        ORDER BY rn 
                        ROWS BETWEEN {window_size - 1} PRECEDING AND CURRENT ROW
                    ) as acc_btts,
                    AVG(rmse_goals) OVER (
                        PARTITION BY model 
                        ORDER BY rn 
                        ROWS BETWEEN {window_size - 1} PRECEDING AND CURRENT ROW
                    ) as avg_rmse,
                    COUNT(*) OVER (
                        PARTITION BY model 
                        ORDER BY rn 
                        ROWS BETWEEN {window_size - 1} PRECEDING AND CURRENT ROW
                    ) as total_matches
                FROM ordered_matches
            )
            SELECT 
                model,
                period,
                date::text as period_start,
                date::text as period_end,
                total_matches,
                ROUND((acc_1x2 * 100)::numeric, 1) as acc_1x2_pct,
                ROUND((acc_over25 * 100)::numeric, 1) as acc_over25_pct,
                ROUND((acc_btts * 100)::numeric, 1) as acc_btts_pct,
                ROUND(avg_rmse::numeric, 3) as avg_rmse
            FROM rolling_metrics
            WHERE total_matches = {window_size}
            ORDER BY period, model
        """)
    
    else:  # monthly
        query = text("""
            WITH metrics_by_month AS (
                SELECT 
                    po.model,
                    DATE_TRUNC('month', m.date) as month_start,
                    COUNT(*) as total_matches,
                    AVG((po.hit_1x2)::int) FILTER (WHERE po.hit_1x2 IS NOT NULL) as acc_1x2,
                    AVG((po.hit_over25)::int) FILTER (WHERE po.hit_over25 IS NOT NULL) as acc_over25,
                    AVG((po.hit_btts)::int) FILTER (WHERE po.hit_btts IS NOT NULL) as acc_btts,
                    AVG(po.rmse_goals) as avg_rmse
                FROM prediction_outcomes po
                JOIN matches m ON m.id = po.match_id
                WHERE m.season_id = :season_id
                  AND (:date_from IS NULL OR m.date >= :date_from)
                  AND (:date_to IS NULL OR m.date <= :date_to)
                GROUP BY po.model, month_start
            )
            SELECT 
                model,
                TO_CHAR(month_start, 'YYYY-MM') as period,
                month_start::text as period_start,
                (month_start + INTERVAL '1 month' - INTERVAL '1 day')::date::text as period_end,
                total_matches,
                ROUND((acc_1x2 * 100)::numeric, 1) as acc_1x2_pct,
                ROUND((acc_over25 * 100)::numeric, 1) as acc_over25_pct,
                ROUND((acc_btts * 100)::numeric, 1) as acc_btts_pct,
                ROUND(avg_rmse::numeric, 3) as avg_rmse
            FROM metrics_by_month
            ORDER BY period, model
        """)
    
    with engine.begin() as conn:
        rows = conn.execute(query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        }).mappings().all()
        
        # Transformar a estructura por modelo
        poisson_data = []
        weinston_data = []
        
        for row in rows:
            data_point = dict(row)
            if data_point["model"] == "poisson":
                poisson_data.append(data_point)
            else:
                weinston_data.append(data_point)
        
        return {
            "window_type": window_type,
            "poisson": poisson_data,
            "weinston": weinston_data
        }



@router.get("/api/team-statistics")
def get_team_statistics(
    season_id: int = Query(..., description="ID de la temporada"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Retorna estadísticas detalladas por equipo incluyendo:
    - Ofensiva (goles anotados)
    - Defensiva (goles recibidos)
    - Corners
    - Tiros y tiros al arco
    - Faltas
    - Tarjetas
    Separado por local y visitante
    """
    
    # Query para estadísticas de equipos
    query = text("""
        WITH home_stats AS (
            SELECT 
                t.id as team_id,
                t.name as team_name,
                COUNT(*) as matches_played,
                AVG(m.home_goals) as avg_goals_scored,
                AVG(m.away_goals) as avg_goals_conceded,
                SUM(m.home_goals) as total_goals_scored,
                SUM(m.away_goals) as total_goals_conceded,
                AVG(wp.corners_home) as avg_corners,
                SUM(wp.corners_home) as total_corners,
                AVG(wp.shots_home) as avg_shots,
                SUM(wp.shots_home) as total_shots,
                AVG(wp.shots_target_home) as avg_shots_target,
                SUM(wp.shots_target_home) as total_shots_target,
                AVG(wp.fouls_home) as avg_fouls,
                SUM(wp.fouls_home) as total_fouls,
                AVG(wp.cards_home) as avg_cards,
                SUM(wp.cards_home) as total_cards
            FROM teams t
            JOIN matches m ON m.home_team_id = t.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NOT NULL
              AND (:date_from IS NULL OR m.date >= :date_from)
              AND (:date_to IS NULL OR m.date <= :date_to)
            GROUP BY t.id, t.name
        ),
        away_stats AS (
            SELECT 
                t.id as team_id,
                t.name as team_name,
                COUNT(*) as matches_played,
                AVG(m.away_goals) as avg_goals_scored,
                AVG(m.home_goals) as avg_goals_conceded,
                SUM(m.away_goals) as total_goals_scored,
                SUM(m.home_goals) as total_goals_conceded,
                AVG(wp.corners_away) as avg_corners,
                SUM(wp.corners_away) as total_corners,
                AVG(wp.shots_away) as avg_shots,
                SUM(wp.shots_away) as total_shots,
                AVG(wp.shots_target_away) as avg_shots_target,
                SUM(wp.shots_target_away) as total_shots_target,
                AVG(wp.fouls_away) as avg_fouls,
                SUM(wp.fouls_away) as total_fouls,
                AVG(wp.cards_away) as avg_cards,
                SUM(wp.cards_away) as total_cards
            FROM teams t
            JOIN matches m ON m.away_team_id = t.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NOT NULL
              AND (:date_from IS NULL OR m.date >= :date_from)
              AND (:date_to IS NULL OR m.date <= :date_to)
            GROUP BY t.id, t.name
        )
        SELECT 
            COALESCE(h.team_id, a.team_id) as team_id,
            COALESCE(h.team_name, a.team_name) as team_name,
            
            -- Partidos jugados
            COALESCE(h.matches_played, 0) as home_matches,
            COALESCE(a.matches_played, 0) as away_matches,
            COALESCE(h.matches_played, 0) + COALESCE(a.matches_played, 0) as total_matches,
            
            -- Goles (Ofensiva)
            ROUND(COALESCE(h.avg_goals_scored, 0)::numeric, 2) as home_avg_goals_scored,
            ROUND(COALESCE(a.avg_goals_scored, 0)::numeric, 2) as away_avg_goals_scored,
            COALESCE(h.total_goals_scored, 0) as home_total_goals_scored,
            COALESCE(a.total_goals_scored, 0) as away_total_goals_scored,
            
            -- Goles Recibidos (Defensiva)
            ROUND(COALESCE(h.avg_goals_conceded, 0)::numeric, 2) as home_avg_goals_conceded,
            ROUND(COALESCE(a.avg_goals_conceded, 0)::numeric, 2) as away_avg_goals_conceded,
            COALESCE(h.total_goals_conceded, 0) as home_total_goals_conceded,
            COALESCE(a.total_goals_conceded, 0) as away_total_goals_conceded,
            
            -- Corners
            ROUND(COALESCE(h.avg_corners, 0)::numeric, 2) as home_avg_corners,
            ROUND(COALESCE(a.avg_corners, 0)::numeric, 2) as away_avg_corners,
            COALESCE(h.total_corners, 0) as home_total_corners,
            COALESCE(a.total_corners, 0) as away_total_corners,
            
            -- Tiros
            ROUND(COALESCE(h.avg_shots, 0)::numeric, 2) as home_avg_shots,
            ROUND(COALESCE(a.avg_shots, 0)::numeric, 2) as away_avg_shots,
            COALESCE(h.total_shots, 0) as home_total_shots,
            COALESCE(a.total_shots, 0) as away_total_shots,
            
            -- Tiros al arco
            ROUND(COALESCE(h.avg_shots_target, 0)::numeric, 2) as home_avg_shots_target,
            ROUND(COALESCE(a.avg_shots_target, 0)::numeric, 2) as away_avg_shots_target,
            COALESCE(h.total_shots_target, 0) as home_total_shots_target,
            COALESCE(a.total_shots_target, 0) as away_total_shots_target,
            
            -- Faltas
            ROUND(COALESCE(h.avg_fouls, 0)::numeric, 2) as home_avg_fouls,
            ROUND(COALESCE(a.avg_fouls, 0)::numeric, 2) as away_avg_fouls,
            COALESCE(h.total_fouls, 0) as home_total_fouls,
            COALESCE(a.total_fouls, 0) as away_total_fouls,
            
            -- Tarjetas
            ROUND(COALESCE(h.avg_cards, 0)::numeric, 2) as home_avg_cards,
            ROUND(COALESCE(a.avg_cards, 0)::numeric, 2) as away_avg_cards,
            COALESCE(h.total_cards, 0) as home_total_cards,
            COALESCE(a.total_cards, 0) as away_total_cards
            
        FROM home_stats h
        FULL OUTER JOIN away_stats a ON h.team_id = a.team_id
        WHERE COALESCE(h.matches_played, 0) + COALESCE(a.matches_played, 0) > 0
        ORDER BY team_name
    """)
    
    # Query para estadísticas de árbitros
    referee_query = text("""
        SELECT 
            m.referee,
            COUNT(*) as matches_officiated,
            AVG(wp.fouls_home + wp.fouls_away) as avg_fouls_per_match,
            SUM(wp.fouls_home + wp.fouls_away) as total_fouls,
            AVG(wp.cards_home + wp.cards_away) as avg_cards_per_match,
            SUM(wp.cards_home + wp.cards_away) as total_cards
        FROM matches m
        LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
        WHERE m.season_id = :season_id
          AND m.referee IS NOT NULL
          AND m.home_goals IS NOT NULL
          AND (:date_from IS NULL OR m.date >= :date_from)
          AND (:date_to IS NULL OR m.date <= :date_to)
        GROUP BY m.referee
        HAVING COUNT(*) >= 3
        ORDER BY avg_fouls_per_match DESC
    """)
    
    with engine.begin() as conn:
        # Obtener estadísticas de equipos
        team_rows = conn.execute(query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        }).mappings().all()
        
        team_stats = [dict(row) for row in team_rows]
        
        # Obtener estadísticas de árbitros
        referee_rows = conn.execute(referee_query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        }).mappings().all()
        
        referee_stats = [dict(row) for row in referee_rows]
        
        return {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to,
            "teams": team_stats,
            "referees": referee_stats
        }        


# Reemplaza SOLO estos dos endpoints en tu api.py

@router.get("/api/matches/upcoming")
def get_upcoming_matches(
    season_id: int = Query(..., description="ID de la temporada"),
    limit: int = Query(10, description="Número de partidos a retornar")
):
    """
    Retorna los próximos partidos sin resultado aún
    """
    query = text("""
        SELECT
            m.id as match_id,
            m.date,
            th.name as home_team,
            ta.name as away_team,
            m.referee,
            
            -- Poisson predictions (son probabilidades 0-1)
            pp.expected_home_goals as poisson_home_goals,
            pp.expected_away_goals as poisson_away_goals,
            pp.prob_home_win as poisson_prob_home,
            pp.prob_draw as poisson_prob_draw,
            pp.prob_away_win as poisson_prob_away,
            pp.over_2 as poisson_over_25,
            pp.both_score as poisson_btts,
            
            -- Weinston predictions
            wp.local_goals as weinston_home_goals,
            wp.away_goals as weinston_away_goals,
            
            -- Convertir result_1x2 a formato letra (0=D, 1=H, 2=A)
            CASE 
                WHEN wp.result_1x2 = 0 THEN 'D'
                WHEN wp.result_1x2 = 1 THEN 'H'
                WHEN wp.result_1x2 = 2 THEN 'A'
                ELSE NULL
            END as weinston_result,
            
            -- CÁLCULO DINÁMICO: Over/Under basado en goles predichos
            -- Usa función sigmoid centrada en 2.5 goles
            -- Si predice 2.5 goles → 50%
            -- Si predice 4+ goles → 90%+
            -- Si predice 1 gol → 10%
            GREATEST(0.05, LEAST(0.95,
                1.0 / (1.0 + EXP(-(COALESCE(wp.local_goals, 0) + COALESCE(wp.away_goals, 0) - 2.5) * 1.8))
            )) as weinston_over_25,
            
            -- CÁLCULO DINÁMICO: BTTS basado en goles individuales
            -- Si ambos predicen 1+ gol → alta probabilidad
            -- Usa producto de probabilidades exponenciales
            GREATEST(0.05, LEAST(0.95,
                (1.0 - EXP(-COALESCE(wp.local_goals, 0) * 1.2)) * 
                (1.0 - EXP(-COALESCE(wp.away_goals, 0) * 1.2))
            )) as weinston_btts
            
        FROM matches m
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
        LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
        WHERE m.season_id = :season_id
          AND m.home_goals IS NULL
          AND m.date >= CURRENT_DATE
        ORDER BY m.date, m.id
        LIMIT :limit
    """)
    
    with engine.begin() as conn:
        rows = conn.execute(query, {
            "season_id": season_id,
            "limit": limit
        }).mappings().all()
        
        return [dict(row) for row in rows]


@router.get("/api/matches/recent-results")
def get_recent_results(
    season_id: int = Query(..., description="ID de la temporada"),
    num_matches: int = Query(20, description="Número de partidos recientes a retornar")
):
    """
    Retorna los últimos partidos jugados con predicciones y resultados reales
    """
    query = text("""
        SELECT
            m.id as match_id,
            m.date,
            th.name as home_team,
            ta.name as away_team,
            m.home_goals as actual_home_goals,
            m.away_goals as actual_away_goals,
            m.referee,
            
            -- Resultado real
            CASE 
                WHEN m.home_goals > m.away_goals THEN 'H'
                WHEN m.home_goals < m.away_goals THEN 'A'
                ELSE 'D'
            END as actual_result,
            
            -- Poisson predictions
            pp.expected_home_goals as poisson_home_goals,
            pp.expected_away_goals as poisson_away_goals,
            pp.prob_home_win as poisson_prob_home,
            pp.prob_draw as poisson_prob_draw,
            pp.prob_away_win as poisson_prob_away,
            pp.over_2 as poisson_over_25,
            pp.both_score as poisson_btts,
            
            -- Weinston predictions
            wp.local_goals as weinston_home_goals,
            wp.away_goals as weinston_away_goals,
            
            -- Convertir result_1x2 a formato letra
            CASE 
                WHEN wp.result_1x2 = 0 THEN 'D'
                WHEN wp.result_1x2 = 1 THEN 'H'
                WHEN wp.result_1x2 = 2 THEN 'A'
                ELSE NULL
            END as weinston_result,
            
            -- CÁLCULO DINÁMICO: Over/Under basado en goles predichos
            GREATEST(0.05, LEAST(0.95,
                1.0 / (1.0 + EXP(-(COALESCE(wp.local_goals, 0) + COALESCE(wp.away_goals, 0) - 2.5) * 1.8))
            )) as weinston_over_25,
            
            -- CÁLCULO DINÁMICO: BTTS basado en goles individuales
            GREATEST(0.05, LEAST(0.95,
                (1.0 - EXP(-COALESCE(wp.local_goals, 0) * 1.2)) * 
                (1.0 - EXP(-COALESCE(wp.away_goals, 0) * 1.2))
            )) as weinston_btts,
            
            -- Aciertos (desde prediction_outcomes)
            po_poisson.hit_1x2 as poisson_hit_1x2,
            po_poisson.hit_over25 as poisson_hit_over25,
            po_poisson.hit_btts as poisson_hit_btts,
            po_weinston.hit_1x2 as weinston_hit_1x2,
            po_weinston.hit_over25 as weinston_hit_over25,
            po_weinston.hit_btts as weinston_hit_btts
            
        FROM matches m
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
        LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
        LEFT JOIN prediction_outcomes po_poisson ON po_poisson.match_id = m.id AND po_poisson.model = 'poisson'
        LEFT JOIN prediction_outcomes po_weinston ON po_weinston.match_id = m.id AND po_weinston.model = 'weinston'
        WHERE m.season_id = :season_id
          AND m.home_goals IS NOT NULL
        ORDER BY m.date DESC, m.id DESC
        LIMIT :num_matches
    """)
    
    with engine.begin() as conn:
        rows = conn.execute(query, {
            "season_id": season_id,
            "num_matches": num_matches
        }).mappings().all()
        
        return [dict(row) for row in rows]


# ============================================================================
# CÓDIGO CORRECTO PARA api.py - RESPETA EL FORMATO ORIGINAL
# ============================================================================

import math  # Asegúrate de tener este import al inicio

@router.post("/api/recalculate-outcomes")
def recalculate_prediction_outcomes(season_id: int = Query(..., description="ID de la temporada")):
    """
    Recalcula SOLO los aciertos (hit_*) manteniendo el formato original de pick_*
    pick_1x2: '1', '2', 'X'
    pick_over25: 'OVER', 'UNDER'
    pick_btts: 'YES', 'NO'
    """
    
    with engine.begin() as conn:
        # Eliminar registros existentes para esta temporada
        conn.execute(text("""
            DELETE FROM prediction_outcomes 
            WHERE match_id IN (
                SELECT id FROM matches WHERE season_id = :season_id
            )
        """), {"season_id": season_id})
        
        # Obtener partidos finalizados con predicciones
        query = text("""
            SELECT 
                m.id as match_id,
                m.home_goals,
                m.away_goals,
                
                -- Resultado real
                CASE 
                    WHEN m.home_goals > m.away_goals THEN 'H'
                    WHEN m.home_goals < m.away_goals THEN 'A'
                    ELSE 'D'
                END as actual_result,
                
                -- Over/Under real
                CASE 
                    WHEN (m.home_goals + m.away_goals) > 2.5 THEN TRUE
                    ELSE FALSE
                END as actual_over25,
                
                -- BTTS real
                CASE 
                    WHEN m.home_goals > 0 AND m.away_goals > 0 THEN TRUE
                    ELSE FALSE
                END as actual_btts,
                
                -- Predicciones Poisson
                pp.expected_home_goals as poisson_pred_home_goals,
                pp.expected_away_goals as poisson_pred_away_goals,
                pp.prob_home_win as poisson_prob_home,
                pp.prob_draw as poisson_prob_draw,
                pp.prob_away_win as poisson_prob_away,
                pp.over_2 as poisson_over25,
                pp.both_score as poisson_btts,
                
                -- Predicciones Weinston
                wp.local_goals as weinston_pred_home_goals,
                wp.away_goals as weinston_pred_away_goals,
                wp.result_1x2 as weinston_result_int,
                wp.over_2 as weinston_over25_text,
                wp.both_score as weinston_btts_text
                
            FROM matches m
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NOT NULL
              AND m.away_goals IS NOT NULL
        """)
        
        matches = conn.execute(query, {"season_id": season_id}).mappings().all()
        
        inserted_count = 0
        
        for match in matches:
            match_id = match['match_id']
            actual_result = match['actual_result']
            actual_over25 = match['actual_over25']
            actual_btts = match['actual_btts']
            actual_home_goals = match['home_goals']
            actual_away_goals = match['away_goals']
            
            # ===== POISSON =====
            if match['poisson_prob_home'] is not None:
                prob_home = match['poisson_prob_home']
                prob_draw = match['poisson_prob_draw']
                prob_away = match['poisson_prob_away']
                
                # Predicción 1X2 - FORMATO ORIGINAL: '1', 'X', '2'
                if prob_home > prob_draw and prob_home > prob_away:
                    poisson_pick_1x2 = '1'  # Local gana
                elif prob_away > prob_draw and prob_away > prob_home:
                    poisson_pick_1x2 = '2'  # Visitante gana
                else:
                    poisson_pick_1x2 = 'X'  # Empate
                
                # Convertir actual_result ('H', 'D', 'A') a formato ('1', 'X', '2')
                actual_result_converted = '1' if actual_result == 'H' else ('2' if actual_result == 'A' else 'X')
                hit_1x2 = (poisson_pick_1x2 == actual_result_converted)
                
                # Over/Under - FORMATO ORIGINAL: 'OVER', 'UNDER'
                poisson_over25_prob = match['poisson_over25'] or 0
                poisson_pick_over25 = 'OVER' if (poisson_over25_prob > 0.5) else 'UNDER'
                hit_over25 = ((poisson_pick_over25 == 'OVER') == actual_over25)
                
                # BTTS - FORMATO ORIGINAL: 'YES', 'NO'
                poisson_btts_prob = match['poisson_btts'] or 0
                poisson_pick_btts = 'YES' if (poisson_btts_prob > 0.5) else 'NO'
                hit_btts = ((poisson_pick_btts == 'YES') == actual_btts)
                
                # Errores absolutos
                pred_home = match['poisson_pred_home_goals'] or 0
                pred_away = match['poisson_pred_away_goals'] or 0
                abs_err_home = abs(actual_home_goals - pred_home)
                abs_err_away = abs(actual_away_goals - pred_away)
                
                # RMSE
                rmse_goals = math.sqrt((abs_err_home ** 2 + abs_err_away ** 2) / 2)
                
                conn.execute(text("""
                    INSERT INTO prediction_outcomes 
                    (match_id, model, pick_1x2, hit_1x2, pick_over25, hit_over25, 
                     pick_btts, hit_btts, abs_err_home_goals, abs_err_away_goals, rmse_goals)
                    VALUES (:match_id, 'poisson', :pick_1x2, :hit_1x2, :pick_over25, 
                            :hit_over25, :pick_btts, :hit_btts, :abs_err_home, :abs_err_away, :rmse_goals)
                """), {
                    'match_id': match_id,
                    'pick_1x2': poisson_pick_1x2,        # '1', 'X', '2'
                    'hit_1x2': hit_1x2,
                    'pick_over25': poisson_pick_over25,  # 'OVER', 'UNDER'
                    'hit_over25': hit_over25,
                    'pick_btts': poisson_pick_btts,      # 'YES', 'NO'
                    'hit_btts': hit_btts,
                    'abs_err_home': abs_err_home,
                    'abs_err_away': abs_err_away,
                    'rmse_goals': rmse_goals
                })
                
                inserted_count += 1
            
            # ===== WEINSTON =====
            if match['weinston_result_int'] is not None:
                result_int = match['weinston_result_int']
                
                # Convertir result_1x2 - FORMATO ORIGINAL: '1', 'X', '2'
                if result_int == 0:
                    weinston_pick_1x2 = 'X'  # Empate
                elif result_int == 1:
                    weinston_pick_1x2 = '1'  # Local gana
                elif result_int == 2:
                    weinston_pick_1x2 = '2'  # Visitante gana
                else:
                    weinston_pick_1x2 = None
                
                # Convertir actual_result
                actual_result_converted = '1' if actual_result == 'H' else ('2' if actual_result == 'A' else 'X')
                hit_1x2 = (weinston_pick_1x2 == actual_result_converted) if weinston_pick_1x2 else False
                
                # Over/Under - FORMATO ORIGINAL: 'OVER', 'UNDER'
                weinston_over_text = (match['weinston_over25_text'] or '').upper()
                weinston_pick_over25 = weinston_over_text if weinston_over_text in ['OVER', 'UNDER'] else 'UNDER'
                hit_over25 = ((weinston_pick_over25 == 'OVER') == actual_over25)
                
                # BTTS - FORMATO ORIGINAL: 'YES', 'NO'
                weinston_btts_text = (match['weinston_btts_text'] or '').upper()
                weinston_pick_btts = 'YES' if (weinston_btts_text == 'YES') else 'NO'
                hit_btts = ((weinston_pick_btts == 'YES') == actual_btts)
                
                # Errores absolutos
                pred_home = match['weinston_pred_home_goals'] or 0
                pred_away = match['weinston_pred_away_goals'] or 0
                abs_err_home = abs(actual_home_goals - pred_home)
                abs_err_away = abs(actual_away_goals - pred_away)
                
                # RMSE
                rmse_goals = math.sqrt((abs_err_home ** 2 + abs_err_away ** 2) / 2)
                
                conn.execute(text("""
                    INSERT INTO prediction_outcomes 
                    (match_id, model, pick_1x2, hit_1x2, pick_over25, hit_over25, 
                     pick_btts, hit_btts, abs_err_home_goals, abs_err_away_goals, rmse_goals)
                    VALUES (:match_id, 'weinston', :pick_1x2, :hit_1x2, :pick_over25, 
                            :hit_over25, :pick_btts, :hit_btts, :abs_err_home, :abs_err_away, :rmse_goals)
                """), {
                    'match_id': match_id,
                    'pick_1x2': weinston_pick_1x2,        # '1', 'X', '2'
                    'hit_1x2': hit_1x2,
                    'pick_over25': weinston_pick_over25,  # 'OVER', 'UNDER'
                    'hit_over25': hit_over25,
                    'pick_btts': weinston_pick_btts,      # 'YES', 'NO'
                    'hit_btts': hit_btts,
                    'abs_err_home': abs_err_home,
                    'abs_err_away': abs_err_away,
                    'rmse_goals': rmse_goals
                })
                
                inserted_count += 1
        
        # Obtener estadísticas
        stats_query = text("""
            SELECT 
                model,
                COUNT(*) as total_predictions,
                SUM(CASE WHEN hit_1x2 THEN 1 ELSE 0 END) as hits_1x2,
                SUM(CASE WHEN hit_over25 THEN 1 ELSE 0 END) as hits_over25,
                SUM(CASE WHEN hit_btts THEN 1 ELSE 0 END) as hits_btts,
                ROUND((AVG(CASE WHEN hit_1x2 THEN 1.0 ELSE 0.0 END) * 100)::NUMERIC, 2) as accuracy_1x2,
                ROUND((AVG(CASE WHEN hit_over25 THEN 1.0 ELSE 0.0 END) * 100)::NUMERIC, 2) as accuracy_over25,
                ROUND((AVG(CASE WHEN hit_btts THEN 1.0 ELSE 0.0 END) * 100)::NUMERIC, 2) as accuracy_btts,
                ROUND(AVG(abs_err_home_goals)::NUMERIC, 2) as avg_err_home,
                ROUND(AVG(abs_err_away_goals)::NUMERIC, 2) as avg_err_away,
                ROUND(AVG(rmse_goals)::NUMERIC, 2) as avg_rmse
            FROM prediction_outcomes po
            JOIN matches m ON m.id = po.match_id
            WHERE m.season_id = :season_id
            GROUP BY model
        """)
        
        stats = conn.execute(stats_query, {"season_id": season_id}).mappings().all()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "statistics": [dict(row) for row in stats]
        }


# REEMPLAZA EL ENDPOINT EN api.py CON ESTE CÓDIGO CORREGIDO

@router.get("/api/matches/{match_id}/details")
def get_match_details(match_id: int):
    """
    Obtiene todos los detalles de un partido específico incluyendo estadísticas y predicciones
    USA LAS MISMAS FÓRMULAS QUE EL DASHBOARD para calcular porcentajes de Weinston
    """
    
    with engine.begin() as conn:
        query = text("""
            SELECT 
                m.id as match_id,
                m.date,
                ht.name as home_team,
                at.name as away_team,
                m.home_goals,
                m.away_goals,
                m.referee,
                
                -- Estadísticas desde weinston_predictions
                wp.shots_home as home_shots,
                wp.shots_away as away_shots,
                wp.shots_target_home as home_shots_on_target,
                wp.shots_target_away as away_shots_on_target,
                wp.fouls_home as home_fouls,
                wp.fouls_away as away_fouls,
                wp.corners_home as home_corners,
                wp.corners_away as away_corners,
                wp.cards_home as home_yellow_cards,
                wp.cards_away as away_yellow_cards,
                0 as home_red_cards,
                0 as away_red_cards,
                0 as home_possession,
                0 as away_possession,
                
                -- Predicciones Poisson
                pp.expected_home_goals as poisson_home_goals,
                pp.expected_away_goals as poisson_away_goals,
                pp.prob_home_win as poisson_prob_home,
                pp.prob_draw as poisson_prob_draw,
                pp.prob_away_win as poisson_prob_away,
                pp.over_2 as poisson_over_25,
                pp.both_score as poisson_btts,
                
                -- Predicciones Weinston
                wp.local_goals as weinston_home_goals,
                wp.away_goals as weinston_away_goals,
                wp.result_1x2,
                wp.over_2 as weinston_over_text,
                wp.both_score as weinston_btts_text,
                
                -- CÁLCULO DINÁMICO: Over/Under basado en goles predichos
                -- MISMA FÓRMULA QUE USA EL DASHBOARD
                GREATEST(0.05, LEAST(0.95,
                    1.0 / (1.0 + EXP(-(COALESCE(wp.local_goals, 0) + COALESCE(wp.away_goals, 0) - 2.5) * 1.8))
                )) as weinston_over_25,
                
                -- CÁLCULO DINÁMICO: BTTS basado en goles individuales
                -- MISMA FÓRMULA QUE USA EL DASHBOARD
                GREATEST(0.05, LEAST(0.95,
                    (1.0 - EXP(-COALESCE(wp.local_goals, 0) * 1.2)) * 
                    (1.0 - EXP(-COALESCE(wp.away_goals, 0) * 1.2))
                )) as weinston_btts
                
            FROM matches m
            -- JOIN con tabla teams para obtener nombres
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            -- LEFT JOIN con predicciones
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.id = :match_id
        """)
        
        result = conn.execute(query, {"match_id": match_id}).mappings().first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        
        # Convertir a diccionario
        match_data = dict(result)
        
        # Procesar resultado de Weinston (convertir int a string)
        result_1x2 = match_data.get('result_1x2')
        if result_1x2 == 0:
            match_data['weinston_result'] = 'X'
        elif result_1x2 == 1:
            match_data['weinston_result'] = '1'
        elif result_1x2 == 2:
            match_data['weinston_result'] = '2'
        else:
            match_data['weinston_result'] = 'X'
        
        return match_data


# ===== REGISTRAR EL ROUTER =====
app.include_router(router)