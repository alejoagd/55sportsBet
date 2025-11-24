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