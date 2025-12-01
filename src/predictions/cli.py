from __future__ import annotations
import typer
from typing import Optional, List
from sqlalchemy import create_engine, text
from src.config import settings
from src.db import engine
from src.db import SessionLocal
from src.weinston.fit import fit_weinston, save_ratings, save_league_params
from sqlalchemy import text

# src/predictions/cli.py
"""
CLI refactorizado con soporte multi-liga.

CAMBIOS PRINCIPALES:
1. Importa LeagueContext
2. Comando 'upcoming' muestra información de liga y pasa league_ctx
3. Comando 'evaluate' muestra información de liga
4. Logs mejorados con información contextual
"""



# Importar LeagueContext
try:
    from .league_context import LeagueContext
except ImportError:
    from src.predictions.league_context import LeagueContext

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
    
    Ahora con soporte multi-liga: cada liga usa sus propios parámetros.
    """
    engine = create_engine(settings.sqlalchemy_url)

    try:
        with engine.begin() as conn:
            # ✅ NUEVO: Cargar y mostrar contexto de liga
            league_ctx = LeagueContext.from_season(conn, season_id)
            
            typer.echo(f"\n{'='*70}")
            typer.echo(f"  GENERANDO PREDICCIONES")
            typer.echo(f"{'='*70}")
            typer.echo(f"\n🏆 Liga: {league_ctx.league_name}")
            typer.echo(f"📅 Temporada: {league_ctx.season_year}")
            typer.echo(f"📊 Promedios: {league_ctx.avg_home_goals:.2f} (H) / {league_ctx.avg_away_goals:.2f} (A)")
            typer.echo(f"🏠 HFA: {league_ctx.hfa:.2f}\n")
            
            # Obtener los matches objetivo
            ids: List[int]
            if match_ids:
                ids = match_ids
                typer.echo(f"🎯 Partidos especificados manualmente: {len(ids)}")
            else:
                q = text("""
                    SELECT id FROM matches
                    WHERE season_id = :sid
                      AND (:dfrom IS NULL OR date >= :dfrom)
                      AND (:dto IS NULL OR date <= :dto)
                    ORDER BY date
                """)
                ids = [r[0] for r in conn.execute(q, {"sid": season_id, "dfrom": date_from, "dto": date_to})]
                
                if date_from or date_to:
                    typer.echo(f"🎯 Partidos en rango de fechas: {len(ids)}")
                else:
                    typer.echo(f"🎯 Todos los partidos de la temporada: {len(ids)}")

            if not ids:
                typer.echo("\n⚠️  No hay partidos que coincidan con los filtros dados.")
                return

            model_set = {m.strip().lower() for m in models.split(",") if m.strip()}
            
            typer.echo(f"\n📋 Modelos a ejecutar: {', '.join(model_set).upper()}\n")

            # ✅ CAMBIO: Pasar league_ctx a las funciones de predicción
            if "poisson" in model_set:
                predict_and_upsert_poisson(conn, season_id, ids, league_ctx=league_ctx)
                typer.echo("\n✅ Poisson completado")

            if "weinston" in model_set:
                predict_and_upsert_weinston(conn, season_id, ids, league_ctx=league_ctx)
                typer.echo("\n✅ Weinston completado")

        typer.echo(f"\n{'='*70}")
        typer.echo("  ✅ PREDICCIONES GENERADAS EXITOSAMENTE")
        typer.echo(f"{'='*70}\n")
        
    except Exception as e:
        typer.echo(f"\n{'='*70}")
        typer.echo(f"  ❌ ERROR EN PREDICCIONES")
        typer.echo(f"{'='*70}")
        typer.echo(f"\n{str(e)}\n")
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
    if metric not in {"rmse", "mae"}:
        raise typer.BadParameter("metric debe ser rmse o mae")

    # ✅ NUEVO: Mostrar contexto de liga
    with engine.begin() as conn:
        league_ctx = LeagueContext.from_season(conn, season_id)
        typer.echo(f"\n🏆 Liga: {league_ctx.league_name} ({league_ctx.season_year})")
        typer.echo(f"📊 Calculando {metric.upper()}...\n")

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
        result = conn.execute(text(sql), params)
        typer.echo(f"✅ {metric.upper()} actualizado para {result.rowcount} predicciones\n")


@app.command("evaluate")
def evaluate_cmd(
    season_id: int = typer.Option(..., help="Season a evaluar"),
    date_from: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    date_to: Optional[str]   = typer.Option(None, "--to",   help="YYYY-MM-DD"),
    match_ids: Optional[List[int]] = typer.Option(None, help="IDs específicos"),
    over_thresh: float = typer.Option(0.5, help="Umbral Poisson OVER 2.5"),
    btts_thresh: float = typer.Option(0.5, help="Umbral Poisson BTTS YES"),
):
    """
    Evalúa el rendimiento de las predicciones contra resultados reales.
    """
    # ✅ NUEVO: Mostrar contexto de liga
    with engine.begin() as conn:
        league_ctx = LeagueContext.from_season(conn, season_id)
        
        typer.echo(f"\n{'='*70}")
        typer.echo(f"  EVALUANDO PREDICCIONES")
        typer.echo(f"{'='*70}")
        typer.echo(f"\n🏆 Liga: {league_ctx.league_name}")
        typer.echo(f"📅 Temporada: {league_ctx.season_year}\n")
    
    from .evaluate import evaluate as eval_fn
    counts = eval_fn(
        season_id=season_id,
        date_from=date_from,
        date_to=date_to,
        only_matches=match_ids,
        pick_over_thresh=over_thresh,
        pick_btts_thresh=btts_thresh,
    )
    
    typer.echo(f"\n✅ Evaluados: Poisson={counts['poisson']}, Weinston={counts['weinston']}\n")

@app.command("fit")
def fit_weinston_cmd(
    season_id: int = typer.Option(..., help="Season a entrenar"),
):
    """
    Entrena el modelo Weinston para una temporada.
    Calcula ratings de equipos (atk/def home/away) y parámetros de liga (mu_home, mu_away, home_adv).
    Guarda todo en weinston_ratings y weinston_params.
    
    ✅ Multi-Liga: Los parámetros se guardan específicos por season_id.
    """

    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. Obtener información de la liga/temporada
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    with SessionLocal() as s:
        # Obtener info de la temporada
        info_query = text("""
            SELECT 
                s.id,
                s.year_start,
                s.year_end,
                l.name as league_name,
                l.id as league_id,
                COUNT(m.id) as total_matches
            FROM seasons s
            LEFT JOIN leagues l ON l.id = s.league_id
            LEFT JOIN matches m ON m.season_id = s.id 
                AND m.home_goals IS NOT NULL 
                AND m.away_goals IS NOT NULL
            WHERE s.id = :season_id
            GROUP BY s.id, s.year_start, s.year_end, l.name, l.id
        """)
        
        info = s.execute(info_query, {"season_id": season_id}).fetchone()
        
        if not info:
            typer.echo(f"❌ Season ID {season_id} no encontrado")
            raise typer.Exit(1)
        
        league_name = info.league_name or "Unknown League"
        total_matches = info.total_matches or 0
        year_range = f"{info.year_start}/{info.year_end}" if info.year_end else str(info.year_start)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. Validación
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    typer.echo("\n" + "="*70)
    typer.echo(f"  🔄 ENTRENAMIENTO WEINSTON")
    typer.echo("="*70)
    typer.echo(f"  Liga: {league_name}")
    typer.echo(f"  Temporada: {year_range} (Season ID: {season_id})")
    typer.echo(f"  Partidos terminados: {total_matches}")
    typer.echo("="*70 + "\n")
    
    if total_matches < 10:
        typer.echo(f"⚠️  Advertencia: Solo hay {total_matches} partidos terminados")
        typer.echo(f"   Se recomienda al menos 10-20 partidos para un entrenamiento confiable")
        
        if not typer.confirm("¿Continuar de todos modos?"):
            typer.echo("❌ Entrenamiento cancelado")
            raise typer.Exit(0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. Entrenar el modelo
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    typer.echo(f"🔄 Entrenando modelo Weinston...")
    
    try:
        with SessionLocal() as s:
            result = fit_weinston(s, season_id)
            
            # Guardar ratings de equipos
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
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. Mostrar resultados
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            
            typer.echo("\n" + "="*70)
            typer.echo(f"  ✅ MODELO ENTRENADO EXITOSAMENTE")
            typer.echo("="*70)
            typer.echo(f"  Liga: {league_name}")
            typer.echo(f"  Temporada: {year_range}")
            typer.echo(f"")
            typer.echo(f"  📊 Equipos entrenados: {len(result.team_ids)}")
            typer.echo(f"  📈 μ_home (goles local): {result.mu_home:.3f}")
            typer.echo(f"  📉 μ_away (goles visit): {result.mu_away:.3f}")
            typer.echo(f"  🏠 Home Advantage: {result.home_adv:.3f}")
            typer.echo(f"  🎯 Loss (error): {result.loss:.4f}")
            typer.echo("="*70 + "\n")
            
            typer.echo(f"💾 Parámetros guardados en:")
            typer.echo(f"   • weinston_ratings (season_id={season_id})")
            typer.echo(f"   • weinston_params (season_id={season_id})")
            typer.echo("")
            
    except Exception as e:
        typer.echo(f"\n❌ Error entrenando Weinston: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)    


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
    typer.echo(f"✅ Evaluados: Poisson={counts['poisson']}, Weinston={counts['weinston']}")


# =====================================================================
# COMANDOS DE BETTING LINES (mantienen estructura original)
# =====================================================================

@app.command("betting-lines")
def betting_lines(
    season_id: int = typer.Option(..., help="ID de la temporada"),
    date_from: str = typer.Option(..., "--from", help="Fecha desde (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", help="Fecha hasta (YYYY-MM-DD)"),
    model: str = typer.Option("weinston", help="Modelo a usar: weinston o poisson"),
):
    """
    Genera líneas de apuesta para estadísticas (tiros, corners, tarjetas, faltas)
    
    Ejemplo:
        python -m src.predictions.cli betting-lines --season-id 2 --from 2024-12-20 --to 2024-12-31
    """
    if model.lower() not in ['weinston', 'poisson']:
        typer.echo("❌ Modelo debe ser 'weinston' o 'poisson'")
        raise typer.Exit(code=1)
    
    typer.echo(f"\n{'='*70}")
    typer.echo(f"  GENERANDO BETTING LINES - {model.upper()}")
    typer.echo(f"{'='*70}\n")
    typer.echo(f"Season: {season_id}")
    typer.echo(f"Rango: {date_from} a {date_to}\n")
    
    with engine.begin() as conn:
        # 1. Obtener las betting lines fijas desde league_parameters
        league_params_query = text("""
            SELECT 
                lp.betting_line_shots,
                lp.betting_line_shots_ot,
                lp.betting_line_corners,
                lp.betting_line_cards,
                lp.betting_line_fouls
            FROM seasons s
            JOIN league_parameters lp ON lp.league_id = s.league_id
            WHERE s.id = :season_id
            LIMIT 1
        """)
        
        league_params = conn.execute(league_params_query, {"season_id": season_id}).mappings().first()
        
        if not league_params:
            typer.echo("❌ No se encontraron parámetros de liga para esta temporada")
            raise typer.Exit(code=1)
        
        # Usar valores fijos de league_parameters
        FIXED_SHOTS_LINE = float(league_params['betting_line_shots'])
        FIXED_SHOTS_OT_LINE = float(league_params['betting_line_shots_ot'])
        FIXED_CORNERS_LINE = float(league_params['betting_line_corners'])
        FIXED_CARDS_LINE = float(league_params['betting_line_cards'])
        FIXED_FOULS_LINE = float(league_params['betting_line_fouls'])
        
        typer.echo(f"📋 Betting Lines Fijas (de league_parameters):")
        typer.echo(f"   Shots: {FIXED_SHOTS_LINE}")
        typer.echo(f"   Shots OT: {FIXED_SHOTS_OT_LINE}")
        typer.echo(f"   Corners: {FIXED_CORNERS_LINE}")
        typer.echo(f"   Cards: {FIXED_CARDS_LINE}")
        typer.echo(f"   Fouls: {FIXED_FOULS_LINE}\n")

        # ═══════════════════════════════════════════════════════════════
        # Resetear secuencia de betting_lines_predictions
        # ═══════════════════════════════════════════════════════════════
        try:
            typer.echo("\n🔄 Verificando secuencia de IDs...")
            
            # Resetear la secuencia al máximo ID actual
            reset_query = text("""
                SELECT setval(
                    'betting_lines_predictions_id_seq',
                    COALESCE((SELECT MAX(id) FROM betting_lines_predictions), 1),
                    true
                )
            """)
            
            result = conn.execute(reset_query).scalar()
            
            # Verificar el valor actual
            check_query = text("SELECT last_value FROM betting_lines_predictions_id_seq")
            current_val = conn.execute(check_query).scalar()
            
            typer.echo(f"✅ Secuencia reseteada a: {current_val}\n")
            
        except Exception as e:
            typer.echo(f"⚠️  Advertencia al resetear secuencia: {e}")
            typer.echo("   Continuando de todas formas...\n")

        # Query para obtener partidos y sus predicciones
        if model.lower() == 'weinston':
            matches_query = text("""
                SELECT 
                    m.id as match_id,
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
                JOIN weinston_predictions wp ON wp.match_id = m.id
                WHERE m.season_id = :season_id
                  AND m.date BETWEEN :date_from AND :date_to
                  AND m.home_goals IS NULL
                ORDER BY m.date
            """)
        else:  # poisson
            typer.echo("⚠️  Betting lines con Poisson aún no implementado completamente")
            typer.echo("   Usando predicciones de Weinston como referencia\n")
            matches_query = text("""
                SELECT 
                    m.id as match_id,
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
                JOIN weinston_predictions wp ON wp.match_id = m.id
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
            typer.echo("⚠️  No se encontraron partidos en el rango especificado")
            return
        
        typer.echo(f"📊 Partidos encontrados: {len(matches)}\n")
        
        generated_count = 0
        
        for match in matches:
            # Calcular totales predichos
            predicted_shots = match['shots_home'] + match['shots_away']
            predicted_shots_ot = match['shots_target_home'] + match['shots_target_away']
            predicted_corners = match['corners_home'] + match['corners_away']
            predicted_cards = match['cards_home'] + match['cards_away']
            predicted_fouls = match['fouls_home'] + match['fouls_away']
            
            # ✅ Usar betting lines FIJAS de league_parameters
            shots_line = FIXED_SHOTS_LINE
            shots_ot_line = FIXED_SHOTS_OT_LINE
            corners_line = FIXED_CORNERS_LINE
            cards_line = FIXED_CARDS_LINE
            fouls_line = FIXED_FOULS_LINE
            
            # Determinar predicción (over/under)
            shots_prediction = 'over' if predicted_shots > shots_line else 'under'
            shots_ot_prediction = 'over' if predicted_shots_ot > shots_ot_line else 'under'
            corners_prediction = 'over' if predicted_corners > corners_line else 'under'
            cards_prediction = 'over' if predicted_cards > cards_line else 'under'
            fouls_prediction = 'over' if predicted_fouls > fouls_line else 'under'
            
            # Factores de escala para normalizar el confidence
            SCALE_SHOTS = 6.0
            SCALE_SHOTS_OT = 2.5
            SCALE_CORNERS = 3.0
            SCALE_CARDS = 1.5
            SCALE_FOULS = 5.0

            # Calcular márgenes (qué tanto se aleja de la línea en la dirección predicha)
            shots_margin = predicted_shots - shots_line if predicted_shots > shots_line else shots_line - predicted_shots
            shots_ot_margin = predicted_shots_ot - shots_ot_line if predicted_shots_ot > shots_ot_line else shots_ot_line - predicted_shots_ot
            corners_margin = predicted_corners - corners_line if predicted_corners > corners_line else corners_line - predicted_corners
            cards_margin = predicted_cards - cards_line if predicted_cards > cards_line else cards_line - predicted_cards
            fouls_margin = predicted_fouls - fouls_line if predicted_fouls > fouls_line else fouls_line - predicted_fouls

            # Calcular confidence basado en el margen
            # Fórmula: min(margen / (escala * 0.5), 1.0) * 0.8 + 0.1
            # Esto da un rango de 10% a 90% (evita 0% y 100%)
            shots_confidence = min(max(shots_margin / (SCALE_SHOTS * 0.5), 0.0), 1.0) * 0.8 + 0.1
            shots_ot_confidence = min(max(shots_ot_margin / (SCALE_SHOTS_OT * 0.5), 0.0), 1.0) * 0.8 + 0.1
            corners_confidence = min(max(corners_margin / (SCALE_CORNERS * 0.5), 0.0), 1.0) * 0.8 + 0.1
            cards_confidence = min(max(cards_margin / (SCALE_CARDS * 0.5), 0.0), 1.0) * 0.8 + 0.1
            fouls_confidence = min(max(fouls_margin / (SCALE_FOULS * 0.5), 0.0), 1.0) * 0.8 + 0.1
            
            # Insertar o actualizar en betting_lines_predictions
            insert_query = text("""
                INSERT INTO betting_lines_predictions (
                    match_id, model,
                    predicted_total_shots, shots_line, shots_prediction, shots_confidence,
                    predicted_total_shots_on_target, shots_on_target_line, shots_on_target_prediction, shots_on_target_confidence,
                    predicted_total_corners, corners_line, corners_prediction, corners_confidence,
                    predicted_total_cards, cards_line, cards_prediction, cards_confidence,
                    predicted_total_fouls, fouls_line, fouls_prediction, fouls_confidence
                )
                VALUES (
                    :match_id, :model,
                    :predicted_shots, :shots_line, :shots_prediction, :shots_confidence,
                    :predicted_shots_ot, :shots_ot_line, :shots_ot_prediction, :shots_ot_confidence,
                    :predicted_corners, :corners_line, :corners_prediction, :corners_confidence,
                    :predicted_cards, :cards_line, :cards_prediction, :cards_confidence,
                    :predicted_fouls, :fouls_line, :fouls_prediction, :fouls_confidence
                )
                ON CONFLICT (match_id, model) DO UPDATE SET
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
                "model": model.lower(),
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
        
        typer.echo(f"\n✅ Betting lines generadas: {generated_count}/{len(matches)} partidos\n")


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