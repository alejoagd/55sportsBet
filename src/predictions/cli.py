# src/predictions/cli.py
from __future__ import annotations
import typer
from typing import Optional, List
from sqlalchemy import create_engine, text
from src.config import settings
from sqlalchemy import text
from typing import Optional, List
import click
from src.db import engine

# Poisson
try:
    from .upcoming_poisson import predict_and_upsert_poisson
except ImportError:
    from src.predictions.upcoming_poisson import predict_and_upsert_poisson

# Weinston
try:
    from .upcoming_weinston import predict_and_upsert_weinston
except ImportError:
    from src.predictions.upcoming_weinston import predict_and_upsert_weinston


app = typer.Typer(help="Predicciones pre-partido (Escenario 2)")

@app.command("upcoming")

def upcoming(
    season_id: int = typer.Option(..., help="Season a usar"),
    date_from: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    date_to: Optional[str] = typer.Option(None, "--to", help="YYYY-MM-DD"),
    models: str = typer.Option("poisson,weinston", help="poisson,weinston"),
    match_ids: Optional[List[int]] = typer.Option(None, help="IDs específicos (opcional)"),
):
    """
    Genera predicciones para partidos FUTUROS (sin resultados).
    Usa strengths de equipos (histórico) -> Poisson -> (opcional) Weinston.
    """
    engine = create_engine(settings.sqlalchemy_url)

    try:
        with engine.begin() as conn:
            # Obtener los matches objetivo
            ids: List[int]
            if match_ids:
                ids = match_ids
            else:
                q = text("""
                    SELECT id FROM matches
                    WHERE season_id = :sid
                      AND (:dfrom IS NULL OR date >= :dfrom)
                      AND (:dto IS NULL OR date <= :dto)
                    ORDER BY date
                """)
                ids = [r[0] for r in conn.execute(q, {"sid": season_id, "dfrom": date_from, "dto": date_to})]

            typer.echo(f"Partidos a predecir: {len(ids)} (season_id={season_id})")
            if not ids:
                typer.echo("No hay partidos que coincidan con los filtros dados.")
                return

            model_set = {m.strip().lower() for m in models.split(",") if m.strip()}

            if "poisson" in model_set:
                from .upcoming_poisson import predict_and_upsert_poisson
                predict_and_upsert_poisson(conn, season_id, ids)
                typer.echo("✔ Poisson actualizado.")

            if "weinston" in model_set:
                from .upcoming_weinston import predict_and_upsert_weinston
                predict_and_upsert_weinston(conn, season_id, ids)
                typer.echo("✔ Weinston actualizado.")

        typer.echo("✅ Predicciones generadas/actualizadas.")
    except Exception as e:
        # Log simple para ver cualquier problema
        typer.echo(f"❌ Error en upcoming: {e}")
        raise

@app.command("score")
def score(
    season_id: int = typer.Option(..., help="Season a evaluar"),
    date_from: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    date_to: Optional[str]   = typer.Option(None, "--to",   help="YYYY-MM-DD"),
    match_ids: Optional[List[int]] = typer.Option(None, help="IDs específicos (opcional)"),
    metric: str = typer.Option("rmse", help="rmse | mae"),
):
    """
    Actualiza wp.error comparando predicción vs. goles reales del match.
    """
    from src.db import engine

    if metric not in {"rmse", "mae"}:
        raise typer.BadParameter("metric debe ser rmse o mae")

    base = """
    UPDATE weinston_predictions AS wp
    SET error = {expr}
    FROM matches m
    WHERE m.id = wp.match_id
      AND m.home_goals IS NOT NULL
      AND m.away_goals IS NOT NULL
      AND m.season_id = :season_id
    """
    expr_rmse = "sqrt(((wp.local_goals - m.home_goals)^2 + (wp.away_goals - m.away_goals)^2)/2.0)"
    expr_mae  = "((abs(wp.local_goals - m.home_goals) + abs(wp.away_goals - m.away_goals))/2.0)"

    sql = base.format(expr=expr_rmse if metric == "rmse" else expr_mae)
    params = {"season_id": season_id}

    if date_from:
        sql += " AND m.date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += " AND m.date <= :date_to"
        params["date_to"] = date_to
    if match_ids:
        sql += " AND m.id = ANY(:ids)"
        params["ids"] = match_ids

    with engine.begin() as conn:
        conn.execute(text(sql), params)

    typer.echo("✓ weinston.error actualizado.")

