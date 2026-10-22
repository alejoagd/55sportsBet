"""
Consolidación de partidos duplicados: conserva la fila con resultado y más datos,
no pierde lo que solo tenía la otra y omite grupos con resultados contradictorios.
Tablas TEMP revertidas: no toca datos reales.
"""
import pytest
from sqlalchemy import text

from src.db import engine
from src.scripts import dedupe_matches as dm

DEP_COLS = "match_id INT, model TEXT, stat TEXT, bet_type TEXT, team TEXT, player_name TEXT, minute INT, payload TEXT"


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("""CREATE TEMP TABLE matches (id INT PRIMARY KEY, season_id INT, home_team_id INT, away_team_id INT,
            date DATE, home_goals INT, away_goals INT, stage TEXT, round_label TEXT, group_name TEXT,
            halftime_homegoal INT, halftime_awaygoal INT, halftime_result TEXT, referee TEXT, apifootball_id INT,
            sofascore_id INT, penalty_winner TEXT, api_football_fixture_id INT, espn_event_id INT, kickoff_at TIMESTAMPTZ)"""))
        for t, _ in dm.DEPENDIENTES:
            c.execute(text(f"CREATE TEMP TABLE {t} ({DEP_COLS})"))
        c.execute(text("CREATE TEMP TABLE prediction_outcomes (match_id INT, model TEXT)"))
        yield c
        tx.rollback()


def _partido(c, mid, res=None, referee=None, d="2026-04-19"):
    hg, ag = res if res else (None, None)
    c.execute(text("INSERT INTO matches (id, season_id, home_team_id, away_team_id, date, home_goals, away_goals, referee) "
                   "VALUES (:i, 1, 10, 20, :d, :h, :a, :r)"), {"i": mid, "d": d, "h": hg, "a": ag, "r": referee})


def _cuenta(c, tabla, mid):
    return c.execute(text(f"SELECT count(*) FROM {tabla} WHERE match_id = :m"), {"m": mid}).scalar()


def test_elige_la_fila_con_resultado_aunque_tenga_id_mayor(conn):
    _partido(conn, 1)                      # fixture sin resultado (id menor)
    _partido(conn, 2, res=(2, 2))          # la jugada
    (grupo,) = dm.encontrar_grupos(conn)
    estado, info = dm.resolver_grupo(conn, grupo)
    assert estado == "ok" and info["keeper"] == 2 and info["losers"] == [1]


def test_sin_resultado_en_ninguna_gana_la_de_mas_datos(conn):
    _partido(conn, 1)
    _partido(conn, 2)
    conn.execute(text("INSERT INTO poisson_predictions (match_id) VALUES (2)"))
    (grupo,) = dm.encontrar_grupos(conn)
    assert dm.resolver_grupo(conn, grupo)[1]["keeper"] == 2


def test_mueve_lo_que_solo_tenia_la_descartada_y_descarta_lo_repetido(conn):
    _partido(conn, 1, res=(1, 0))
    _partido(conn, 2, res=(1, 0))
    conn.execute(text("INSERT INTO match_stats (match_id) VALUES (1), (2)"))                 # repetido: queda 1
    conn.execute(text("INSERT INTO poisson_predictions (match_id) VALUES (1)"))
    conn.execute(text("INSERT INTO best_bets_history (match_id, model, bet_type) VALUES (1,'poisson','OVER_25'),(2,'poisson','OVER_25'),(2,'weinston','OVER_25')"))
    conn.execute(text("INSERT INTO prediction_outcomes VALUES (2,'poisson')"))

    stats = dm.consolidar(conn, keeper=1, losers=[2])

    assert _cuenta(conn, "match_stats", 1) == 1
    assert _cuenta(conn, "best_bets_history", 1) == 2     # la repetida se descartó y la weinston se movió
    assert stats["best_bets_history: movidas"] == 1 and stats["best_bets_history: descartadas"] == 1
    assert conn.execute(text("SELECT count(*) FROM matches WHERE id = 2")).scalar() == 0
    assert _cuenta(conn, "prediction_outcomes", 2) == 0   # se regeneran con evaluate()


def test_hereda_campos_vacios_sin_pisar_los_que_ya_tiene(conn):
    _partido(conn, 1, res=(1, 0), referee=None)
    _partido(conn, 2, res=(1, 0), referee="Gil Manzano")
    conn.execute(text("UPDATE matches SET espn_event_id = 99 WHERE id = 2"))
    conn.execute(text("UPDATE matches SET halftime_homegoal = 1 WHERE id = 1"))
    conn.execute(text("UPDATE matches SET halftime_homegoal = 0 WHERE id = 2"))

    dm.consolidar(conn, keeper=1, losers=[2])

    fila = conn.execute(text("SELECT referee, espn_event_id, halftime_homegoal FROM matches WHERE id = 1")).one()
    assert tuple(fila) == ("Gil Manzano", 99, 1)


def test_omite_grupos_con_resultados_distintos(conn):
    _partido(conn, 1, res=(1, 0))
    _partido(conn, 2, res=(0, 3))
    (grupo,) = dm.encontrar_grupos(conn)
    estado, info = dm.resolver_grupo(conn, grupo)
    assert estado == "omitido" and "distintos" in info["motivo"]


def test_partidos_en_fechas_distintas_no_son_duplicados(conn):
    _partido(conn, 1, res=(1, 0), d="2026-04-19")
    _partido(conn, 2, res=(1, 0), d="2026-05-19")
    assert dm.encontrar_grupos(conn) == []
