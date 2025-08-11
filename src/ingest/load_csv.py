import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from pathlib import Path
import typer
from tqdm import tqdm

from src.db import engine
from src.ingest.normalize import rename_columns

app = typer.Typer(help="Cargar CSV a tablas existentes")

@app.command()
def table(
    csv: str = typer.Argument(..., help="Ruta al CSV"),
    table: str = typer.Argument(..., help="Tabla destino (p.ej. teams, matches, match_stats, poisson_predictions)"),
    rename: bool = typer.Option(True, help="Renombrar columnas españolas a schema DB cuando aplique"),
    chunksize: int = typer.Option(5000, help="Tamaño de lote"),
):
    path = Path(csv)
    if not path.exists():
        raise typer.BadParameter(f"No existe: {path}")

    df = pd.read_csv(path)
    if rename:
        df = rename_columns(df)

    with engine.begin() as conn:
        # Carga en lotes usando COPY si es posible; pandas to_sql como fallback
        try:
            tmp_table = f"tmp_{table}"
            df.head(0).to_sql(tmp_table, conn, if_exists="replace", index=False)
            # usa COPY FROM STDIN vía psycopg2 fcopy
            copy_sql = f"COPY {tmp_table} ({', '.join(df.columns)}) FROM STDIN WITH CSV HEADER"
            with conn.connection.cursor() as cur:  # tipo psycopg2 cursor
                import io
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                buf.seek(0)
                cur.copy_expert(copy_sql, buf)
            # upsert simple por columnas en común; para tablas con PK 'id' se hará append
            # Mover de tmp a final
            conn.execute(text(f"INSERT INTO {table} ({', '.join(df.columns)}) SELECT {', '.join(df.columns)} FROM {tmp_table}"))
            conn.execute(text(f"DROP TABLE {tmp_table}"))
        except Exception:
            df.to_sql(table, conn, if_exists="append", index=False, method="multi")

if __name__ == "__main__":
    app()