@app.command("evaluate")
def evaluate_cmd(
    season_id: int = typer.Option(..., help="Season a evaluar"),
    date_from: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    date_to: Optional[str]   = typer.Option(None, "--to",   help="YYYY-MM-DD"),
    match_ids: Optional[List[int]] = typer.Option(None, help="IDs específicos"),
    over_thresh: float = typer.Option(0.5, help="Umbral Poisson OVER 2.5"),
    btts_thresh: float = typer.Option(0.5, help="Umbral Poisson BTTS YES"),
):
    from .evaluate import evaluate as eval_fn
    counts = eval_fn(
        season_id=season_id,
        date_from=date_from,
        date_to=date_to,
        only_matches=match_ids,
        pick_over_thresh=over_thresh,
        pick_btts_thresh=btts_thresh,
    )
    typer.echo(f"✓ Evaluados: Poisson={counts['poisson']}, Weinston={counts['weinston']}")


# --- Callback raíz para aceptar opciones sin subcomando ---


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    season_id: Optional[int] = typer.Option(None, "--season-id"),
    date_from: Optional[str] = typer.Option(None, "--date-from", "--from"),
    date_to: Optional[str] = typer.Option(None, "--date-to", "--to"),
    match_ids: Optional[List[int]] = typer.Option(None, "--match-ids", help="IDs específicos (opcional)"),
    over_thresh: float = typer.Option(0.5, "--over-thresh", help="Umbral Poisson OVER 2.5"),
    btts_thresh: float = typer.Option(0.5, "--btts-thresh", help="Umbral Poisson BTTS YES"),
):
    """
    Si no se invoca un subcomando, se comporta como 'evaluate'.
    """
    if ctx.invoked_subcommand is not None:
        return  # se usó upcoming/score/evaluate normalmente

    if season_id is None:
        typer.echo("Uso: python -m src.predictions.cli evaluate --season-id <id> [--from YYYY-MM-DD] [--to YYYY-MM-DD]")
        raise typer.Exit(code=2)

    from .evaluate import evaluate as eval_fn
    counts = eval_fn(
        season_id=season_id,
        date_from=date_from,
        date_to=date_to,
        only_matches=match_ids,
        pick_over_thresh=over_thresh,
        pick_btts_thresh=btts_thresh,
    )
    typer.echo(f"✓ Evaluados: Poisson={counts['poisson']}, Weinston={counts['weinston']}")




@app.command("fit")
def fit_weinston_cmd(
    season_id: int = typer.Option(..., help="Season a entrenar"),
):
    """
    Entrena el modelo Weinston para una temporada.
    Calcula ratings de equipos (atk/def home/away) y parámetros de liga (mu_home, mu_away, home_adv).
    Guarda todo en weinston_ratings y weinston_params.
    """
    from src.db import SessionLocal
    from src.weinston.fit import fit_weinston, save_ratings, save_league_params
    
    typer.echo(f"🔄 Entrenando modelo Weinston para season_id={season_id}...")
    
    try:
        with SessionLocal() as s:
            result = fit_weinston(s, season_id)
            
            # Guardar ratings
            save_ratings(
                season_id=season_id,
                team_ids=result.team_ids,
                atk_home=result.atk_home,
                def_home=result.def_home,
                atk_away=result.atk_away,
                def_away=result.def_away
            )
            
            # Guardar parámetros de liga
            save_league_params(
                season_id=season_id,
                mu_home=result.mu_home,
                mu_away=result.mu_away,
                home_adv=result.home_adv,
                loss=result.loss
            )
            
            typer.echo(f"✅ Modelo entrenado exitosamente!")
            typer.echo(f"   📊 Equipos: {len(result.team_ids)}")
            typer.echo(f"   📈 μ_home: {result.mu_home:.3f}")
            typer.echo(f"   📉 μ_away: {result.mu_away:.3f}")
            typer.echo(f"   🏠 Home Advantage: {result.home_adv:.3f}")
            typer.echo(f"   🎯 Loss: {result.loss:.2f}")
            
    except Exception as e:
        typer.echo(f"❌ Error entrenando Weinston: {e}")
        raise

