import typer
from src.db import SessionLocal
from .compute import compute_for_match, upsert_prediction

app = typer.Typer(help="Calcular Poisson para partidos")

@app.command()
def match(match_id: int):
    with SessionLocal() as s:
        pred = compute_for_match(s, match_id)
        upsert_prediction(s, pred)
        s.commit()
        typer.echo(f"OK: guardado match_id={match_id}")

if __name__ == "__main__":
    app()