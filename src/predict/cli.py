from __future__ import annotations
import typer
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from src.db import SessionLocal
from src.models import Match
from src.poisson.compute import compute_for_match, upsert_prediction

# Importamos el backfill de Winston (ya probado)
from src.weinston.cli import backfill as weinston_backfill  # <- tu backfill existente

app = typer.Typer(help="Orquestador de predicciones (Poisson + Winston)")

def _window_query(s, d_from: date, d_to: date):
    return (
        s.execute(
            select(Match.id)
            .where(and_(Match.date >= d_from, Match.date <= d_to))
            .order_by(Match.date, Match.id)
        ).scalars().all()
    )

@app.command()
def window(
    season_id: int = typer.Option(..., "--season-id"),
    start: str = typer.Option(None, help="YYYY-MM-DD (default: hoy)"),
    end:   str = typer.Option(None, help="YYYY-MM-DD (default: hoy+7)"),
    only_missing: bool = typer.Option(True, help="Winston: calcular sólo faltantes"),
):
    """Corre Winston (fit/backfill de toda la temporada) y Poisson (sólo ventana)."""
    today = datetime.today().date()
    d_from = datetime.strptime(start, "%Y-%m-%d").date() if start else today
    d_to   = datetime.strptime(end, "%Y-%m-%d").date() if end else (today + timedelta(days=7))

    # 1) Winston: usamos tu backfill que hace upsert (puede tardar, pero es idempotente)
    weinston_backfill(season_id=season_id, only_missing=only_missing)

    # 2) Poisson: sólo para la ventana pedida
    with SessionLocal() as s:
        mids = _window_query(s, d_from, d_to)
        n = 0
        for mid in mids:
            pred = compute_for_match(s, mid)
            upsert_prediction(s, pred)
            n += 1
        s.commit()
        typer.echo(f"OK ventana {d_from}..{d_to}: Poisson upsert {n} partidos")

@app.command()
def missing(
    season_id: int = typer.Option(..., "--season-id"),
    start: str = typer.Option(None, help="YYYY-MM-DD"),
    end:   str = typer.Option(None, help="YYYY-MM-DD"),
):
    """Calcula predicciones sólo para partidos de la ventana que no las tienen."""
    today = datetime.today().date()
    d_from = datetime.strptime(start, "%Y-%m-%d").date() if start else today
    d_to   = datetime.strptime(end, "%Y-%m-%d").date() if end else (today + timedelta(days=7))

    # Winston primero (sólo faltantes)
    weinston_backfill(season_id=season_id, only_missing=True)

    # Poisson: sólo faltantes
    sql = """
    select m.id
    from matches m
    left join poisson_predictions pp on pp.match_id = m.id
    where m.date between :d_from and :d_to
      and pp.match_id is null
    order by m.date, m.id
    """
    with SessionLocal() as s:
        ids = [r[0] for r in s.execute(sql, {"d_from": d_from, "d_to": d_to}).all()]
        n=0
        for mid in ids:
            pred = compute_for_match(s, mid)
            upsert_prediction(s, pred)
            n+=1
        s.commit()
        typer.echo(f"OK missing Poisson: {n} nuevos en {d_from}..{d_to}")

if __name__ == "__main__":
    app()
