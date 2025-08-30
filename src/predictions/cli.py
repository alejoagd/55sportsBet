# src/predictions/cli.py
from __future__ import annotations
import typer
from typing import Optional, List
from sqlalchemy import create_engine, text
from src.config import settings

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

if __name__ == "__main__":
    app()
