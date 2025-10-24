# src/predictions/cli.py
from __future__ import annotations
import typer
from typing import Optional, List
from sqlalchemy import create_engine, text
from src.config import settings
from sqlalchemy import text
from typing import Optional, List

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


# Agregar este comando a src/predictions/cli.py

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


if __name__ == "__main__":
    app()
