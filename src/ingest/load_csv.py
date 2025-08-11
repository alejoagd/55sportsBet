# (opcional) Cargador directo a una sola tabla. Lo mantenemos por si lo necesitas.
import pandas as pd
from sqlalchemy import text
from pathlib import Path
import typer
from src.db import engine
from src.ingest.normalize import rename_columns

app = typer.Typer(help="Cargar CSV a tablas existentes")

@app.command()
def table(
    csv: str = typer.Argument(..., help="Ruta al CSV"),
    table: str = typer.Argument(..., help="Tabla destino (p.ej. teams, matches, match_stats, poisson_predictions)"),
    rename: bool = typer.Option(True, help="Renombrar columnas españolas a schema DB cuando aplique"),
):
    path = Path(csv)
    if not path.exists():
        raise typer.BadParameter(f"No existe: {path}")

    df = pd.read_csv(path)
    if rename:
        df = rename_columns(df)

    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="append", index=False, method="multi")

if __name__ == "__main__":
    app()