# ============================================================================
# COMANDOS CLI PARA BETTING LINES
# ============================================================================

@app.command("betting-lines-generate")
def betting_lines_generate(
    season_id: int = typer.Option(..., help="ID de la temporada"),
    date_from: str = typer.Option(..., "--from", help="Fecha desde (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", help="Fecha hasta (YYYY-MM-DD)"),
):
    """
    Genera predicciones de líneas de apuesta (Over/Under) para partidos sin resultado
    
    Ejemplo:
        python -m src.predictions.cli betting-lines-generate --season-id 2 --from 2024-12-01 --to 2024-12-31
    """
    from datetime import datetime
    
    # Configuración de líneas (pueden ajustarse basándose en análisis histórico)
    BETTING_LINES = {
        'shots': 24.5,
        'shots_on_target': 8.5,
        'corners': 10.5,
        'cards': 4.5,
        'fouls': 22.5
    }
    
    typer.echo(f"\n{'='*70}")
    typer.echo(f"  GENERANDO BETTING LINES")
    typer.echo(f"{'='*70}\n")
    typer.echo(f"Season: {season_id}")
    typer.echo(f"Rango: {date_from} a {date_to}")
    typer.echo(f"Líneas: Tiros={BETTING_LINES['shots']}, Corners={BETTING_LINES['corners']}, Tarjetas={BETTING_LINES['cards']}\n")
    
    with engine.begin() as conn:
        # Obtener partidos sin resultado con predicciones Weinston
        matches_query = text("""
            SELECT 
                m.id as match_id,
                m.date,
                
                -- Predicciones Weinston (estadísticas)
                wp.shots_home,
                wp.shots_away,
                wp.shots_target_home,
                wp.shots_target_away,
                wp.corners_home,
                wp.corners_away,
                wp.cards_home,
                wp.cards_away,
                wp.fouls_home,
                wp.fouls_away
                
            FROM matches m
            LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
            WHERE m.season_id = :season_id
              AND m.date BETWEEN :date_from AND :date_to
              AND m.home_goals IS NULL
            ORDER BY m.date
        """)
        
        matches = conn.execute(matches_query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        }).mappings().all()
        
        if not matches:
            typer.echo("❌ No hay partidos sin resultado en el rango de fechas")
            return
        
        generated_count = 0
        
        for match in matches:
            if match['shots_home'] is None:
                typer.echo(f"⚠️  Match {match['match_id']}: No tiene predicciones Weinston, saltando...")
                continue
            
            # Calcular totales predichos
            predicted_shots = float(match['shots_home'] or 0) + float(match['shots_away'] or 0)
            predicted_shots_ot = float(match['shots_target_home'] or 0) + float(match['shots_target_away'] or 0)
            predicted_corners = float(match['corners_home'] or 0) + float(match['corners_away'] or 0)
            predicted_cards = float(match['cards_home'] or 0) + float(match['cards_away'] or 0)
            predicted_fouls = float(match['fouls_home'] or 0) + float(match['fouls_away'] or 0)
            
            # Calcular predicciones y confianza
            shots_line = BETTING_LINES['shots']
            shots_prediction = 'over' if predicted_shots > shots_line else 'under'
            shots_confidence = min(abs(predicted_shots - shots_line) / 10.0, 1.0)
            
            shots_ot_line = BETTING_LINES['shots_on_target']
            shots_ot_prediction = 'over' if predicted_shots_ot > shots_ot_line else 'under'
            shots_ot_confidence = min(abs(predicted_shots_ot - shots_ot_line) / 5.0, 1.0)
            
            corners_line = BETTING_LINES['corners']
            corners_prediction = 'over' if predicted_corners > corners_line else 'under'
            corners_confidence = min(abs(predicted_corners - corners_line) / 5.0, 1.0)
            
            cards_line = BETTING_LINES['cards']
            cards_prediction = 'over' if predicted_cards > cards_line else 'under'
            cards_confidence = min(abs(predicted_cards - cards_line) / 3.0, 1.0)
            
            fouls_line = BETTING_LINES['fouls']
            fouls_prediction = 'over' if predicted_fouls > fouls_line else 'under'
            fouls_confidence = min(abs(predicted_fouls - fouls_line) / 8.0, 1.0)
            
            # Insertar o actualizar
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
                "match_id": match['match_id'],
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
            
            generated_count += 1
        
        typer.echo(f"\n✅ Betting lines generadas: {generated_count}/{len(matches)} partidos")


