# api.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from src.config import settings
from src.predictions.evaluate import evaluate
from src.predictions.metrics import metrics_by_model
from datetime import datetime, date
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
    
    ⚠️ CORREGIDO: Ahora usa match_stats (datos reales) en lugar de weinston_predictions
    """
    
    # Query para estadísticas de equipos
    query = text("""
        WITH home_stats AS (
            SELECT 
                t.id as team_id,
                t.name as team_name,
                COUNT(*) as matches_played,
                
                -- Goles (desde matches)
                AVG(m.home_goals) as avg_goals_scored,
                AVG(m.away_goals) as avg_goals_conceded,
                SUM(m.home_goals) as total_goals_scored,
                SUM(m.away_goals) as total_goals_conceded,
                
                -- Estadísticas detalladas (desde match_stats - DATOS REALES)
                AVG(ms.home_corners) as avg_corners,
                SUM(ms.home_corners) as total_corners,
                AVG(ms.home_shots) as avg_shots,
                SUM(ms.home_shots) as total_shots,
                AVG(ms.home_shots_on_target) as avg_shots_target,
                SUM(ms.home_shots_on_target) as total_shots_target,
                AVG(ms.home_fouls) as avg_fouls,
                SUM(ms.home_fouls) as total_fouls,
                AVG(COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as avg_cards,
                SUM(COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as total_cards
                
            FROM teams t
            JOIN matches m ON m.home_team_id = t.id
            LEFT JOIN match_stats ms ON ms.match_id = m.id
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
                
                -- Goles (desde matches)
                AVG(m.away_goals) as avg_goals_scored,
                AVG(m.home_goals) as avg_goals_conceded,
                SUM(m.away_goals) as total_goals_scored,
                SUM(m.home_goals) as total_goals_conceded,
                
                -- Estadísticas detalladas (desde match_stats - DATOS REALES)
                AVG(ms.away_corners) as avg_corners,
                SUM(ms.away_corners) as total_corners,
                AVG(ms.away_shots) as avg_shots,
                SUM(ms.away_shots) as total_shots,
                AVG(ms.away_shots_on_target) as avg_shots_target,
                SUM(ms.away_shots_on_target) as total_shots_target,
                AVG(ms.away_fouls) as avg_fouls,
                SUM(ms.away_fouls) as total_fouls,
                AVG(COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0)) as avg_cards,
                SUM(COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0)) as total_cards
                
            FROM teams t
            JOIN matches m ON m.away_team_id = t.id
            LEFT JOIN match_stats ms ON ms.match_id = m.id
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
    
    # Query para estadísticas de árbitros (TAMBIÉN CORREGIDA)
    referee_query = text("""
        SELECT 
            m.referee,
            COUNT(*) as matches_officiated,
            ROUND(AVG(COALESCE(ms.home_fouls, 0) + COALESCE(ms.away_fouls, 0))::numeric, 2) as avg_fouls_per_match,
            SUM(COALESCE(ms.home_fouls, 0) + COALESCE(ms.away_fouls, 0)) as total_fouls,
            ROUND(AVG(
                COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.away_yellow_cards, 0) + 
                COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0)
            )::numeric, 2) as avg_cards_per_match,
            SUM(
                COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.away_yellow_cards, 0) + 
                COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0)
            ) as total_cards
        FROM matches m
        LEFT JOIN match_stats ms ON ms.match_id = m.id
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
            
            -- ✅ USAR VALORES DE BD (el frontend ya sabe cómo mostrarlos)
            wp.prob_over_25 as weinston_over_25,
            wp.prob_btts as weinston_btts
            
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
            
            -- ✅ USAR VALORES DE BD
            wp.prob_over_25 as weinston_over_25,
            wp.prob_btts as weinston_btts,
            
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



@router.get("/api/matches/{match_id}/details")
def get_match_details(match_id: int):
    """
    Obtiene todos los detalles de un partido específico incluyendo estadísticas y predicciones
    - Predicciones de Weinston: SIEMPRE de weinston_predictions
    - Estadísticas del Partido: de match_stats (reales) o weinston_predictions (fallback)
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
                
                -- PREDICCIONES DE WEINSTON (SIEMPRE de weinston_predictions)
                wp.shots_home as weinston_shots_home,
                wp.shots_away as weinston_shots_away,
                wp.shots_target_home as weinston_shots_on_target_home,
                wp.shots_target_away as weinston_shots_on_target_away,
                wp.fouls_home as weinston_fouls_home,
                wp.fouls_away as weinston_fouls_away,
                wp.corners_home as weinston_corners_home,
                wp.corners_away as weinston_corners_away,
                wp.cards_home as weinston_cards_home,
                wp.cards_away as weinston_cards_away,

                -- 🔥 NUEVO: Probabilidades exactas de Weinston
                wp.prob_over_25 as weinston_prob_over_25,
                wp.prob_btts as weinston_prob_btts,
                wp.prob_home_win as weinston_prob_home_win,
                wp.prob_draw as weinston_prob_draw,
                wp.prob_away_win as weinston_prob_away_win,
                
                -- ESTADÍSTICAS REALES DEL PARTIDO (de match_stats con fallback a weinston)
                COALESCE(ms.home_shots, wp.shots_home, 0) as home_shots,
                COALESCE(ms.away_shots, wp.shots_away, 0) as away_shots,
                COALESCE(ms.home_shots_on_target, wp.shots_target_home, 0) as home_shots_on_target,
                COALESCE(ms.away_shots_on_target, wp.shots_target_away, 0) as away_shots_on_target,
                COALESCE(ms.home_fouls, wp.fouls_home, 0) as home_fouls,
                COALESCE(ms.away_fouls, wp.fouls_away, 0) as away_fouls,
                COALESCE(ms.home_corners, wp.corners_home, 0) as home_corners,
                COALESCE(ms.away_corners, wp.corners_away, 0) as away_corners,
                COALESCE(ms.home_yellow_cards, wp.cards_home, 0) as home_yellow_cards,
                COALESCE(ms.away_yellow_cards, wp.cards_away, 0) as away_yellow_cards,
                COALESCE(ms.home_red_cards, 0) as home_red_cards,
                COALESCE(ms.away_red_cards, 0) as away_red_cards,
                
                -- Estadísticas adicionales solo disponibles en match_stats
                ms.total_shots,
                ms.total_shots_on_target,
                ms.total_corners,
                ms.total_fouls,
                ms.total_cards,
                
                -- Indicador de si tiene estadísticas reales
                CASE WHEN ms.match_id IS NOT NULL THEN true ELSE false END as has_real_stats,
                
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
                
                -- ✅ USAR VALORES DE BD
                wp.prob_over_25 as weinston_over_25,
                wp.prob_btts as weinston_btts
                
            FROM matches m
            -- JOIN con tabla teams para obtener nombres
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            -- LEFT JOIN con predicciones
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            -- LEFT JOIN con estadísticas REALES del partido
            LEFT JOIN match_stats ms ON ms.match_id = m.id
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


@router.get("/api/best-bets/analysis")
def get_best_bets_analysis(season_id: int = Query(..., description="ID de la temporada")):
    """
    Analiza los próximos partidos y recomienda las mejores apuestas basándose en:
    1. Porcentaje de acierto histórico del modelo en cada tipo de predicción
    2. Confianza (probabilidad) de la predicción actual
    3. Score combinado para rankear
    """
    
    with engine.begin() as conn:
        # 1. Calcular % de acierto histórico por modelo y tipo
        historical_accuracy_query = text("""
            SELECT 
                model,
                COUNT(*) as total_predictions,
                
                -- Aciertos por tipo
                SUM(CASE WHEN hit_1x2 THEN 1 ELSE 0 END) as hits_1x2,
                SUM(CASE WHEN hit_over25 THEN 1 ELSE 0 END) as hits_over25,
                SUM(CASE WHEN hit_btts THEN 1 ELSE 0 END) as hits_btts,
                
                -- Porcentajes de acierto
                ROUND(AVG(CASE WHEN hit_1x2 THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_1x2,
                ROUND(AVG(CASE WHEN hit_over25 THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_over25,
                ROUND(AVG(CASE WHEN hit_btts THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_btts
                
            FROM prediction_outcomes po
            JOIN matches m ON m.id = po.match_id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NOT NULL  -- Solo partidos finalizados
            GROUP BY model
        """)
        
        accuracy_results = conn.execute(historical_accuracy_query, {"season_id": season_id}).mappings().all()
        
        # Crear diccionario de accuracy por modelo
        accuracy_by_model = {}
        for row in accuracy_results:
            accuracy_by_model[row['model']] = {
                'total_predictions': row['total_predictions'],
                'accuracy_1x2': float(row['accuracy_1x2'] or 0),
                'accuracy_over25': float(row['accuracy_over25'] or 0),
                'accuracy_btts': float(row['accuracy_btts'] or 0)
            }
        
        # 2. Obtener próximos partidos con predicciones
        upcoming_matches_query = text("""
            SELECT
                m.id as match_id,
                m.date,
                th.name as home_team,
                ta.name as away_team,
                
                -- Poisson predictions
                pp.prob_home_win as poisson_prob_home,
                pp.prob_draw as poisson_prob_draw,
                pp.prob_away_win as poisson_prob_away,
                pp.over_2 as poisson_over_25,
                pp.both_score as poisson_btts,
                
                -- Weinston predictions
                wp.result_1x2 as weinston_result_int,
                wp.local_goals as weinston_home_goals,
                wp.away_goals as weinston_away_goals,
                
                -- Cálculo dinámico Over/Under para Weinston
                GREATEST(0.05, LEAST(0.95,
                    1.0 / (1.0 + EXP(-(COALESCE(wp.local_goals, 0) + COALESCE(wp.away_goals, 0) - 2.5) * 1.8))
                )) as weinston_over_25,
                
                -- Cálculo dinámico BTTS para Weinston
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
            ORDER BY m.date
            LIMIT 20
        """)
        
        upcoming_matches = conn.execute(upcoming_matches_query, {"season_id": season_id}).mappings().all()
        
        # 3. Analizar cada partido y calcular scores
        recommendations = []
        
        for match in upcoming_matches:
            match_id = match['match_id']
            home_team = match['home_team']
            away_team = match['away_team']
            date = match['date']
            
            # Analizar Poisson
            if match['poisson_prob_home'] is not None:
                poisson_accuracy = accuracy_by_model.get('poisson', {})
                
                # 1X2 - Predicción más probable
                prob_home = float(match['poisson_prob_home'] or 0)
                prob_draw = float(match['poisson_prob_draw'] or 0)
                prob_away = float(match['poisson_prob_away'] or 0)
                
                max_prob_1x2 = max(prob_home, prob_draw, prob_away)
                if max_prob_1x2 == prob_home:
                    prediction_1x2 = 'Victoria Local (1)'
                elif max_prob_1x2 == prob_away:
                    prediction_1x2 = 'Victoria Visitante (2)'
                else:
                    prediction_1x2 = 'Empate (X)'
                
                # Score 1X2 = Probabilidad * Accuracy histórica / 100
                score_1x2 = max_prob_1x2 * (poisson_accuracy.get('accuracy_1x2', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Poisson',
                    'bet_type': '1X2',
                    'prediction': prediction_1x2,
                    'confidence': round(max_prob_1x2 * 100, 1),
                    'historical_accuracy': poisson_accuracy.get('accuracy_1x2', 0),
                    'combined_score': round(score_1x2 * 100, 2)
                })
                
                # Over/Under
                over_prob = float(match['poisson_over_25'] or 0)
                under_prob = 1 - over_prob
                
                if over_prob > 0.5:
                    prediction_ou = f'Over 2.5'
                    confidence_ou = over_prob
                else:
                    prediction_ou = f'Under 2.5'
                    confidence_ou = under_prob
                
                score_ou = confidence_ou * (poisson_accuracy.get('accuracy_over25', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Poisson',
                    'bet_type': 'Over/Under',
                    'prediction': prediction_ou,
                    'confidence': round(confidence_ou * 100, 1),
                    'historical_accuracy': poisson_accuracy.get('accuracy_over25', 0),
                    'combined_score': round(score_ou * 100, 2)
                })
                
                # BTTS
                btts_prob = float(match['poisson_btts'] or 0)
                no_btts_prob = 1 - btts_prob
                
                if btts_prob > 0.5:
                    prediction_btts = 'Ambos anotan (Sí)'
                    confidence_btts = btts_prob
                else:
                    prediction_btts = 'Ambos NO anotan'
                    confidence_btts = no_btts_prob
                
                score_btts = confidence_btts * (poisson_accuracy.get('accuracy_btts', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Poisson',
                    'bet_type': 'BTTS',
                    'prediction': prediction_btts,
                    'confidence': round(confidence_btts * 100, 1),
                    'historical_accuracy': poisson_accuracy.get('accuracy_btts', 0),
                    'combined_score': round(score_btts * 100, 2)
                })
            
            # Analizar Weinston
            if match['weinston_result_int'] is not None:
                weinston_accuracy = accuracy_by_model.get('weinston', {})
                
                # 1X2
                result_int = match['weinston_result_int']
                if result_int == 0:
                    prediction_1x2 = 'Empate (X)'
                elif result_int == 1:
                    prediction_1x2 = 'Victoria Local (1)'
                else:
                    prediction_1x2 = 'Victoria Visitante (2)'
                
                # Weinston no tiene probabilidades por resultado, usar confianza base
                confidence_1x2 = 0.75  # Confianza base
                score_1x2 = confidence_1x2 * (weinston_accuracy.get('accuracy_1x2', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Weinston',
                    'bet_type': '1X2',
                    'prediction': prediction_1x2,
                    'confidence': round(confidence_1x2 * 100, 1),
                    'historical_accuracy': weinston_accuracy.get('accuracy_1x2', 0),
                    'combined_score': round(score_1x2 * 100, 2)
                })
                
                # Over/Under
                over_prob = float(match['weinston_over_25'] or 0)
                under_prob = 1 - over_prob
                
                if over_prob > 0.5:
                    prediction_ou = f'Over 2.5'
                    confidence_ou = over_prob
                else:
                    prediction_ou = f'Under 2.5'
                    confidence_ou = under_prob
                
                score_ou = confidence_ou * (weinston_accuracy.get('accuracy_over25', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Weinston',
                    'bet_type': 'Over/Under',
                    'prediction': prediction_ou,
                    'confidence': round(confidence_ou * 100, 1),
                    'historical_accuracy': weinston_accuracy.get('accuracy_over25', 0),
                    'combined_score': round(score_ou * 100, 2)
                })
                
                # BTTS
                btts_prob = float(match['weinston_btts'] or 0)
                no_btts_prob = 1 - btts_prob
                
                if btts_prob > 0.5:
                    prediction_btts = 'Ambos anotan (Sí)'
                    confidence_btts = btts_prob
                else:
                    prediction_btts = 'Ambos NO anotan'
                    confidence_btts = no_btts_prob
                
                score_btts = confidence_btts * (weinston_accuracy.get('accuracy_btts', 0) / 100)
                
                recommendations.append({
                    'match_id': match_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'model': 'Weinston',
                    'bet_type': 'BTTS',
                    'prediction': prediction_btts,
                    'confidence': round(confidence_btts * 100, 1),
                    'historical_accuracy': weinston_accuracy.get('accuracy_btts', 0),
                    'combined_score': round(score_btts * 100, 2)
                })
        
        # 4. Ordenar por combined_score descendente y tomar top 4
        recommendations.sort(key=lambda x: x['combined_score'], reverse=True)
        top_recommendations = recommendations[:4]

        # ✅ CORREGIDO: Guardar automáticamente las top 4 en best_bets_history
        if recommendations:
            top_4 = recommendations[:4]
            
            # Preparar datos para guardar
            with engine.begin() as conn_save:
                for idx, rec in enumerate(top_4, start=1):
                    
                    print(f"🔄 Procesando best bet {idx}: {rec['home_team']} vs {rec['away_team']} - {rec['bet_type']} - {rec['prediction']}")
                    
                    # Obtener odds de Poisson (simplificado y corregido)
                    odds_query = text("""
                        SELECT 
                            CASE 
                                WHEN pp.min_odds_1 > 0 THEN pp.min_odds_1
                                WHEN pp.min_odds_over25 > 0 THEN pp.min_odds_over25
                                WHEN pp.min_odds_btts_yes > 0 THEN pp.min_odds_btts_yes
                                ELSE 1.85
                            END as odds
                        FROM poisson_predictions pp
                        WHERE pp.match_id = :match_id
                        LIMIT 1
                    """)
                    
                    try:
                        odds_result = conn_save.execute(odds_query, {
                            "match_id": rec['match_id']
                        }).scalar()
                        odds = float(odds_result) if odds_result else 1.85
                        print(f"   💰 Odds obtenidas: {odds}")
                    except Exception as e:
                        print(f"   ⚠️ Error obteniendo odds: {e}")
                        odds = 1.85
                    
                    # 🔥 CORREGIDO: Formateo de fecha
                    try:
                        if isinstance(rec['date'], str):
                            date_str = rec['date'][:10]  # Solo YYYY-MM-DD
                        else:
                            date_str = rec['date'].strftime("%Y-%m-%d")
                        print(f"   📅 Fecha procesada: {date_str}")
                    except Exception as e:
                        print(f"   ⚠️ Error con fecha: {e}")
                        date_str = "2025-11-10"  # Fallback
                    
                    # 🔥 CORREGIDO: Mapeo de bet_type
                    bet_type_map = {
                        '1X2': '1X2',
                        'Over/Under': 'OVER_UNDER', 
                        'BTTS': 'BTTS'
                    }
                    bet_type_clean = bet_type_map.get(rec['bet_type'], rec['bet_type'])
                    
                    # Insertar en best_bets_history
                    upsert_query = text("""
                        INSERT INTO best_bets_history (
                            match_id, season_id, date, home_team, away_team,
                            model, bet_type, prediction,
                            confidence, historical_accuracy, combined_score, rank, odds,
                            created_at
                        ) VALUES (
                            :match_id, :season_id, :date, :home_team, :away_team,
                            :model, :bet_type, :prediction,
                            :confidence, :historical_accuracy, :combined_score, :rank, :odds,
                            NOW()
                        )
                        ON CONFLICT (match_id, model, bet_type) 
                        DO UPDATE SET
                            prediction = EXCLUDED.prediction,
                            confidence = EXCLUDED.confidence,
                            historical_accuracy = EXCLUDED.historical_accuracy,
                            combined_score = EXCLUDED.combined_score,
                            rank = EXCLUDED.rank,
                            odds = EXCLUDED.odds,
                            created_at = NOW()
                    """)
                    
                    try:
                        conn_save.execute(upsert_query, {
                            "match_id": int(rec['match_id']),
                            "season_id": int(season_id),
                            "date": date_str,
                            "home_team": str(rec['home_team']),
                            "away_team": str(rec['away_team']),
                            "model": str(rec['model']).lower(),
                            "bet_type": bet_type_clean,
                            "prediction": str(rec['prediction']),
                            "confidence": float(rec['confidence']),
                            "historical_accuracy": float(rec['historical_accuracy']),
                            "combined_score": float(rec['combined_score']),
                            "rank": int(idx),
                            "odds": float(odds)
                        })
                        print(f"   ✅ Best bet {idx} guardada exitosamente en BD")
                    except Exception as e:
                        print(f"   ❌ Error guardando best bet {idx}: {e}")
                        print(f"   📝 Datos que intentaba insertar:")
                        print(f"      match_id: {rec['match_id']}")
                        print(f"      season_id: {season_id}")
                        print(f"      date: {date_str}")
                        print(f"      model: {str(rec['model']).lower()}")
                        print(f"      bet_type: {bet_type_clean}")
                        print(f"      prediction: {str(rec['prediction'])}")
        
        return {
            'historical_accuracy': dict(accuracy_by_model),
            'top_bets': top_recommendations,
            'all_recommendations': recommendations[:10]
        }
    

@router.post("/api/betting-lines/generate")
def generate_betting_lines_predictions(season_id: int = Query(...)):
    """
    Genera predicciones de líneas de apuesta (Over/Under) para todos los partidos sin resultado
    
    Líneas de apuesta estándar (basadas en Premier League):
    - Tiros totales: 24.5
    - Tiros a puerta: 8.5
    - Corners: 10.5
    - Tarjetas: 4.5
    - Faltas: 22.5
    """
    
    # Configuración de líneas (pueden ajustarse basándose en análisis histórico)
    BETTING_LINES = {
        'shots': 24.5,
        'shots_on_target': 8.5,
        'corners': 10.5,
        'cards': 4.5,
        'fouls': 22.5
    }
    
    with engine.begin() as conn:
        # Obtener partidos sin resultado
        matches_query = text("""
            SELECT 
                m.id as match_id,
                m.date,
                th.name as home_team,
                ta.name as away_team,
                
                -- Predicciones Poisson
                pp.expected_home_goals as poisson_home_goals,
                pp.expected_away_goals as poisson_away_goals,
                
                -- Predicciones Weinston (estadísticas)
                wp.shots_home as weinston_shots_home,
                wp.shots_away as weinston_shots_away,
                wp.shots_target_home as weinston_shots_on_target_home,
                wp.shots_target_away as weinston_shots_on_target_away,
                wp.corners_home as weinston_corners_home,
                wp.corners_away as weinston_corners_away,
                wp.cards_home as weinston_cards_home,
                wp.cards_away as weinston_cards_away,
                wp.fouls_home as weinston_fouls_home,
                wp.fouls_away as weinston_fouls_away
                
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NULL
              AND m.date >= CURRENT_DATE
            ORDER BY m.date
        """)
        
        matches = conn.execute(matches_query, {"season_id": season_id}).mappings().all()
        
        generated_predictions = []
        
        for match in matches:
            match_id = match['match_id']
            
            # WEINSTON: Calcular totales predichos
            if match['weinston_shots_home'] is not None:
                # Tiros
                predicted_shots = float(match['weinston_shots_home'] or 0) + float(match['weinston_shots_away'] or 0)
                shots_line = BETTING_LINES['shots']
                shots_prediction = 'over' if predicted_shots > shots_line else 'under'
                # Confianza: distancia normalizada del umbral (0-1)
                shots_distance = abs(predicted_shots - shots_line)
                shots_confidence = min(shots_distance / 10.0, 1.0)  # Normalizar a 0-1
                
                # Tiros a puerta
                predicted_shots_ot = float(match['weinston_shots_on_target_home'] or 0) + float(match['weinston_shots_on_target_away'] or 0)
                shots_ot_line = BETTING_LINES['shots_on_target']
                shots_ot_prediction = 'over' if predicted_shots_ot > shots_ot_line else 'under'
                shots_ot_distance = abs(predicted_shots_ot - shots_ot_line)
                shots_ot_confidence = min(shots_ot_distance / 5.0, 1.0)
                
                # Corners
                predicted_corners = float(match['weinston_corners_home'] or 0) + float(match['weinston_corners_away'] or 0)
                corners_line = BETTING_LINES['corners']
                corners_prediction = 'over' if predicted_corners > corners_line else 'under'
                corners_distance = abs(predicted_corners - corners_line)
                corners_confidence = min(corners_distance / 5.0, 1.0)
                
                # Tarjetas
                predicted_cards = float(match['weinston_cards_home'] or 0) + float(match['weinston_cards_away'] or 0)
                cards_line = BETTING_LINES['cards']
                cards_prediction = 'over' if predicted_cards > cards_line else 'under'
                cards_distance = abs(predicted_cards - cards_line)
                cards_confidence = min(cards_distance / 3.0, 1.0)
                
                # Faltas
                predicted_fouls = float(match['weinston_fouls_home'] or 0) + float(match['weinston_fouls_away'] or 0)
                fouls_line = BETTING_LINES['fouls']
                fouls_prediction = 'over' if predicted_fouls > fouls_line else 'under'
                fouls_distance = abs(predicted_fouls - fouls_line)
                fouls_confidence = min(fouls_distance / 8.0, 1.0)
                
                # Insertar o actualizar predicciones
                insert_query = text("""
                    INSERT INTO betting_lines_predictions (
                        match_id, model,
                        predicted_total_shots, shots_line, shots_prediction, shots_confidence,
                        predicted_total_shots_on_target, shots_on_target_line, shots_on_target_prediction, shots_on_target_confidence,
                        predicted_total_corners, corners_line, corners_prediction, corners_confidence,
                        predicted_total_cards, cards_line, cards_prediction, cards_confidence,
                        predicted_total_fouls, fouls_line, fouls_prediction, fouls_confidence
                    ) VALUES (
                        :match_id, 'weinston',
                        :predicted_shots, :shots_line, :shots_prediction, :shots_confidence,
                        :predicted_shots_ot, :shots_ot_line, :shots_ot_prediction, :shots_ot_confidence,
                        :predicted_corners, :corners_line, :corners_prediction, :corners_confidence,
                        :predicted_cards, :cards_line, :cards_prediction, :cards_confidence,
                        :predicted_fouls, :fouls_line, :fouls_prediction, :fouls_confidence
                    )
                    ON CONFLICT (match_id, model) 
                    DO UPDATE SET
                        predicted_total_shots = EXCLUDED.predicted_total_shots,
                        shots_line = EXCLUDED.shots_line,
                        shots_prediction = EXCLUDED.shots_prediction,
                        shots_confidence = EXCLUDED.shots_confidence,
                        predicted_total_shots_on_target = EXCLUDED.predicted_total_shots_on_target,
                        shots_on_target_line = EXCLUDED.shots_on_target_line,
                        shots_on_target_prediction = EXCLUDED.shots_on_target_prediction,
                        shots_on_target_confidence = EXCLUDED.shots_on_target_confidence,
                        predicted_total_corners = EXCLUDED.predicted_total_corners,
                        corners_line = EXCLUDED.corners_line,
                        corners_prediction = EXCLUDED.corners_prediction,
                        corners_confidence = EXCLUDED.corners_confidence,
                        predicted_total_cards = EXCLUDED.predicted_total_cards,
                        cards_line = EXCLUDED.cards_line,
                        cards_prediction = EXCLUDED.cards_prediction,
                        cards_confidence = EXCLUDED.cards_confidence,
                        predicted_total_fouls = EXCLUDED.predicted_total_fouls,
                        fouls_line = EXCLUDED.fouls_line,
                        fouls_prediction = EXCLUDED.fouls_prediction,
                        fouls_confidence = EXCLUDED.fouls_confidence,
                        updated_at = CURRENT_TIMESTAMP
                """)
                
                conn.execute(insert_query, {
                    "match_id": match_id,
                    "predicted_shots": predicted_shots,
                    "shots_line": shots_line,
                    "shots_prediction": shots_prediction,
                    "shots_confidence": shots_confidence,
                    "predicted_shots_ot": predicted_shots_ot,
                    "shots_ot_line": shots_ot_line,
                    "shots_ot_prediction": shots_ot_prediction,
                    "shots_ot_confidence": shots_ot_confidence,
                    "predicted_corners": predicted_corners,
                    "corners_line": corners_line,
                    "corners_prediction": corners_prediction,
                    "corners_confidence": corners_confidence,
                    "predicted_cards": predicted_cards,
                    "cards_line": cards_line,
                    "cards_prediction": cards_prediction,
                    "cards_confidence": cards_confidence,
                    "predicted_fouls": predicted_fouls,
                    "fouls_line": fouls_line,
                    "fouls_prediction": fouls_prediction,
                    "fouls_confidence": fouls_confidence
                })
                
                generated_predictions.append({
                    'match_id': match_id,
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'date': str(match['date']),
                    'predictions': {
                        'shots': {
                            'predicted': round(predicted_shots, 2),
                            'line': shots_line,
                            'prediction': shots_prediction,
                            'confidence': round(shots_confidence * 100, 1)
                        },
                        'shots_on_target': {
                            'predicted': round(predicted_shots_ot, 2),
                            'line': shots_ot_line,
                            'prediction': shots_ot_prediction,
                            'confidence': round(shots_ot_confidence * 100, 1)
                        },
                        'corners': {
                            'predicted': round(predicted_corners, 2),
                            'line': corners_line,
                            'prediction': corners_prediction,
                            'confidence': round(corners_confidence * 100, 1)
                        },
                        'cards': {
                            'predicted': round(predicted_cards, 2),
                            'line': cards_line,
                            'prediction': cards_prediction,
                            'confidence': round(cards_confidence * 100, 1)
                        },
                        'fouls': {
                            'predicted': round(predicted_fouls, 2),
                            'line': fouls_line,
                            'prediction': fouls_prediction,
                            'confidence': round(fouls_confidence * 100, 1)
                        }
                    }
                })
        
        return {
            'betting_lines': BETTING_LINES,
            'total_matches': len(matches),
            'predictions_generated': len(generated_predictions),
            'predictions': generated_predictions
        }


@router.post("/api/betting-lines/validate")
def validate_betting_lines(season_id: int = Query(...)):
    """
    Valida las predicciones de líneas de apuesta contra los resultados reales
    Se ejecuta después de que los partidos han finalizado
    """
    
    with engine.begin() as conn:
        # Actualizar resultados reales y validar predicciones
        update_query = text("""
            UPDATE betting_lines_predictions blp
            SET 
                -- Actualizar resultados reales
                actual_total_shots = ms.home_shots + ms.away_shots,
                actual_total_shots_on_target = ms.home_shots_on_target + ms.away_shots_on_target,
                actual_total_corners = ms.home_corners + ms.away_corners,
                actual_total_cards = ms.home_yellow_cards + ms.away_yellow_cards + 
                                    COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0),
                actual_total_fouls = ms.home_fouls + ms.away_fouls,
                
                -- Validar predicciones (TRUE si acertó)
                shots_hit = CASE 
                    WHEN blp.shots_prediction = 'over' AND (ms.home_shots + ms.away_shots) > blp.shots_line THEN TRUE
                    WHEN blp.shots_prediction = 'under' AND (ms.home_shots + ms.away_shots) < blp.shots_line THEN TRUE
                    ELSE FALSE
                END,
                
                shots_on_target_hit = CASE 
                    WHEN blp.shots_on_target_prediction = 'over' AND (ms.home_shots_on_target + ms.away_shots_on_target) > blp.shots_on_target_line THEN TRUE
                    WHEN blp.shots_on_target_prediction = 'under' AND (ms.home_shots_on_target + ms.away_shots_on_target) < blp.shots_on_target_line THEN TRUE
                    ELSE FALSE
                END,
                
                corners_hit = CASE 
                    WHEN blp.corners_prediction = 'over' AND (ms.home_corners + ms.away_corners) > blp.corners_line THEN TRUE
                    WHEN blp.corners_prediction = 'under' AND (ms.home_corners + ms.away_corners) < blp.corners_line THEN TRUE
                    ELSE FALSE
                END,
                
                cards_hit = CASE 
                    WHEN blp.cards_prediction = 'over' AND (ms.home_yellow_cards + ms.away_yellow_cards + COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0)) > blp.cards_line THEN TRUE
                    WHEN blp.cards_prediction = 'under' AND (ms.home_yellow_cards + ms.away_yellow_cards + COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0)) < blp.cards_line THEN TRUE
                    ELSE FALSE
                END,
                
                fouls_hit = CASE 
                    WHEN blp.fouls_prediction = 'over' AND (ms.home_fouls + ms.away_fouls) > blp.fouls_line THEN TRUE
                    WHEN blp.fouls_prediction = 'under' AND (ms.home_fouls + ms.away_fouls) < blp.fouls_line THEN TRUE
                    ELSE FALSE
                END,
                
                updated_at = CURRENT_TIMESTAMP
                
            FROM matches m
            JOIN match_stats ms ON ms.match_id = m.id
            WHERE blp.match_id = m.id
              AND m.season_id = :season_id
              AND m.home_goals IS NOT NULL
              AND blp.actual_total_shots IS NULL
        """)
        
        result = conn.execute(update_query, {"season_id": season_id})
        updated_count = result.rowcount
        
        # Obtener accuracy general
        accuracy_query = text("""
            SELECT 
                blp.model,
                COUNT(*) as total_predictions,
                
                -- Accuracy por tipo de predicción
                ROUND(AVG(CASE WHEN blp.shots_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as shots_accuracy,
                ROUND(AVG(CASE WHEN blp.shots_on_target_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as shots_ot_accuracy,
                ROUND(AVG(CASE WHEN blp.corners_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as corners_accuracy,
                ROUND(AVG(CASE WHEN blp.cards_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as cards_accuracy,
                ROUND(AVG(CASE WHEN blp.fouls_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as fouls_accuracy,
                
                -- Accuracy promedio
                ROUND(AVG(
                    (CASE WHEN blp.shots_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.shots_on_target_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.corners_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.cards_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.fouls_hit THEN 1.0 ELSE 0.0 END) / 5.0
                ) * 100, 2) as overall_accuracy
                
            FROM betting_lines_predictions blp
            JOIN matches m ON m.id = blp.match_id
            WHERE m.season_id = :season_id
              AND blp.actual_total_shots IS NOT NULL
            GROUP BY blp.model
        """)
        
        accuracy_results = conn.execute(accuracy_query, {"season_id": season_id}).mappings().all()
        
        return {
            'validated_predictions': updated_count,
            'accuracy_by_model': [dict(row) for row in accuracy_results]
        }


@router.get("/api/betting-lines/matches/{match_id}")
def get_betting_lines_for_match(match_id: int):
    """
    Obtiene las predicciones de líneas de apuesta para un partido específico
    """
    
    with engine.begin() as conn:
        query = text("""
            SELECT 
                blp.*,
                m.date,
                th.name as home_team,
                ta.name as away_team,
                m.home_goals,
                m.away_goals
            FROM betting_lines_predictions blp
            JOIN matches m ON m.id = blp.match_id
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            WHERE blp.match_id = :match_id
        """)
        
        result = conn.execute(query, {"match_id": match_id}).mappings().first()
        
        if not result:
            raise HTTPException(status_code=404, detail="No se encontraron predicciones para este partido")
        
        return dict(result)    
    
# ============================================================================
# ENDPOINTS DE BETTING LINES
# ============================================================================

@app.get("/api/betting-lines/match/{match_id}")
def get_betting_lines_by_match(match_id: int, model: str = Query("weinston")):
    """
    Obtiene las betting lines de un partido específico para mostrar en la tabla
    """
    query = text("""
        SELECT 
            bl.match_id,
            
            -- Tiros
            bl.predicted_total_shots,
            bl.shots_line,
            bl.shots_prediction,
            bl.shots_confidence,
            bl.actual_total_shots,
            bl.shots_hit,
            
            -- Tiros a puerta
            bl.predicted_total_shots_on_target,
            bl.shots_on_target_line,
            bl.shots_on_target_prediction,
            bl.shots_on_target_confidence,
            bl.actual_total_shots_on_target,
            bl.shots_on_target_hit,
            
            -- Corners
            bl.predicted_total_corners,
            bl.corners_line,
            bl.corners_prediction,
            bl.corners_confidence,
            bl.actual_total_corners,
            bl.corners_hit,
            
            -- Tarjetas
            bl.predicted_total_cards,
            bl.cards_line,
            bl.cards_prediction,
            bl.cards_confidence,
            bl.actual_total_cards,
            bl.cards_hit,
            
            -- Faltas
            bl.predicted_total_fouls,
            bl.fouls_line,
            bl.fouls_prediction,
            bl.fouls_confidence,
            bl.actual_total_fouls,
            bl.fouls_hit
            
        FROM betting_lines_predictions bl
        WHERE bl.match_id = :match_id
          AND bl.model = :model
    """)
    
    with engine.begin() as conn:
        result = conn.execute(query, {"match_id": match_id, "model": model}).mappings().first()
        
        if not result:
            return None
        
        return dict(result)


@app.get("/api/betting-lines/season/{season_id}")
def get_betting_lines_by_season(
    season_id: int,
    model: str = Query("weinston"),
    validated: Optional[bool] = Query(None)
):
    """
    Obtiene todas las betting lines de una temporada
    """
    where_clauses = ["m.season_id = :season_id", "bl.model = :model"]
    params = {"season_id": season_id, "model": model}
    
    if validated is not None:
        if validated:
            where_clauses.append("bl.actual_total_shots IS NOT NULL")
        else:
            where_clauses.append("bl.actual_total_shots IS NULL")
    
    query = text(f"""
        SELECT 
            bl.match_id,
            m.date,
            t1.name as home_team,
            t2.name as away_team,
            
            -- Betting lines resumidas
            bl.shots_prediction,
            bl.shots_line,
            bl.shots_confidence,
            bl.shots_hit,
            
            bl.corners_prediction,
            bl.corners_line,
            bl.corners_confidence,
            bl.corners_hit,
            
            bl.cards_prediction,
            bl.cards_line,
            bl.cards_confidence,
            bl.cards_hit
            
        FROM betting_lines_predictions bl
        JOIN matches m ON m.id = bl.match_id
        JOIN teams t1 ON t1.id = m.home_team_id
        JOIN teams t2 ON t2.id = m.away_team_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY m.date DESC
    """)
    
    with engine.begin() as conn:
        results = conn.execute(query, params).mappings().all()
        return [dict(r) for r in results]


@app.get("/api/betting-lines/accuracy/{season_id}")
def get_betting_lines_accuracy(season_id: int):
    """
    Obtiene el accuracy de betting lines por modelo
    """
    query = text("""
        SELECT 
            bl.model,
            COUNT(*) as total,
            ROUND(AVG(CASE WHEN bl.shots_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as shots_acc,
            ROUND(AVG(CASE WHEN bl.shots_on_target_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as shots_ot_acc,
            ROUND(AVG(CASE WHEN bl.corners_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as corners_acc,
            ROUND(AVG(CASE WHEN bl.cards_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as cards_acc,
            ROUND(AVG(CASE WHEN bl.fouls_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as fouls_acc,
            ROUND(AVG(
                (CASE WHEN bl.shots_hit THEN 1.0 ELSE 0.0 END +
                 CASE WHEN bl.shots_on_target_hit THEN 1.0 ELSE 0.0 END +
                 CASE WHEN bl.corners_hit THEN 1.0 ELSE 0.0 END +
                 CASE WHEN bl.cards_hit THEN 1.0 ELSE 0.0 END +
                 CASE WHEN bl.fouls_hit THEN 1.0 ELSE 0.0 END) / 5.0
            ) * 100, 1) as overall_acc
        FROM betting_lines_predictions bl
        JOIN matches m ON m.id = bl.match_id
        WHERE m.season_id = :season_id
          AND bl.actual_total_shots IS NOT NULL
        GROUP BY bl.model
    """)
    
    with engine.begin() as conn:
        results = conn.execute(query, {"season_id": season_id}).mappings().all()
        return [dict(r) for r in results]   


@app.get("/api/matches/{match_id}/h2h-analysis")
async def get_h2h_analysis(match_id: int):
    """
    Obtiene análisis de enfrentamientos directos (H2H) con narrativa generada.
    Analiza hasta 12 partidos previos: 6 como local + 6 como visitante.
    """
    
    with engine.begin() as conn:
        # 1. Obtener información del partido actual
        match_info_query = text("""
            SELECT 
                m.id,
                m.date,
                m.home_team_id,
                m.away_team_id,
                m.season_id,
                ht.name as home_team,
                at.name as away_team,
                m.home_goals,
                m.away_goals,
                
                -- Predicciones de Weinston
                wp.local_goals as pred_home_goals,
                wp.away_goals as pred_away_goals,
                wp.shots_home as pred_home_shots,
                wp.shots_away as pred_away_shots,
                wp.corners_home as pred_home_corners,
                wp.corners_away as pred_away_corners,
                wp.cards_home as pred_home_cards,
                wp.cards_away as pred_away_cards,
                wp.both_score as pred_btts,
                wp.over_2 as pred_over25
                
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.id = :match_id
        """)
        
        match_info = conn.execute(match_info_query, {"match_id": match_id}).mappings().first()
        
        if not match_info:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        
        match_info = dict(match_info)
        
        # 2. Obtener últimos 6 H2H cuando el equipo HOME jugó de LOCAL
        # Ejemplo: Brighton (home) vs Leeds (away) - buscamos partidos donde Brighton fue local contra Leeds
        h2h_home_query = text("""
            SELECT 
                m.id,
                m.date,
                CONCAT(s.year_start, '/', s.year_end) as season,
                m.home_goals,
                m.away_goals,
                m.home_goals + m.away_goals as total_goals,
                CASE WHEN m.home_goals > 0 AND m.away_goals > 0 THEN true ELSE false END as btts,
                CASE WHEN m.home_goals + m.away_goals >= 3 THEN true ELSE false END as over25,
                
                -- Estadísticas
                COALESCE(ms.home_shots, 0) as home_shots,
                COALESCE(ms.away_shots, 0) as away_shots,
                COALESCE(ms.home_shots_on_target, 0) as home_shots_on_target,
                COALESCE(ms.away_shots_on_target, 0) as away_shots_on_target,
                COALESCE(ms.home_corners, 0) as home_corners,
                COALESCE(ms.away_corners, 0) as away_corners,
                COALESCE(ms.home_fouls, 0) as home_fouls,
                COALESCE(ms.away_fouls, 0) as away_fouls,
                COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0) as home_cards,
                COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0) as away_cards,
                
                -- Totales
                COALESCE(ms.total_shots, 0) as total_shots,
                COALESCE(ms.total_corners, 0) as total_corners,
                COALESCE(ms.total_fouls, 0) as total_fouls,
                COALESCE(ms.total_cards, 0) as total_cards
                
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            LEFT JOIN match_stats ms ON ms.match_id = m.id
            WHERE m.home_team_id = :home_team_id
              AND m.away_team_id = :away_team_id
              AND m.home_goals IS NOT NULL
              AND m.id != :current_match_id
              AND m.date < :match_date
            ORDER BY m.date DESC
            LIMIT 6
        """)
        
        h2h_home_rows = conn.execute(h2h_home_query, {
            "home_team_id": match_info["home_team_id"],
            "away_team_id": match_info["away_team_id"],
            "current_match_id": match_id,
            "match_date": match_info["date"]
        }).mappings().all()
        
        h2h_home = [dict(row) for row in h2h_home_rows]
        
        # 3. Obtener últimos 6 H2H cuando el equipo HOME jugó de VISITANTE
        # Ejemplo: Brighton (home hoy) vs Leeds - buscamos partidos donde Brighton fue visitante contra Leeds
        # Es decir: Leeds (home) vs Brighton (away)
        h2h_away_query = text("""
            SELECT 
                m.id,
                m.date,
                CONCAT(s.year_start, '/', s.year_end) as season,
                m.away_goals as team_goals,
                m.home_goals as opponent_goals,
                m.home_goals + m.away_goals as total_goals,
                CASE WHEN m.home_goals > 0 AND m.away_goals > 0 THEN true ELSE false END as btts,
                CASE WHEN m.home_goals + m.away_goals >= 3 THEN true ELSE false END as over25,
                
                -- Estadísticas (desde la perspectiva del equipo que hoy es local)
                COALESCE(ms.away_shots, 0) as team_shots,
                COALESCE(ms.home_shots, 0) as opponent_shots,
                COALESCE(ms.away_shots_on_target, 0) as team_shots_on_target,
                COALESCE(ms.home_shots_on_target, 0) as opponent_shots_on_target,
                COALESCE(ms.away_corners, 0) as team_corners,
                COALESCE(ms.home_corners, 0) as opponent_corners,
                COALESCE(ms.away_fouls, 0) as team_fouls,
                COALESCE(ms.home_fouls, 0) as opponent_fouls,
                COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0) as team_cards,
                COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0) as opponent_cards,
                
                -- Totales
                COALESCE(ms.total_shots, 0) as total_shots,
                COALESCE(ms.total_corners, 0) as total_corners,
                COALESCE(ms.total_fouls, 0) as total_fouls,
                COALESCE(ms.total_cards, 0) as total_cards,
                
                -- Para mostrar el marcador correctamente (home - away del partido histórico)
                m.home_goals,
                m.away_goals
                
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            LEFT JOIN match_stats ms ON ms.match_id = m.id
            WHERE m.away_team_id = :home_team_id
              AND m.home_team_id = :away_team_id
              AND m.home_goals IS NOT NULL
              AND m.id != :current_match_id
              AND m.date < :match_date
            ORDER BY m.date DESC
            LIMIT 6
        """)
        
        h2h_away_rows = conn.execute(h2h_away_query, {
            "home_team_id": match_info["home_team_id"],
            "away_team_id": match_info["away_team_id"],
            "current_match_id": match_id,
            "match_date": match_info["date"]
        }).mappings().all()
        
        h2h_away = [dict(row) for row in h2h_away_rows]
        
        # 4. Calcular estadísticas agregadas
        stats = calculate_h2h_stats(h2h_home, h2h_away, match_info)
        
        # 5. Generar narrativa
        narrative = generate_match_narrative(match_info, stats, h2h_home, h2h_away)
        
        return {
            "match_id": match_id,
            "home_team": match_info["home_team"],
            "away_team": match_info["away_team"],
            "date": match_info["date"],
            "h2h_home": h2h_home,
            "h2h_away": h2h_away,
            "stats": stats,
            "narrative": narrative,
            "predictions": {
                "home_goals": match_info["pred_home_goals"],
                "away_goals": match_info["pred_away_goals"],
                "home_shots": match_info["pred_home_shots"],
                "away_shots": match_info["pred_away_shots"],
                "home_corners": match_info["pred_home_corners"],
                "away_corners": match_info["pred_away_corners"],
                "btts": match_info["pred_btts"],
                "over25": match_info["pred_over25"]
            }
        }


# ==============================================================================
# FUNCIONES CORREGIDAS: calculate_h2h_stats y generate_match_narrative
# Incluye TODAS las estadísticas: goles, tiros, tiros a puerta, corners, faltas y tarjetas
# ==============================================================================

def calculate_h2h_stats(h2h_home: List[Dict], h2h_away: List[Dict], match_info: Dict) -> Dict[str, Any]:
    """
    Calcula estadísticas agregadas del H2H con TODAS las métricas
    """
    all_matches = h2h_home + h2h_away
    total_matches = len(all_matches)
    
    if total_matches == 0:
        return {
            "total_matches": 0,
            "has_data": False,
            "message": "No hay datos históricos de enfrentamientos directos"
        }
    
    # Promedios
    stats = {
        "total_matches": total_matches,
        "matches_home_venue": len(h2h_home),
        "matches_away_venue": len(h2h_away),
        "has_data": True,
        
        # Promedios generales (todos los partidos)
        "avg_total_goals": sum(m["total_goals"] for m in all_matches) / total_matches if total_matches > 0 else 0,
        "avg_total_shots": sum(m.get("total_shots", 0) for m in all_matches) / total_matches if total_matches > 0 else 0,
        "avg_total_corners": sum(m.get("total_corners", 0) for m in all_matches) / total_matches if total_matches > 0 else 0,
        "avg_total_fouls": sum(m.get("total_fouls", 0) for m in all_matches) / total_matches if total_matches > 0 else 0,
        "avg_total_cards": sum(m.get("total_cards", 0) for m in all_matches) / total_matches if total_matches > 0 else 0,
        
        # Frecuencias
        "btts_count": sum(1 for m in all_matches if m.get("btts")),
        "btts_percentage": (sum(1 for m in all_matches if m.get("btts")) / total_matches * 100) if total_matches > 0 else 0,
        
        "over25_count": sum(1 for m in all_matches if m.get("over25")),
        "over25_percentage": (sum(1 for m in all_matches if m.get("over25")) / total_matches * 100) if total_matches > 0 else 0,
    }
    
    # Promedios específicos de LOCAL (equipo que hoy juega de local)
    if h2h_home:
        stats["home_venue"] = {
            "matches": len(h2h_home),
            # Goles
            "avg_home_goals": sum(m["home_goals"] for m in h2h_home) / len(h2h_home),
            "avg_away_goals": sum(m["away_goals"] for m in h2h_home) / len(h2h_home),
            # Tiros
            "avg_home_shots": sum(m.get("home_shots", 0) for m in h2h_home) / len(h2h_home),
            "avg_away_shots": sum(m.get("away_shots", 0) for m in h2h_home) / len(h2h_home),
            # Tiros a puerta
            "avg_home_shots_on_target": sum(m.get("home_shots_on_target", 0) for m in h2h_home) / len(h2h_home),
            "avg_away_shots_on_target": sum(m.get("away_shots_on_target", 0) for m in h2h_home) / len(h2h_home),
            # Corners
            "avg_home_corners": sum(m.get("home_corners", 0) for m in h2h_home) / len(h2h_home),
            "avg_away_corners": sum(m.get("away_corners", 0) for m in h2h_home) / len(h2h_home),
            # Faltas
            "avg_home_fouls": sum(m.get("home_fouls", 0) for m in h2h_home) / len(h2h_home),
            "avg_away_fouls": sum(m.get("away_fouls", 0) for m in h2h_home) / len(h2h_home),
            # Tarjetas
            "avg_home_cards": sum(m.get("home_cards", 0) for m in h2h_home) / len(h2h_home),
            "avg_away_cards": sum(m.get("away_cards", 0) for m in h2h_home) / len(h2h_home),
        }
    
    # Promedios específicos de VISITANTE (equipo que hoy juega de local, pero en partidos donde fue visitante)
    if h2h_away:
        stats["away_venue"] = {
            "matches": len(h2h_away),
            # Goles (team = equipo que hoy es local, opponent = equipo que hoy es visitante)
            "avg_team_goals": sum(m["team_goals"] for m in h2h_away) / len(h2h_away),
            "avg_opponent_goals": sum(m["opponent_goals"] for m in h2h_away) / len(h2h_away),
            # Tiros
            "avg_team_shots": sum(m.get("team_shots", 0) for m in h2h_away) / len(h2h_away),
            "avg_opponent_shots": sum(m.get("opponent_shots", 0) for m in h2h_away) / len(h2h_away),
            # Tiros a puerta
            "avg_team_shots_on_target": sum(m.get("team_shots_on_target", 0) for m in h2h_away) / len(h2h_away),
            "avg_opponent_shots_on_target": sum(m.get("opponent_shots_on_target", 0) for m in h2h_away) / len(h2h_away),
            # Corners
            "avg_team_corners": sum(m.get("team_corners", 0) for m in h2h_away) / len(h2h_away),
            "avg_opponent_corners": sum(m.get("opponent_corners", 0) for m in h2h_away) / len(h2h_away),
            # Faltas
            "avg_team_fouls": sum(m.get("team_fouls", 0) for m in h2h_away) / len(h2h_away),
            "avg_opponent_fouls": sum(m.get("opponent_fouls", 0) for m in h2h_away) / len(h2h_away),
            # Tarjetas
            "avg_team_cards": sum(m.get("team_cards", 0) for m in h2h_away) / len(h2h_away),
            "avg_opponent_cards": sum(m.get("opponent_cards", 0) for m in h2h_away) / len(h2h_away),
        }
    
    return stats


def generate_match_narrative(match_info: Dict, stats: Dict, h2h_home: List[Dict], h2h_away: List[Dict]) -> Dict[str, str]:
    """
    Genera narrativa textual del análisis H2H con resumen de resultados y estadísticas
    """
    home_team = match_info["home_team"]
    away_team = match_info["away_team"]
    
    if not stats.get("has_data"):
        return {
            "summary": f"No hay datos históricos disponibles para enfrentamientos entre {home_team} y {away_team}.",
            "home_venue_analysis": "",
            "away_venue_analysis": "",
            "prediction_analysis": "",
            "conclusion": ""
        }
    
    # 1. RESUMEN GENERAL
    summary = f"""En los últimos {stats['total_matches']} enfrentamientos directos entre {home_team} y {away_team}, se han promediado {stats['avg_total_goals']:.1f} goles por partido. """
    
    if stats['btts_percentage'] >= 60:
        summary += f"Ambos equipos han anotado en el {stats['btts_percentage']:.0f}% de los encuentros, mostrando una clara tendencia ofensiva. "
    elif stats['btts_percentage'] <= 30:
        summary += f"Solo en el {stats['btts_percentage']:.0f}% de los partidos ambos equipos han marcado, indicando encuentros con pocos goles. "
    
    if stats['over25_percentage'] >= 60:
        summary += f"El {stats['over25_percentage']:.0f}% de los partidos han tenido más de 2.5 goles."
    
    # 2. ANÁLISIS CUANDO JUEGA DE LOCAL CON RESUMEN DE RESULTADOS
    home_venue_analysis = ""
    if h2h_home:
        home_stats = stats.get("home_venue", {})
        
        # 🎯 CALCULAR RESULTADOS (G-E-P, BTTS, Over 2.5)
        wins = sum(1 for m in h2h_home if m['home_goals'] > m['away_goals'])
        draws = sum(1 for m in h2h_home if m['home_goals'] == m['away_goals'])
        losses = sum(1 for m in h2h_home if m['home_goals'] < m['away_goals'])
        btts_count = sum(1 for m in h2h_home if m.get('btts', False))
        over25_count = sum(1 for m in h2h_home if m.get('over25', False))
        total_home_matches = len(h2h_home)
        
        # Construir narrativa con resumen de resultados
        home_venue_analysis = f"""Cuando {home_team} ha jugado de local contra {away_team} (últimos {total_home_matches} partidos):
{home_team}: G{wins}-E{draws}-P{losses} | BTTS: {btts_count}/{total_home_matches} | Over 2.5: {over25_count}/{total_home_matches}

- Promedio de goles: {home_team} {home_stats['avg_home_goals']:.1f} - {away_team} {home_stats['avg_away_goals']:.1f}
- Promedio de tiros: {home_stats['avg_home_shots']:.1f} del {home_team} vs {home_stats['avg_away_shots']:.1f} del {away_team}
- Promedio de tiros al arco: {home_stats['avg_home_shots_on_target']:.1f} del {home_team} vs {home_stats['avg_away_shots_on_target']:.1f} del {away_team}
- Promedio de corners: {home_stats['avg_home_corners']:.1f} del {home_team} vs {home_stats['avg_away_corners']:.1f} del {away_team}
- Promedio de faltas: {home_stats['avg_home_fouls']:.1f} del {home_team} vs {home_stats['avg_away_fouls']:.1f} del {away_team}
- Promedio de tarjetas: {home_stats['avg_home_cards']:.1f} del {home_team} vs {home_stats['avg_away_cards']:.1f} del {away_team}
"""
    
    # 3. ANÁLISIS CUANDO JUEGA DE VISITANTE CON RESUMEN DE RESULTADOS
    away_venue_analysis = ""
    if h2h_away:
        away_stats = stats.get("away_venue", {})
        
        # 🎯 CALCULAR RESULTADOS (G-E-P, BTTS, Over 2.5)
        # Nota: En h2h_away, el equipo que hoy es local (home_team) fue visitante
        # Por lo tanto: team_goals = away_goals histórico, opponent_goals = home_goals histórico
        wins = sum(1 for m in h2h_away if m['team_goals'] > m['opponent_goals'])
        draws = sum(1 for m in h2h_away if m['team_goals'] == m['opponent_goals'])
        losses = sum(1 for m in h2h_away if m['team_goals'] < m['opponent_goals'])
        btts_count = sum(1 for m in h2h_away if m.get('btts', False))
        over25_count = sum(1 for m in h2h_away if m.get('over25', False))
        total_away_matches = len(h2h_away)
        
        # Construir narrativa con resumen de resultados
        away_venue_analysis = f"""Cuando {home_team} ha jugado de visitante contra {away_team} (últimos {total_away_matches} partidos):
{home_team}: G{wins}-E{draws}-P{losses} | BTTS: {btts_count}/{total_away_matches} | Over 2.5: {over25_count}/{total_away_matches}

- Promedio de goles: {away_team} {away_stats['avg_opponent_goals']:.1f} - {home_team} {away_stats['avg_team_goals']:.1f}
- Promedio de tiros: {away_stats['avg_opponent_shots']:.1f} del {away_team} vs {away_stats['avg_team_shots']:.1f} del {home_team}
- Promedio de tiros al arco: {away_stats['avg_opponent_shots_on_target']:.1f} del {away_team} vs {away_stats['avg_team_shots_on_target']:.1f} del {home_team}
- Promedio de corners: {away_stats['avg_opponent_corners']:.1f} del {away_team} vs {away_stats['avg_team_corners']:.1f} del {home_team}
- Promedio de faltas: {away_stats['avg_opponent_fouls']:.1f} del {away_team} vs {away_stats['avg_team_fouls']:.1f} del {home_team}
- Promedio de tarjetas: {away_stats['avg_opponent_cards']:.1f} del {away_team} vs {away_stats['avg_team_cards']:.1f} del {home_team}
"""
    
    # 4. COMPARACIÓN CON PREDICCIÓN ACTUAL
    pred_goals_total = (match_info["pred_home_goals"] or 0) + (match_info["pred_away_goals"] or 0)
    prediction_analysis = f"""Predicción para este partido:
- Goles esperados: {match_info['pred_home_goals']:.1f} - {match_info['pred_away_goals']:.1f} (Total: {pred_goals_total:.1f})
- Histórico: {stats['avg_total_goals']:.1f} goles promedio

"""
    
    if abs(pred_goals_total - stats['avg_total_goals']) < 0.5:
        prediction_analysis += "La predicción se alinea con el histórico reciente."
    elif pred_goals_total > stats['avg_total_goals'] + 0.5:
        prediction_analysis += f"Se espera un partido con más goles que el promedio histórico (+{pred_goals_total - stats['avg_total_goals']:.1f} goles)."
    else:
        prediction_analysis += f"Se espera un partido con menos goles que el promedio histórico ({pred_goals_total - stats['avg_total_goals']:.1f} goles)."
    
    # 5. CONCLUSIÓN
    conclusion = f"""Tendencia: Los enfrentamientos directos muestran """
    if stats['avg_total_goals'] >= 3:
        conclusion += "partidos con muchos goles"
    elif stats['avg_total_goals'] >= 2:
        conclusion += "partidos equilibrados"
    else:
        conclusion += "partidos cerrados y defensivos"
    
    conclusion += f", con un promedio de {stats['avg_total_corners']:.0f} corners y {stats['avg_total_cards']:.0f} tarjetas por partido."
    
    return {
        "summary": summary,
        "home_venue_analysis": home_venue_analysis,
        "away_venue_analysis": away_venue_analysis,
        "prediction_analysis": prediction_analysis,
        "conclusion": conclusion,
        "full_narrative": f"{summary}\n\n{home_venue_analysis}\n{away_venue_analysis}\n{prediction_analysis}\n\n{conclusion}"
    }
# ============================================================================
# 1. ENDPOINT: Guardar Best Bets (POST /api/best-bets/save)
# ============================================================================

@router.post("/api/best-bets/save")
def save_best_bets(
    season_id: int = Query(..., description="ID de la temporada"),
    bets: List[Dict[str, Any]] = None
):
    """
    Guarda las mejores apuestas en best_bets_history.
    Se llama automáticamente después de generar el análisis.
    
    Body example:
    [
        {
            "match_id": 5110,
            "date": "2025-11-09",
            "home_team": "West Ham",
            "away_team": "Burnley",
            "model": "weinston",
            "bet_type": "OVER_25",
            "prediction": "OVER",
            "confidence": 0.95,
            "historical_accuracy": 74.8,
            "combined_score": 71.0,
            "rank": 1,
            "odds": 1.85
        },
        ...
    ]
    """
    
    with engine.begin() as conn:
        inserted_count = 0
        updated_count = 0
        
        for bet in bets:
            # Extraer odds del sistema (si están disponibles)
            odds = bet.get('odds')
            
            # Si no hay odds en el input, intentar obtener de BD
            if odds is None:
                odds_query = text("""
                    SELECT 
                        CASE 
                            WHEN :bet_type = '1X2' AND :prediction = '1' THEN pp.min_odds_1
                            WHEN :bet_type = '1X2' AND :prediction = 'X' THEN pp.min_odds_x
                            WHEN :bet_type = '1X2' AND :prediction = '2' THEN pp.min_odds_2
                            WHEN :bet_type = 'OVER_25' AND :prediction = 'OVER' THEN pp.min_odds_over25
                            WHEN :bet_type = 'OVER_25' AND :prediction = 'UNDER' THEN pp.min_odds_under25
                            WHEN :bet_type = 'BTTS' AND :prediction = 'YES' THEN pp.min_odds_btts_yes
                            WHEN :bet_type = 'BTTS' AND :prediction = 'NO' THEN pp.min_odds_btts_no
                            ELSE NULL
                        END as odds
                    FROM poisson_predictions pp
                    WHERE pp.match_id = :match_id
                """)
                
                odds_result = conn.execute(odds_query, {
                    "match_id": bet['match_id'],
                    "bet_type": bet['bet_type'],
                    "prediction": bet['prediction']
                }).scalar()
                
                odds = float(odds_result) if odds_result else None
            
            # Insertar o actualizar
            upsert_query = text("""
                INSERT INTO best_bets_history (
                    match_id, season_id, date, home_team, away_team,
                    model, bet_type, prediction,
                    confidence, historical_accuracy, combined_score, rank, odds,
                    created_at
                ) VALUES (
                    :match_id, :season_id, :date, :home_team, :away_team,
                    :model, :bet_type, :prediction,
                    :confidence, :historical_accuracy, :combined_score, :rank, :odds,
                    NOW()
                )
                ON CONFLICT (match_id, model, bet_type) 
                DO UPDATE SET
                    prediction = EXCLUDED.prediction,
                    confidence = EXCLUDED.confidence,
                    historical_accuracy = EXCLUDED.historical_accuracy,
                    combined_score = EXCLUDED.combined_score,
                    rank = EXCLUDED.rank,
                    odds = EXCLUDED.odds,
                    created_at = NOW()
                RETURNING (xmax = 0) AS inserted
            """)
            
            result = conn.execute(upsert_query, {
                "match_id": bet['match_id'],
                "season_id": season_id,
                "date": bet['date'],
                "home_team": bet['home_team'],
                "away_team": bet['away_team'],
                "model": bet['model'].lower(),
                "bet_type": bet['bet_type'],
                "prediction": bet['prediction'],
                "confidence": float(bet['confidence']),
                "historical_accuracy": float(bet['historical_accuracy']),
                "combined_score": float(bet['combined_score']),
                "rank": int(bet['rank']),
                "odds": odds
            }).fetchone()
            
            if result[0]:  # xmax = 0 means it was an insert
                inserted_count += 1
            else:
                updated_count += 1
        
        return {
            "success": True,
            "inserted": inserted_count,
            "updated": updated_count,
            "total": len(bets)
        }

# ============================================================================
# 2. ENDPOINT: Validar Best Bets (POST /api/best-bets/validate)
# ============================================================================

@router.post("/api/best-bets/validate")
def validate_best_bets(season_id: int = Query(..., description="ID de la temporada")):
    """
    Valida todas las best bets pendientes que ya tienen resultado.
    Compara predicción vs resultado real y actualiza hit/actual_result.
    """
    
    with engine.begin() as conn:
        # Llamar a la función de validación
        result = conn.execute(
            text("SELECT * FROM validate_best_bets(:season_id)"),
            {"season_id": season_id}
        ).fetchone()
        
        validated_count = result[0]
        hits = result[1]
        misses = result[2]
        
        accuracy = (hits / validated_count * 100) if validated_count > 0 else 0
        
        return {
            "success": True,
            "validated": validated_count,
            "hits": hits,
            "misses": misses,
            "accuracy": round(accuracy, 2)
        }

# ============================================================================
# 3. ENDPOINT: Estadísticas de Best Bets (GET /api/best-bets/stats)
# ============================================================================

@router.get("/api/best-bets/stats")
def get_best_bets_stats(
    season_id: int = Query(..., description="ID de la temporada"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Retorna estadísticas agregadas de las best bets.
    """
    
    with engine.begin() as conn:
        # Query base
        where_clauses = ["season_id = :season_id", "validated_at IS NOT NULL"]
        params = {"season_id": season_id}
        
        if date_from:
            where_clauses.append("date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("date <= :date_to")
            params["date_to"] = date_to
        
        where_sql = " AND ".join(where_clauses)
        
        # 1. Estadísticas generales
        general_stats_query = text(f"""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
                ROUND(AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct,
                ROUND(AVG(confidence) * 100, 2) as avg_confidence,
                ROUND(AVG(combined_score), 2) as avg_score,
                SUM(profit_loss) as total_profit_loss,
                ROUND(SUM(profit_loss) / (COUNT(*) * 10.0) * 100, 2) as roi_pct
            FROM best_bets_with_results
            WHERE {where_sql}
        """)
        
        general = conn.execute(general_stats_query, params).mappings().one()
        
        # 2. Por tipo de apuesta
        by_type_query = text(f"""
            SELECT 
                bet_type,
                COUNT(*) as total,
                SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
                ROUND(AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct,
                ROUND(AVG(confidence) * 100, 2) as avg_confidence,
                SUM(profit_loss) as profit_loss,
                ROUND(SUM(profit_loss) / (COUNT(*) * 10.0) * 100, 2) as roi_pct
            FROM best_bets_with_results
            WHERE {where_sql}
            GROUP BY bet_type
            ORDER BY accuracy_pct DESC
        """)
        
        by_type = conn.execute(by_type_query, params).mappings().all()
        
        # 3. Por modelo
        by_model_query = text(f"""
            SELECT 
                model,
                COUNT(*) as total,
                SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
                ROUND(AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct,
                ROUND(AVG(confidence) * 100, 2) as avg_confidence,
                SUM(profit_loss) as profit_loss,
                ROUND(SUM(profit_loss) / (COUNT(*) * 10.0) * 100, 2) as roi_pct
            FROM best_bets_with_results
            WHERE {where_sql}
            GROUP BY model
            ORDER BY accuracy_pct DESC
        """)
        
        by_model = conn.execute(by_model_query, params).mappings().all()
        
        # 4. Por ranking
        by_rank_query = text(f"""
            SELECT 
                rank,
                COUNT(*) as total,
                SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
                ROUND(AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct,
                ROUND(AVG(confidence) * 100, 2) as avg_confidence,
                ROUND(AVG(combined_score), 2) as avg_score,
                SUM(profit_loss) as profit_loss,
                ROUND(SUM(profit_loss) / (COUNT(*) * 10.0) * 100, 2) as roi_pct
            FROM best_bets_with_results
            WHERE {where_sql}
            GROUP BY rank
            ORDER BY rank
        """)
        
        by_rank = conn.execute(by_rank_query, params).mappings().all()
        
        # 5. Evolución temporal (por semana)
        evolution_query = text(f"""
            SELECT 
                DATE_TRUNC('week', date) as week,
                COUNT(*) as total,
                SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
                ROUND(AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_pct,
                SUM(profit_loss) as profit_loss,
                ROUND(SUM(profit_loss) / (COUNT(*) * 10.0) * 100, 2) as roi_pct
            FROM best_bets_with_results
            WHERE {where_sql}
            GROUP BY week
            ORDER BY week
        """)
        
        evolution = conn.execute(evolution_query, params).mappings().all()
        
        return {
            "general": dict(general),
            "by_type": [dict(row) for row in by_type],
            "by_model": [dict(row) for row in by_model],
            "by_rank": [dict(row) for row in by_rank],
            "evolution": [
                {
                    **dict(row),
                    "week": row["week"].strftime("%Y-%m-%d") if row["week"] else None
                } 
                for row in evolution
            ]
        }

# ============================================================================
# 4. ENDPOINT: Historial de Best Bets (GET /api/best-bets/history)
# ============================================================================

@router.get("/api/best-bets/history")
def get_best_bets_history(
    season_id: int = Query(..., description="ID de la temporada"),
    limit: int = Query(50, description="Número máximo de registros"),
    validated: Optional[bool] = Query(None, description="Filtrar por validadas (True/False/None)")
):
    """
    Retorna el historial completo de best bets con sus resultados.
    """
    
    with engine.begin() as conn:
        where_clauses = ["season_id = :season_id"]
        params = {"season_id": season_id, "limit": limit}
        
        if validated is not None:
            if validated:
                where_clauses.append("validated_at IS NOT NULL")
            else:
                where_clauses.append("validated_at IS NULL")
        
        where_sql = " AND ".join(where_clauses)
        
        query = text(f"""
            SELECT 
                *
            FROM best_bets_with_results
            WHERE {where_sql}
            ORDER BY date DESC, rank
            LIMIT :limit
        """)
        
        results = conn.execute(query, params).mappings().all()
        
        return [
            {
                **dict(row),
                "date": row["date"].strftime("%Y-%m-%d") if row["date"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "validated_at": row["validated_at"].isoformat() if row["validated_at"] else None
            }
            for row in results
        ]
# ============================================================================
# H2H SCORING SYSTEM ENDPOINTS  
# ============================================================================

@router.get("/api/matches/{match_id}/h2h-scoring")
def get_match_h2h_scoring(match_id: int):
    """
    Obtiene el análisis H2H Scoring para un partido específico.
    """
    from src.predictions.h2h_scoring_system import calculate_h2h_scoring
    
    with engine.begin() as conn:
        match_query = text("""
            SELECT home_team_id, away_team_id, season_id
            FROM matches WHERE id = :match_id
        """)
        
        match_info = conn.execute(match_query, {"match_id": match_id}).fetchone()
        if not match_info:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        
        result = calculate_h2h_scoring(
            match_id=match_id,
            home_team_id=match_info.home_team_id,
            away_team_id=match_info.away_team_id,
            season_id=match_info.season_id
        )
        
        return result

@router.get("/api/leagues/{season_id}/h2h-effectiveness")
def get_league_h2h_effectiveness(season_id: int, min_score: int = Query(8)):
    """
    Estadísticas de efectividad del sistema H2H por liga y puntuación.
    """
    from src.predictions.h2h_scoring_system import get_league_effectiveness_stats
    
    result = get_league_effectiveness_stats(season_id, min_score)
    return result    

# ============================================================================
# BETTING LINES STATISTICS ENDPOINTS
# ============================================================================

# AGREGAR ESTO AL FINAL DE TU api.py (después de todos los otros endpoints)

@app.get("/api/betting-lines/stats")
def get_betting_lines_stats(
    season_id: int = Query(2, description="ID de la temporada"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    window_type: str = Query("gameweek", description="Tipo de ventana: gameweek, weekly, monthly")
):
    """
    Endpoint para estadísticas de betting lines
    """
    
    with engine.begin() as conn:
        where_clauses = ["m.season_id = :season_id", "blp.actual_total_shots IS NOT NULL"]
        params = {"season_id": season_id}
        
        if date_from:
            where_clauses.append("m.date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("m.date <= :date_to")
            params["date_to"] = date_to
        
        where_sql = " AND ".join(where_clauses)
        
        # Estadísticas generales (como en terminal)
        stats_query = text(f"""
            SELECT 
                blp.model,
                COUNT(*) as total,
                ROUND(AVG(CASE WHEN blp.shots_hit THEN 100.0 ELSE 0.0 END), 1) as shots_accuracy,
                ROUND(AVG(CASE WHEN blp.shots_on_target_hit THEN 100.0 ELSE 0.0 END), 1) as shots_ot_accuracy,
                ROUND(AVG(CASE WHEN blp.corners_hit THEN 100.0 ELSE 0.0 END), 1) as corners_accuracy,
                ROUND(AVG(CASE WHEN blp.cards_hit THEN 100.0 ELSE 0.0 END), 1) as cards_accuracy,
                ROUND(AVG(CASE WHEN blp.fouls_hit THEN 100.0 ELSE 0.0 END), 1) as fouls_accuracy,
                ROUND(AVG(
                    (CASE WHEN blp.shots_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.shots_on_target_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.corners_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.cards_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.fouls_hit THEN 1.0 ELSE 0.0 END) / 5.0 * 100
                ), 1) as overall_accuracy
            FROM betting_lines_predictions blp
            JOIN matches m ON m.id = blp.match_id
            WHERE {where_sql}
            GROUP BY blp.model
        """)
        
        stats = conn.execute(stats_query, params).mappings().all()
        
        return {
            "general_stats": [dict(row) for row in stats],
            "evolution": [],  # Vacío por ahora, solo necesitas las stats generales
            "window_type": window_type
        }

# AGREGAR ESTE ENDPOINT DE DEBUG A TU api.py

@router.get("/api/best-bets/debug-data")
def debug_best_bets_data(season_id: int = Query(2)):
    """
    Debug: Ver exactamente qué partidos y predicciones se están consultando
    """
    
    with engine.begin() as conn:
        # 1. Ver partidos disponibles para análisis (sin resultado)
        upcoming_matches_query = text("""
            SELECT
                m.id as match_id,
                m.date,
                th.name as home_team,
                ta.name as away_team,
                m.home_goals,
                m.away_goals,
                
                -- Verificar si hay predicciones
                CASE WHEN pp.match_id IS NOT NULL THEN 'SÍ' ELSE 'NO' END as tiene_poisson,
                CASE WHEN wp.match_id IS NOT NULL THEN 'SÍ' ELSE 'NO' END as tiene_weinston,
                
                -- Poisson predictions
                pp.prob_home_win as poisson_prob_home,
                pp.prob_draw as poisson_prob_draw,
                pp.prob_away_win as poisson_prob_away,
                pp.over_2 as poisson_over_25,
                pp.both_score as poisson_btts,
                
                -- Weinston predictions  
                wp.result_1x2 as weinston_result_int,
                wp.local_goals as weinston_home_goals,
                wp.away_goals as weinston_away_goals
                
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NULL  -- Solo próximos partidos
              AND m.date >= CURRENT_DATE - INTERVAL '2 days'  -- Desde hace 2 días
              AND m.date <= CURRENT_DATE + INTERVAL '7 days'  -- Hasta en 7 días
            ORDER BY m.date ASC
        """)
        
        upcoming_matches = conn.execute(upcoming_matches_query, {"season_id": season_id}).mappings().all()
        
        # 2. Ver accuracy histórica actual
        historical_accuracy_query = text("""
            SELECT 
                model,
                COUNT(*) as total_predictions,
                ROUND(AVG(CASE WHEN hit_1x2 THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_1x2,
                ROUND(AVG(CASE WHEN hit_over25 THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_over25,
                ROUND(AVG(CASE WHEN hit_btts THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_btts
            FROM prediction_outcomes po
            JOIN matches m ON m.id = po.match_id
            WHERE m.season_id = :season_id
              AND m.home_goals IS NOT NULL
            GROUP BY model
        """)
        
        accuracy_data = conn.execute(historical_accuracy_query, {"season_id": season_id}).mappings().all()
        
        # 3. Ver datos en best_bets_history
        saved_bets_query = text("""
            SELECT *
            FROM best_bets_history
            WHERE season_id = :season_id
            ORDER BY created_at DESC, rank ASC
            LIMIT 10
        """)
        
        saved_bets = conn.execute(saved_bets_query, {"season_id": season_id}).mappings().all()
        
        return {
            "debug_timestamp": datetime.now().isoformat(),
            "upcoming_matches": [dict(r) for r in upcoming_matches],
            "historical_accuracy": [dict(r) for r in accuracy_data],
            "saved_best_bets": [dict(r) for r in saved_bets],
            "total_upcoming": len(upcoming_matches),
            "matches_with_poisson": len([r for r in upcoming_matches if r['tiene_poisson'] == 'SÍ']),
            "matches_with_weinston": len([r for r in upcoming_matches if r['tiene_weinston'] == 'SÍ'])
        }

# TAMBIÉN AGREGAR ENDPOINT PARA VER PARTIDOS ESPECÍFICOS
@router.get("/api/matches/by-teams")
def get_matches_by_teams(
    home_team: str = Query(..., description="Nombre del equipo local"),
    away_team: str = Query(..., description="Nombre del equipo visitante"),
    season_id: int = Query(2)
):
    """
    Buscar partidos específicos por equipos
    """
    
    with engine.begin() as conn:
        query = text("""
            SELECT 
                m.id,
                m.date,
                th.name as home_team,
                ta.name as away_team,
                m.home_goals,
                m.away_goals,
                CASE WHEN pp.match_id IS NOT NULL THEN 'SÍ' ELSE 'NO' END as tiene_poisson,
                CASE WHEN wp.match_id IS NOT NULL THEN 'SÍ' ELSE 'NO' END as tiene_weinston
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND (
                (LOWER(th.name) LIKE LOWER(:home_pattern) AND LOWER(ta.name) LIKE LOWER(:away_pattern))
                OR (LOWER(th.name) LIKE LOWER(:away_pattern) AND LOWER(ta.name) LIKE LOWER(:home_pattern))
              )
            ORDER BY m.date DESC
        """)
        
        results = conn.execute(query, {
            "season_id": season_id,
            "home_pattern": f"%{home_team}%",
            "away_pattern": f"%{away_team}%"
        }).mappings().all()
        
        return [dict(r) for r in results]

# ===== REGISTRAR EL ROUTER =====
app.include_router(router)