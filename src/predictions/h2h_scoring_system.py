# src/predictions/h2h_scoring_system.py
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text, Connection
from src.db import engine
from datetime import datetime

def calculate_h2h_scoring(
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    season_id: int,
    n_recent: int = 12  # Últimos 12 enfrentamientos por defecto
) -> Dict[str, Any]:
    """
    Calcula el H2H Scoring System para un partido específico.
    
    Este sistema:
    1. Obtiene las predicciones de Weinston para el partido
    2. Busca los últimos N enfrentamientos directos
    3. Calcula cuántas veces se cumplió cada predicción históricamente
    4. Genera una puntuación (0-12) que indica la confianza histórica
    
    Returns:
        {
            "match_id": int,
            "total_h2h_matches": int,
            "predictions": {
                "goles": {"prediction": "UNDER_2_5", "hit_count": 8, "score": 8},
                "corners": {"prediction": "OVER_10_5", "hit_count": 9, "score": 9},
                ...
            },
            "h2h_matches": [...],  # Lista de partidos históricos
            "overall_confidence": float  # Confianza promedio
        }
    """
    
    with engine.begin() as conn:
        # 1. Obtener las predicciones de Weinston para este partido
        weinston_predictions = _get_weinston_predictions(conn, match_id)
        if not weinston_predictions:
            return {"error": "No hay predicciones de Weinston para este partido"}
        
        # 2. Obtener enfrentamientos directos históricos
        h2h_matches = _get_h2h_matches(conn, home_team_id, away_team_id, season_id, match_id, n_recent)
        if len(h2h_matches) < 3:  # Mínimo 3 partidos para análisis
            return {"error": f"Pocos datos H2H: solo {len(h2h_matches)} partidos"}
        
        # 3. Calcular scoring para cada estadística
        scoring_results = _calculate_scoring_by_stat(weinston_predictions, h2h_matches, len(h2h_matches))
        
        # 4. Calcular confianza general
        scores = [result["score"] for result in scoring_results.values() if result["score"] is not None]
        overall_confidence = sum(scores) / len(scores) if scores else 0

        # 5. Guardar en base de datos
        save_h2h_scoring_to_db(match_id, scoring_results, round(overall_confidence, 2))

        return {
            "match_id": match_id,
            "total_h2h_matches": len(h2h_matches),
            "predictions": scoring_results,
            "h2h_matches": h2h_matches,
            "overall_confidence": round(overall_confidence, 2)
        }

