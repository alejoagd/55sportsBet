"""
Temporada en curso por liga: la que tiene más partidos pendientes (y, a igualdad,
la más nueva); excluye el Mundial. Tablas TEMP revertidas: no toca datos reales.
"""
import pytest
from sqlalchemy import text

from src.api import _current_seasons
from src.db import engine


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("CREATE TEMP TABLE leagues (id INT PRIMARY KEY, name TEXT)"))
        c.execute(text("CREATE TEMP TABLE seasons (id INT PRIMARY KEY, league_id INT, year_start INT)"))
        c.execute(text("CREATE TEMP TABLE matches (id INT PRIMARY KEY, season_id INT, date DATE, home_goals INT, away_goals INT)"))
        yield c
        tx.rollback()


def _add_match(c, mid, season, played):
    c.execute(text("INSERT INTO matches VALUES (:i,:s,'2026-10-01',:g,:g)"), {"i": mid, "s": season, "g": 1 if played else None})


def test_elige_la_temporada_con_partidos_pendientes_y_excluye_el_mundial(conn):
    conn.execute(text("INSERT INTO leagues VALUES (1,'Serie A'),(2,'Liga Argentina'),(3,'FIFA World Cup')"))
    # Serie A: ids al revés del tiempo (29 = 2025, 110 = 2026). La 2026 tiene pendientes.
    conn.execute(text("INSERT INTO seasons VALUES (29,1,2025),(110,1,2026),(50,2,2026),(51,2,2025),(76,3,2026)"))
    for i in range(3): _add_match(conn, 100 + i, 29, True)
    _add_match(conn, 200, 110, True); _add_match(conn, 201, 110, False); _add_match(conn, 202, 110, False)
    _add_match(conn, 300, 50, False)                 # Argentina 2026 con pendiente
    _add_match(conn, 301, 51, True)                  # Argentina 2025 ya terminada
    _add_match(conn, 400, 76, False)                 # Mundial: no cuenta

    res = {r["league_name"]: r["season_id"] for r in _current_seasons(conn)}

    assert res == {"Serie A": 110, "Liga Argentina": 50}


def test_a_igualdad_de_pendientes_gana_la_mas_nueva(conn):
    conn.execute(text("INSERT INTO leagues VALUES (1,'La Liga')"))
    conn.execute(text("INSERT INTO seasons VALUES (15,1,2025),(109,1,2026)"))
    _add_match(conn, 1, 15, True); _add_match(conn, 2, 109, True)   # sin pendientes en ninguna
    assert [r["season_id"] for r in _current_seasons(conn)] == [109]
