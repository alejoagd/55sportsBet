"""
Fusión de clubes duplicados: se mueve todo al equipo con más partidos y se rechazan
los pares que no son el mismo club. Tablas TEMP revertidas: no toca datos reales.
"""
import pytest
from sqlalchemy import text

from src.db import engine
from src.scripts.merge_duplicate_teams import merge_pair


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("CREATE TEMP TABLE teams (id INT PRIMARY KEY, name TEXT)"))
        c.execute(text("CREATE TEMP TABLE matches (id SERIAL, season_id INT, home_team_id INT, away_team_id INT)"))
        c.execute(text("CREATE TEMP TABLE team_external_ids (team_id INT, source TEXT, external_id INT, UNIQUE (source, external_id))"))
        c.execute(text("CREATE TEMP TABLE weinston_ratings (season_id INT, team_id INT, UNIQUE (season_id, team_id))"))
        c.execute(text("INSERT INTO teams VALUES (1,'Newells Old Boys'),(2,'Newell''s Old Boys'),(3,'Rival'),(4,'Otro')"))
        yield c
        tx.rollback()


def _partidos(c, tid):
    return c.execute(text("SELECT count(*) FROM matches WHERE :t IN (home_team_id, away_team_id)"), {"t": tid}).scalar()


def test_fusiona_en_el_equipo_con_mas_partidos(conn):
    # 1 = API-Football (temporada 10), 2 = ESPN (temporadas 20 y 21)
    conn.execute(text("INSERT INTO matches (season_id, home_team_id, away_team_id) VALUES (10,1,3),(20,2,3),(20,3,2),(21,2,4)"))
    conn.execute(text("INSERT INTO team_external_ids VALUES (1,'api_football',111),(2,'espn',222)"))
    conn.execute(text("INSERT INTO weinston_ratings VALUES (10,1),(20,2)"))

    estado, _ = merge_pair(conn, "Newells Old Boys", "Newell's Old Boys", apply=True)

    assert estado == "fusionado"
    assert conn.execute(text("SELECT count(*) FROM teams WHERE id = 1")).scalar() == 0
    assert _partidos(conn, 2) == 4 and _partidos(conn, 1) == 0
    assert conn.execute(text("SELECT count(*) FROM team_external_ids WHERE team_id = 2")).scalar() == 2
    assert conn.execute(text("SELECT count(*) FROM weinston_ratings WHERE team_id = 2")).scalar() == 2


def test_simulacion_no_escribe(conn):
    conn.execute(text("INSERT INTO matches (season_id, home_team_id, away_team_id) VALUES (10,1,3),(20,2,3)"))
    estado, _ = merge_pair(conn, "Newells Old Boys", "Newell's Old Boys", apply=False)
    assert estado == "fusionado"
    assert conn.execute(text("SELECT count(*) FROM teams")).scalar() == 4
    assert _partidos(conn, 1) == 1


def test_rechaza_si_se_enfrentaron_entre_si(conn):
    conn.execute(text("INSERT INTO matches (season_id, home_team_id, away_team_id) VALUES (10,1,2)"))
    estado, motivo = merge_pair(conn, "Newells Old Boys", "Newell's Old Boys", apply=True)
    assert estado == "omitido" and "entre sí" in motivo
    assert conn.execute(text("SELECT count(*) FROM teams")).scalar() == 4


def test_rechaza_si_comparten_temporada(conn):
    conn.execute(text("INSERT INTO matches (season_id, home_team_id, away_team_id) VALUES (10,1,3),(10,2,4)"))
    estado, motivo = merge_pair(conn, "Newells Old Boys", "Newell's Old Boys", apply=True)
    assert estado == "omitido" and "temporada" in motivo


def test_omite_si_un_nombre_no_existe(conn):
    estado, _ = merge_pair(conn, "Newells Old Boys", "No existe", apply=True)
    assert estado == "omitido"