@app.command("betting-lines-validate")
def betting_lines_validate(
    season_id: int = typer.Option(..., help="ID de la temporada"),
    date_from: str = typer.Option(..., "--from", help="Fecha desde (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", help="Fecha hasta (YYYY-MM-DD)"),
):
    """
    Valida las predicciones de líneas de apuesta contra los resultados reales
    
    Ejemplo:
        python -m src.predictions.cli betting-lines-validate --season-id 2 --from 2024-12-01 --to 2024-12-31
    """
    typer.echo(f"\n{'='*70}")
    typer.echo(f"  VALIDANDO BETTING LINES")
    typer.echo(f"{'='*70}\n")
    typer.echo(f"Season: {season_id}")
    typer.echo(f"Rango: {date_from} a {date_to}\n")
    
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
              AND m.date BETWEEN :date_from AND :date_to
              AND m.home_goals IS NOT NULL
              AND (blp.actual_total_shots IS NULL OR blp.updated_at < m.date + INTERVAL '1 day')
        """)
        
        result = conn.execute(update_query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        })
        
        validated_count = result.rowcount
        
        typer.echo(f"✅ Betting lines validadas: {validated_count} partidos\n")
        
        # Mostrar accuracy
        accuracy_query = text("""
            SELECT 
                blp.model,
                COUNT(*) as total,
                ROUND(AVG(CASE WHEN blp.shots_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as shots_acc,
                ROUND(AVG(CASE WHEN blp.shots_on_target_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as shots_ot_acc,
                ROUND(AVG(CASE WHEN blp.corners_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as corners_acc,
                ROUND(AVG(CASE WHEN blp.cards_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as cards_acc,
                ROUND(AVG(CASE WHEN blp.fouls_hit THEN 1.0 ELSE 0.0 END) * 100, 2) as fouls_acc,
                ROUND(AVG(
                    (CASE WHEN blp.shots_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.shots_on_target_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.corners_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.cards_hit THEN 1.0 ELSE 0.0 END +
                     CASE WHEN blp.fouls_hit THEN 1.0 ELSE 0.0 END) / 5.0
                ) * 100, 2) as overall_acc
            FROM betting_lines_predictions blp
            JOIN matches m ON m.id = blp.match_id
            WHERE m.season_id = :season_id
              AND m.date BETWEEN :date_from AND :date_to
              AND blp.actual_total_shots IS NOT NULL
            GROUP BY blp.model
        """)
        
        accuracy_results = conn.execute(accuracy_query, {
            "season_id": season_id,
            "date_from": date_from,
            "date_to": date_to
        }).mappings().all()
        
        if accuracy_results:
            typer.echo("📊 ACCURACY POR MODELO:\n")
            for row in accuracy_results:
                typer.echo(f"  {row['model'].upper()}:")
                typer.echo(f"    Total predicciones: {row['total']}")
                typer.echo(f"    Accuracy general:   {row['overall_acc']}%")
                typer.echo(f"    Tiros:     {row['shots_acc']}%")
                typer.echo(f"    Tiros OT:  {row['shots_ot_acc']}%")
                typer.echo(f"    Corners:   {row['corners_acc']}%")
                typer.echo(f"    Tarjetas:  {row['cards_acc']}%")
                typer.echo(f"    Faltas:    {row['fouls_acc']}%")
                typer.echo()


if __name__ == "__main__":
    app()
