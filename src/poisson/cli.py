from typing import Optional
from datetime import datetime
import typer
from src.db import SessionLocal
from src.models import Match, PoissonPrediction
from .compute import compute_for_match, upsert_prediction

app = typer.Typer(help="Calcular Poisson para partidos")

def _parse_date(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise typer.BadParameter("Usa formato YYYY-MM-DD") from e

@app.command()
def backfill(
    season_id: Optional[int] = typer.Option(None),
    date_from: Optional[str] = typer.Option(None, help="YYYY-MM-DD"),
    date_to:   Optional[str] = typer.Option(None, help="YYYY-MM-DD"),
    only_missing: bool = typer.Option(True, "--only-missing/--no-only-missing",
                                      help="Solo partidos sin predicción"),
):
    dfrom = _parse_date(date_from)
    dto   = _parse_date(date_to)

    with SessionLocal() as s:
        q = s.query(Match.id).outerjoin(PoissonPrediction, PoissonPrediction.match_id == Match.id)
        if only_missing:
            q = q.filter(PoissonPrediction.match_id.is_(None))
        if season_id is not None:
            q = q.filter(Match.season_id == season_id)
        if dfrom:
            q = q.filter(Match.date >= dfrom)
        if dto:
            q = q.filter(Match.date <= dto)

        ids = [mid for (mid,) in q.order_by(Match.date.asc()).all()]
        for mid in ids:
            pred = compute_for_match(s, mid)
            upsert_prediction(s, pred)
        s.commit()
        typer.echo(f"OK: {len(ids)} predicciones generadas/actualizadas")

@app.command()
def match(match_id: int):
    with SessionLocal() as s:
        pred = compute_for_match(s, match_id)
        upsert_prediction(s, pred)
        s.commit()
        typer.echo(f"OK: guardado match_id={match_id}")

if __name__ == "__main__":
    app()
