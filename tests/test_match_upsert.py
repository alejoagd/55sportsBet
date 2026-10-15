"""
Regresión de upsert_match / _retire_stale_bracket_placeholder.

Usa tablas TEMP dentro de una transacción que se revierte: en CI la BD está
vacía (sin esquema) y nunca debe tocar datos reales.
"""
from datetime import date

import pytest
from sqlalchemy import text

from src.db import engine
from src.ingest.match_upsert import upsert_match

SEASON = 1
FLU, PAL, TBD_H, TBD_A = 498, 502, 757, 758


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("""
            CREATE TEMP TABLE matches (
                id SERIAL PRIMARY KEY, season_id INT, date DATE NOT NULL,
                home_team_id INT, away_team_id INT, home_goals INT, away_goals INT,
                fulltime_result VARCHAR(100), stage VARCHAR(20), round_label TEXT,
                group_name VARCHAR(100), api_football_fixture_id INT,
                espn_event_id BIGINT, kickoff_at TIMESTAMPTZ
            )
        """))
        for t in ("betting_lines_predictions", "match_stats", "poisson_predictions",
                  "weinston_predictions", "wc_scoring_events"):
            c.execute(text(f"CREATE TEMP TABLE {t} (match_id INT)"))
        yield c
        tx.rollback()


def _upsert(conn, home, away, d, eeid, hg=None, ag=None):
    return upsert_match(
        conn, season_id=SEASON, match_date=d, home_id=home, away_id=away,
        home_goals=hg, away_goals=ag, stage="semifinal", round_label="Semifinals",
        espn_event_id=eeid,
    )


def _ids(conn):
    return {r.espn_event_id for r in conn.execute(text("SELECT espn_event_id FROM matches"))}


def test_ida_y_vuelta_coexisten(conn):
    # La vuelta (sin jugar) ya existe; entra la ida con el local/visitante invertido.
    _upsert(conn, PAL, FLU, date(2026, 10, 22), 401912520)
    _upsert(conn, FLU, PAL, date(2026, 10, 15), 401912522, hg=1, ag=2)
    assert _ids(conn) == {401912520, 401912522}

    # Y a la inversa (ida sin jugar, entra la vuelta): tampoco se borran entre sí.
    _upsert(conn, FLU, PAL, date(2026, 10, 15), 401912522)
    _upsert(conn, PAL, FLU, date(2026, 10, 22), 401912520)
    assert _ids(conn) == {401912520, 401912522}


def test_placeholder_tbd_sigue_retirandose(conn):
    _upsert(conn, TBD_H, TBD_A, date(2026, 10, 22), 999)
    _upsert(conn, PAL, FLU, date(2026, 10, 22), 401912520)
    assert _ids(conn) == {401912520}


def test_fila_corregida_a_mano_misma_orientacion_se_retira(conn):
    # Placeholder al que alguien ya le puso los equipos reales, con otra fecha.
    _upsert(conn, PAL, FLU, date(2026, 10, 21), 999)
    _upsert(conn, PAL, FLU, date(2026, 10, 22), 401912520)
    assert _ids(conn) == {401912520}
