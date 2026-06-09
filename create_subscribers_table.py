"""
Crea la tabla `subscribers` en la base de datos.
Ejecutar una sola vez en local y en producción:
  python create_subscribers_table.py
"""
from src.db import engine
from sqlalchemy import text


def main():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id            SERIAL PRIMARY KEY,
                nombre        VARCHAR(100)  NOT NULL,
                apellido      VARCHAR(100)  NOT NULL,
                correo        VARCHAR(255)  NOT NULL UNIQUE,
                telefono      VARCHAR(20),
                pais          VARCHAR(100),
                ciudad        VARCHAR(100),
                acepta_politica BOOLEAN     NOT NULL DEFAULT false,
                fecha_registro  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                activo        BOOLEAN       NOT NULL DEFAULT true
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_subscribers_correo ON subscribers(correo)"
        ))
    print("✅ Tabla 'subscribers' creada correctamente.")


if __name__ == "__main__":
    main()
