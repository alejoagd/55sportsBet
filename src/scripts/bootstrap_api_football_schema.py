# src/scripts/bootstrap_api_football_schema.py
"""
Agrega a la BD las columnas/tabla necesarias para ingestar Brasileirao, Liga
Argentina, Liga Betplay, Copa Libertadores y Copa Sudamericana (API-Football +
ESPN). Mismo patrón ad hoc que ya usa el repo (ALTER TABLE ... IF NOT EXISTS
ejecutado desde un script, sin sistema de migraciones) — ver
seed_wc2026_r32_schedule.py / update_wc2026_r32_matches.py.

Uso:
  python -m src.scripts.bootstrap_api_football_schema
"""
from __future__ import annotations
from sqlalchemy import text
from src.db import engine

STATEMENTS = [
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS stage VARCHAR(20)",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS round_label TEXT",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS group_name VARCHAR(10)",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS api_football_fixture_id INTEGER",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS espn_event_id BIGINT",
    """
    CREATE TABLE IF NOT EXISTS team_external_ids (
        id SERIAL PRIMARY KEY,
        team_id INTEGER NOT NULL REFERENCES teams(id),
        source VARCHAR(30) NOT NULL,
        external_id INTEGER NOT NULL,
        UNIQUE(source, external_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_matches_api_football_fixture_id ON matches(api_football_fixture_id)",
    "CREATE INDEX IF NOT EXISTS ix_matches_espn_event_id ON matches(espn_event_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"-- {stmt.strip().splitlines()[0]}...")
            conn.execute(text(stmt))
    print("\n✅ Schema listo: stage/round_label/group_name/api_football_fixture_id/espn_event_id en matches, tabla team_external_ids.")


if __name__ == "__main__":
    main()