def _get_weinston_predictions(conn: Connection, match_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene las predicciones de Weinston para un partido.
    
    ✅ CORREGIDO: Lee los thresholds de league_parameters según la liga del partido
    """
    query = text("""
        SELECT 
            wp.local_goals,
            wp.away_goals,
            wp.over_2,
            wp.both_score,
            wp.shots_home,
            wp.shots_away,
            wp.shots_target_home,
            wp.shots_target_away,
            wp.fouls_home,
            wp.fouls_away,
            wp.cards_home,
            wp.cards_away,
            wp.corners_home,
            wp.corners_away,
            -- ✅ NUEVO: Obtener thresholds de league_parameters
            lp.betting_line_shots,
            lp.betting_line_shots_ot,
            lp.betting_line_fouls,
            lp.betting_line_cards,
            lp.betting_line_corners
        FROM weinston_predictions wp
        JOIN matches m ON m.id = wp.match_id
        JOIN seasons s ON s.id = m.season_id
        JOIN league_parameters lp ON lp.league_id = s.league_id
        WHERE wp.match_id = :match_id
    """)
    
    result = conn.execute(query, {"match_id": match_id}).fetchone()
    if not result:
        return None
    
    # Calcular totales predichos
    total_goals = float(result.local_goals) + float(result.away_goals)
    total_shots = float(result.shots_home) + float(result.shots_away)
    total_shots_target = float(result.shots_target_home) + float(result.shots_target_away)
    total_fouls = float(result.fouls_home) + float(result.fouls_away)
    total_cards = float(result.cards_home) + float(result.cards_away)
    total_corners = float(result.corners_home) + float(result.corners_away)
    
    # ✅ Usar thresholds de league_parameters
    line_shots = float(result.betting_line_shots)
    line_shots_ot = float(result.betting_line_shots_ot)
    line_fouls = float(result.betting_line_fouls)
    line_cards = float(result.betting_line_cards)
    line_corners = float(result.betting_line_corners)
    
    return {
        "goles": {
            "predicted_total": total_goals,
            "line": 2.5,  # Este sí es universal
            "prediction": "OVER_2_5" if total_goals >= 2.5 else "UNDER_2_5"
        },
        "tiros": {
            "predicted_total": total_shots,
            "line": line_shots,  # ✅ Dinámico por liga
            "prediction": f"OVER_{line_shots}" if total_shots >= line_shots else f"UNDER_{line_shots}"
        },
        "tiros_al_arco": {
            "predicted_total": total_shots_target,
            "line": line_shots_ot,  # ✅ Dinámico por liga
            "prediction": f"OVER_{line_shots_ot}" if total_shots_target >= line_shots_ot else f"UNDER_{line_shots_ot}"
        },
        "faltas": {
            "predicted_total": total_fouls,
            "line": line_fouls,  # ✅ Dinámico por liga
            "prediction": f"OVER_{line_fouls}" if total_fouls >= line_fouls else f"UNDER_{line_fouls}"
        },
        "tarjetas": {
            "predicted_total": total_cards,
            "line": line_cards,  # ✅ Dinámico por liga
            "prediction": f"OVER_{line_cards}" if total_cards >= line_cards else f"UNDER_{line_cards}"
        },
        "corners": {
            "predicted_total": total_corners,
            "line": line_corners,  # ✅ Dinámico por liga
            "prediction": f"OVER_{line_corners}" if total_corners >= line_corners else f"UNDER_{line_corners}"
        },
        "btts": {
            "prediction": result.both_score  # "YES" o "NO"
        }
    }

def _get_h2h_matches(
    conn: Connection, 
    home_team_id: int, 
    away_team_id: int, 
    current_season_id: int,
    match_id: int,
    n_recent: int
) -> List[Dict[str, Any]]:
    """
    Obtiene los últimos N enfrentamientos directos entre estos equipos.
    Incluye tanto partidos donde home_team jugó de local vs away_team,
    como partidos donde away_team jugó de local vs home_team.
    """
    query = text("""
        SELECT 
            m.id,
            m.date,
            m.season_id,
            CONCAT(s.year_start, '/', s.year_end) as season,
            m.home_team_id,
            m.away_team_id,
            th.name as home_team,
            ta.name as away_team,
            m.home_goals,
            m.away_goals,
            
            -- Estadísticas del partido
            ms.home_shots,
            ms.away_shots,
            ms.home_shots_on_target,
            ms.away_shots_on_target,
            ms.home_fouls,
            ms.away_fouls,
            ms.home_corners,
            ms.away_corners,
            ms.home_yellow_cards,
            ms.away_yellow_cards,
            ms.home_red_cards,
            ms.away_red_cards,
            
            -- Totales calculados
            (ms.home_shots + ms.away_shots) as total_shots,
            (ms.home_shots_on_target + ms.away_shots_on_target) as total_shots_target,
            (ms.home_fouls + ms.away_fouls) as total_fouls,
            (COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.away_yellow_cards, 0) + 
             COALESCE(ms.home_red_cards, 0) + COALESCE(ms.away_red_cards, 0)) as total_cards,
            (ms.home_corners + ms.away_corners) as total_corners,
            
            -- Análisis de resultados
            (m.home_goals + m.away_goals) as total_goals,
            CASE WHEN (m.home_goals + m.away_goals) >= 3 THEN TRUE ELSE FALSE END as over_25,
            CASE WHEN m.home_goals > 0 AND m.away_goals > 0 THEN TRUE ELSE FALSE END as btts
            
        FROM matches m
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        JOIN seasons s ON s.id = m.season_id
        LEFT JOIN match_stats ms ON ms.match_id = m.id
        
        WHERE m.season_id <= :current_season_id  -- Incluir temporada actual y anteriores
          AND m.home_goals IS NOT NULL  -- Solo partidos finalizados
          AND m.away_goals IS NOT NULL
          AND m.id != :match_id  -- Excluir el partido actual que estamos analizando
          AND (
              (m.home_team_id = :home_team_id AND m.away_team_id = :away_team_id) OR
              (m.home_team_id = :away_team_id AND m.away_team_id = :home_team_id)
          )
        
        ORDER BY m.date DESC
        LIMIT :n_recent
    """)
    
    results = conn.execute(query, {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "current_season_id": current_season_id,
        "match_id": match_id,
        "n_recent": n_recent
    }).mappings().all()
    
    return [dict(row) for row in results]

def _calculate_scoring_by_stat(
    predictions: Dict[str, Any], 
    h2h_matches: List[Dict[str, Any]], 
    total_matches: int
) -> Dict[str, Dict[str, Any]]:
    """
    Calcula el scoring para cada estadística comparando la predicción 
    con el historial de enfrentamientos directos.
    """
    results = {}
    
    # 1. GOLES
    if "goles" in predictions:
        pred = predictions["goles"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_goals"] is not None:
                valid_matches += 1
                actual_over_25 = match["total_goals"] >= 3
                predicted_over_25 = pred["prediction"] == "OVER_2_5"
                
                if actual_over_25 == predicted_over_25:
                    hit_count += 1
        
        results["goles"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 2. TIROS
    if "tiros" in predictions:
        pred = predictions["tiros"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_shots"] is not None:
                valid_matches += 1
                actual_over = match["total_shots"] >= pred["line"]
                predicted_over = pred["prediction"].startswith("OVER")
                
                if actual_over == predicted_over:
                    hit_count += 1
        
        results["tiros"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 3. TIROS AL ARCO
    if "tiros_al_arco" in predictions:
        pred = predictions["tiros_al_arco"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_shots_target"] is not None:
                valid_matches += 1
                actual_over = match["total_shots_target"] >= pred["line"]
                predicted_over = pred["prediction"].startswith("OVER")
                
                if actual_over == predicted_over:
                    hit_count += 1
        
        results["tiros_al_arco"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 4. FALTAS
    if "faltas" in predictions:
        pred = predictions["faltas"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_fouls"] is not None:
                valid_matches += 1
                actual_over = match["total_fouls"] >= pred["line"]
                predicted_over = pred["prediction"].startswith("OVER")
                
                if actual_over == predicted_over:
                    hit_count += 1
        
        results["faltas"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 5. TARJETAS
    if "tarjetas" in predictions:
        pred = predictions["tarjetas"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_cards"] is not None:
                valid_matches += 1
                actual_over = match["total_cards"] >= pred["line"]
                predicted_over = pred["prediction"].startswith("OVER")
                
                if actual_over == predicted_over:
                    hit_count += 1
        
        results["tarjetas"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 6. CORNERS
    if "corners" in predictions:
        pred = predictions["corners"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["total_corners"] is not None:
                valid_matches += 1
                actual_over = match["total_corners"] >= pred["line"]
                predicted_over = pred["prediction"].startswith("OVER")
                
                if actual_over == predicted_over:
                    hit_count += 1
        
        results["corners"] = {
            "prediction": pred["prediction"],
            "predicted_total": pred["predicted_total"],
            "line": pred["line"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    # 7. BTTS
    if "btts" in predictions:
        pred = predictions["btts"]
        hit_count = 0
        valid_matches = 0
        
        for match in h2h_matches:
            if match["btts"] is not None:
                valid_matches += 1
                actual_btts = match["btts"]
                predicted_btts = pred["prediction"] == "YES"
                
                if actual_btts == predicted_btts:
                    hit_count += 1
        
        results["btts"] = {
            "prediction": pred["prediction"],
            "hit_count": hit_count,
            "valid_matches": valid_matches,
            "score": hit_count if valid_matches > 0 else None,
            "percentage": round(hit_count / valid_matches * 100, 1) if valid_matches > 0 else None
        }
    
    return results

def save_h2h_scoring_to_db(
    match_id: int,
    scoring_results: Dict[str, Any],
    overall_confidence: float
) -> bool:
    """
    Guarda los resultados del H2H scoring en la base de datos.

    Args:
        match_id: ID del partido
        scoring_results: Resultados del scoring (output de _calculate_scoring_by_stat)
        overall_confidence: Confianza promedio general

    Returns:
        True si se guardó exitosamente, False en caso contrario
    """
    try:
        with engine.begin() as conn:
            # Preparar datos para inserción
            data = {
                "match_id": match_id,
                "overall_confidence": overall_confidence
            }

            # Goles
            if "goles" in scoring_results and scoring_results["goles"]["score"] is not None:
                data["goles_score"] = scoring_results["goles"]["score"]
                data["goles_prediction"] = scoring_results["goles"]["prediction"]
                data["goles_hit"] = None  # Se actualizará después del partido

            # Tiros
            if "tiros" in scoring_results and scoring_results["tiros"]["score"] is not None:
                data["tiros_score"] = scoring_results["tiros"]["score"]
                data["tiros_prediction"] = scoring_results["tiros"]["prediction"]
                data["tiros_hit"] = None

            # Tiros al arco
            if "tiros_al_arco" in scoring_results and scoring_results["tiros_al_arco"]["score"] is not None:
                data["tiros_al_arco_score"] = scoring_results["tiros_al_arco"]["score"]
                data["tiros_al_arco_prediction"] = scoring_results["tiros_al_arco"]["prediction"]
                data["tiros_al_arco_hit"] = None

            # Corners
            if "corners" in scoring_results and scoring_results["corners"]["score"] is not None:
                data["corners_score"] = scoring_results["corners"]["score"]
                data["corners_prediction"] = scoring_results["corners"]["prediction"]
                data["corners_hit"] = None

            # Tarjetas
            if "tarjetas" in scoring_results and scoring_results["tarjetas"]["score"] is not None:
                data["tarjetas_score"] = scoring_results["tarjetas"]["score"]
                data["tarjetas_prediction"] = scoring_results["tarjetas"]["prediction"]
                data["tarjetas_hit"] = None

            # Faltas
            if "faltas" in scoring_results and scoring_results["faltas"]["score"] is not None:
                data["faltas_score"] = scoring_results["faltas"]["score"]
                data["faltas_prediction"] = scoring_results["faltas"]["prediction"]
                data["faltas_hit"] = None

            # Construir query de inserción/actualización
            columns = ", ".join(data.keys())
            placeholders = ", ".join([f":{key}" for key in data.keys()])

            # Update set clause (excluir match_id del UPDATE)
            update_cols = [key for key in data.keys() if key != "match_id"]
            update_set = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])

            query = text(f"""
                INSERT INTO h2h_scoring ({columns})
                VALUES ({placeholders})
                ON CONFLICT (match_id)
                DO UPDATE SET
                    {update_set},
                    updated_at = NOW()
            """)

            conn.execute(query, data)
            return True

    except Exception as e:
        print(f"❌ Error saving H2H scoring to DB for match {match_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_league_effectiveness_stats(season_id: int, min_score: int = 8) -> Dict[str, Any]:
    """
    Calcula estadísticas de efectividad por liga y por puntuación,
    similar a lo que muestras en la imagen 1.

    Args:
        season_id: ID de la temporada
        min_score: Puntuación mínima para considerar "alta confianza" (default: 8)

    Returns:
        {
            "by_stat": {
                "corners": [
                    {"score": 11, "total": 16, "hits": 13, "accuracy": 81.25},
                    {"score": 10, "total": 21, "hits": 17, "accuracy": 80.95},
                    ...
                ]
            },
            "summary": {
                "total_analyzed": 150,
                "high_confidence_bets": 45,  # score >= min_score
                "high_confidence_accuracy": 78.5
            }
        }
    """
    # Esta función se implementaría para analizar todos los partidos ya jugados
    # y generar las estadísticas como las de tu imagen 1
    # Por ahora devuelvo un placeholder

    return {
        "by_stat": {
            "corners": [
                {"score": 11, "total": 16, "hits": 13, "accuracy": 81.25},
                {"score": 10, "total": 21, "hits": 17, "accuracy": 80.95},
                {"score": 9, "total": 24, "hits": 18, "accuracy": 75.0}
            ]
        },
        "summary": {
            "total_analyzed": 150,
            "high_confidence_bets": 45,
            "high_confidence_accuracy": 78.5
        }
    }


STAT_LABELS = {
    "goles": "Goles (Over/Under 2.5)",
    "tiros": "Tiros",
    "tiros_al_arco": "Tiros a puerta",
    "faltas": "Faltas",
    "tarjetas": "Tarjetas",
    "corners": "Corners",
}


def _current_weekend_window() -> Tuple[Any, Any]:
    """
    Ventana viernes-lunes que contiene "este fin de semana": si hoy ya cae
    dentro de un fin de semana (vie/sáb/dom/lun) usa ESE, si no, el próximo.
    Cubre ligas que juegan desde el viernes hasta el lunes por la noche.
    """
    from datetime import date, timedelta
    today = date.today()
    weekday = today.weekday()  # Mon=0 ... Sun=6
    if weekday in (4, 5, 6, 0):  # ya estamos en un fin de semana (vie/sáb/dom/lun)
        start = today - timedelta(days=(weekday - 4) % 7)
    else:  # martes/miércoles/jueves -> el próximo viernes
        start = today + timedelta(days=(4 - weekday) % 7)
    end = start + timedelta(days=3)  # viernes .. lunes
    return start, end


def get_top_upcoming_h2h_picks(
    days_ahead: Optional[int] = None,
    min_sample: int = 10,
    min_accuracy: float = 0,
    limit: int = 4,
    weekend_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    De los partidos que se van a jugar (por defecto, solo los de "este fin de
    semana" — viernes a lunes; con weekend_only=False o days_ahead seteado,
    usa una ventana de N días desde hoy en su lugar), calcula la puntuación
    H2H en vivo (0-12) de cada estadística y la cruza contra la efectividad
    REAL que esa puntuación exacta tuvo históricamente en esa liga (tabla
    h2h_scoring, ya poblada por el backtest — ver
    /api/h2h-score/effectiveness-by-league).

    Devuelve las `limit` combinaciones (partido, estadística) con mayor
    accuracy real histórico — sin diversificar por item: si el mismo patrón
    (ej. "Faltas score=3") es el más confiable en varios partidos distintos
    del fin de semana, todos entran antes de bajar a otro item. Único
    resguardo: nunca se repite el mismo partido en dos lugares del listado.
    `min_sample` exige un mínimo de partidos históricos con esa puntuación
    exacta, y `min_accuracy` (0-100) descarta cualquier candidato por debajo
    de ese piso de confiabilidad real en vez de solo tomar el top N a
    cualquier costo.
    """
    with engine.begin() as conn:
        # 1) tabla de efectividad real (liga, stat, score) -> (accuracy, total)
        #    misma union que usa /api/h2h-score/effectiveness-by-league
        accuracy_query = text("""
            SELECT l.name as league, x.stat, x.score,
                   COUNT(*) as total,
                   ROUND(AVG(CASE WHEN x.hit THEN 100.0 ELSE 0.0 END), 1) as accuracy
            FROM (
                SELECT match_id, 'goles' as stat, goles_score as score, goles_hit as hit FROM h2h_scoring WHERE goles_score IS NOT NULL AND goles_hit IS NOT NULL
                UNION ALL
                SELECT match_id, 'tiros', tiros_score, tiros_hit FROM h2h_scoring WHERE tiros_score IS NOT NULL AND tiros_hit IS NOT NULL
                UNION ALL
                SELECT match_id, 'tiros_al_arco', tiros_al_arco_score, tiros_al_arco_hit FROM h2h_scoring WHERE tiros_al_arco_score IS NOT NULL AND tiros_al_arco_hit IS NOT NULL
                UNION ALL
                SELECT match_id, 'faltas', faltas_score, faltas_hit FROM h2h_scoring WHERE faltas_score IS NOT NULL AND faltas_hit IS NOT NULL
                UNION ALL
                SELECT match_id, 'tarjetas', tarjetas_score, tarjetas_hit FROM h2h_scoring WHERE tarjetas_score IS NOT NULL AND tarjetas_hit IS NOT NULL
                UNION ALL
                SELECT match_id, 'corners', corners_score, corners_hit FROM h2h_scoring WHERE corners_score IS NOT NULL AND corners_hit IS NOT NULL
            ) x
            JOIN matches m ON m.id = x.match_id
            JOIN seasons s ON s.id = m.season_id
            JOIN leagues l ON l.id = s.league_id
            GROUP BY l.name, x.stat, x.score
        """)
        accuracy_lookup: Dict[Tuple[str, str, int], Tuple[float, int]] = {
            (row.league, row.stat, row.score): (float(row.accuracy), row.total)
            for row in conn.execute(accuracy_query).fetchall()
        }

        # 2) partidos a analizar: "este fin de semana" (viernes-lunes) por defecto,
        #    o una ventana de N dias si se pide explicitamente
        if weekend_only and days_ahead is None:
            window_start, window_end = _current_weekend_window()
            date_filter = "m.date BETWEEN :window_start AND :window_end"
            date_params = {"window_start": window_start, "window_end": window_end}
        else:
            date_filter = "m.date BETWEEN CURRENT_DATE AND CURRENT_DATE + (:days_ahead || ' days')::interval"
            date_params = {"days_ahead": days_ahead or 10}

        candidates_query = text(f"""
            SELECT m.id as match_id, m.home_team_id, m.away_team_id, m.season_id, m.date,
                   th.name as home_team, ta.name as away_team, th.logo_url as home_logo, ta.logo_url as away_logo,
                   l.name as league
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            JOIN weinston_predictions wp ON wp.match_id = m.id
            JOIN seasons s ON s.id = m.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE m.home_goals IS NULL
              AND {date_filter}
            ORDER BY m.date
        """)
        candidates = conn.execute(candidates_query, date_params).mappings().all()

    # Se toman las N mas confiables en TOTAL (sin diversificar por item): si
    # el patron con mayor accuracy real (ej. "Faltas score=3/6") se repite en
    # varios partidos distintos del fin de semana, todos esos partidos
    # entran antes de bajar a mirar otros items — solo se evita recomendar
    # el MISMO partido dos veces (para no gastar 2 de los 4 espacios en un
    # solo partido con 2 estadisticas fuertes).
    all_candidates: List[Dict[str, Any]] = []

    for c in candidates:
        scoring = calculate_h2h_scoring(c["match_id"], c["home_team_id"], c["away_team_id"], c["season_id"])
        if "error" in scoring:
            continue

        for stat, result in scoring["predictions"].items():
            score = result.get("score")
            if score is None:
                continue
            lookup = accuracy_lookup.get((c["league"], stat, score))
            if not lookup:
                continue
            historical_accuracy, historical_sample = lookup
            if historical_sample < min_sample:
                continue
            if historical_accuracy < min_accuracy:
                continue

            candidate_pick = {
                "match_id": c["match_id"],
                "date": c["date"].isoformat() if hasattr(c["date"], "isoformat") else str(c["date"]),
                "home_team": c["home_team"],
                "away_team": c["away_team"],
                "home_team_logo": c["home_logo"],
                "away_team_logo": c["away_logo"],
                "league": c["league"],
                "stat": stat,
                "stat_label": STAT_LABELS.get(stat, stat),
                "prediction": result["prediction"],
                "line": result.get("line"),
                "score": score,
                "h2h_valid_matches": result["valid_matches"],
                "historical_accuracy": historical_accuracy,
                "historical_sample": historical_sample,
            }

            all_candidates.append(candidate_pick)

    all_candidates.sort(key=lambda p: p["historical_accuracy"], reverse=True)

    picks: List[Dict[str, Any]] = []
    used_matches: set = set()
    for candidate_pick in all_candidates:
        if candidate_pick["match_id"] in used_matches:
            continue
        picks.append(candidate_pick)
        used_matches.add(candidate_pick["match_id"])
        if len(picks) >= limit:
            break

    return picks