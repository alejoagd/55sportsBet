"""
Error de goles de Poisson: fórmula compartida con Weinston y recálculo de las
filas que quedaron en NULL. Tablas TEMP revertidas: no toca datos reales.
"""
import math

import pytest
from sqlalchemy import text

from src.db import engine
from src.predictions.evaluate import goal_errors
from src.scripts.backfill_poisson_rmse import check_consistency, count_missing, fill_missing


def test_goal_errors_formula():
    ae_h, ae_a, rmse = goal_errors(2.4, 0.8, 1, 3)
    assert ae_h == pytest.approx(1.4) and ae_a == pytest.approx(2.2)
    assert rmse == pytest.approx(math.sqrt((1.4 ** 2 + 2.2 ** 2) / 2))


def test_goal_errors_prediccion_exacta():
    assert goal_errors(2.0, 1.0, 2, 1) == (0.0, 0.0, 0.0)


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("""CREATE TEMP TABLE prediction_outcomes (match_id INT, model TEXT, hit_1x2 BOOL,
            abs_err_home_goals NUMERIC, abs_err_away_goals NUMERIC, rmse_goals NUMERIC, updated_at TIMESTAMPTZ)"""))
        c.execute(text("CREATE TEMP TABLE poisson_predictions (match_id INT, expected_home_goals NUMERIC, expected_away_goals NUMERIC)"))
        c.execute(text("CREATE TEMP TABLE matches (id INT, home_goals INT, away_goals INT)"))
        yield c
        tx.rollback()


def _seed(c):
    c.execute(text("INSERT INTO matches VALUES (1,1,3),(2,2,2),(3,0,0),(4,NULL,NULL)"))
    c.execute(text("INSERT INTO poisson_predictions VALUES (1,2.4,0.8),(2,1.5,1.5),(3,1.0,1.0),(4,1.0,1.0)"))
    c.execute(text("INSERT INTO prediction_outcomes VALUES (1,'poisson',true,NULL,NULL,NULL,NULL),(2,'poisson',false,NULL,NULL,NULL,NULL),"
                   "(3,'poisson',true,1.0,1.0,1.0,NULL),(4,'poisson',NULL,NULL,NULL,NULL,NULL),(1,'weinston',true,0.1,0.1,0.1,NULL)"))


def test_rellena_solo_los_vacios_de_partidos_terminados(conn):
    _seed(conn)
    assert count_missing(conn) == 2            # partidos 1 y 2; el 4 no se jugó

    assert fill_missing(conn) == 2

    rows = {r[0]: r for r in conn.execute(text(
        "SELECT match_id, rmse_goals, abs_err_home_goals, hit_1x2 FROM prediction_outcomes WHERE model='poisson' ORDER BY match_id"))}
    assert float(rows[1][1]) == pytest.approx(math.sqrt((1.4 ** 2 + 2.2 ** 2) / 2), abs=1e-6)
    assert float(rows[2][1]) == pytest.approx(math.sqrt((0.5 ** 2 + 0.5 ** 2) / 2), abs=1e-6)
    assert float(rows[3][1]) == 1.0            # ya tenía valor: no se toca
    assert rows[4][1] is None                  # sin resultado: sigue vacío
    assert rows[1][3] is True and rows[2][3] is False   # hit_* intactos
    assert float(conn.execute(text("SELECT rmse_goals FROM prediction_outcomes WHERE model='weinston'")).scalar()) == 0.1


def test_detecta_si_la_formula_no_coincide(conn):
    _seed(conn)
    # partido 3 (0-0 con esperados 1.0/1.0): la fórmula da 1.0, igual a lo guardado
    count, max_diff = check_consistency(conn)
    assert count == 1 and max_diff == pytest.approx(0.0)

    conn.execute(text("UPDATE prediction_outcomes SET rmse_goals = 1.5 WHERE match_id = 3 AND model = 'poisson'"))
    _, max_diff = check_consistency(conn)
    assert max_diff == pytest.approx(0.5)
