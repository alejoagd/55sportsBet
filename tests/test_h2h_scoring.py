"""
H2H Score: búsqueda de enfrentamientos por fecha, denominador y recuento.

Usa tablas TEMP dentro de una transacción que se revierte (en CI la BD está
vacía y nunca debe tocar datos reales).
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from src.db import engine
from src.predictions.h2h_scoring_system import (
    MIN_H2H_MATCHES, _calculate_scoring_by_stat, _get_h2h_matches,
)
from src.scripts.recount_h2h_scoring import build_predictions, parse_prediction

A, B = 1, 2


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("CREATE TEMP TABLE teams (id INT PRIMARY KEY, name TEXT)"))
        c.execute(text("CREATE TEMP TABLE seasons (id INT PRIMARY KEY, year_start INT, year_end INT)"))
        c.execute(text("""CREATE TEMP TABLE matches (id INT PRIMARY KEY, season_id INT, date DATE,
            home_team_id INT, away_team_id INT, home_goals INT, away_goals INT)"""))
        c.execute(text("""CREATE TEMP TABLE match_stats (match_id INT, home_shots INT, away_shots INT,
            home_shots_on_target INT, away_shots_on_target INT, home_fouls INT, away_fouls INT,
            home_corners INT, away_corners INT, home_yellow_cards INT, away_yellow_cards INT,
            home_red_cards INT, away_red_cards INT)"""))
        c.execute(text("INSERT INTO teams VALUES (1,'A'),(2,'B')"))
        # Los ids de temporada van AL REVÉS del tiempo (como en la BD real)
        c.execute(text("INSERT INTO seasons VALUES (29,2025,2026),(30,2024,2025),(31,2023,2024)"))
        yield c
        tx.rollback()


def _match(c, mid, season_id, d, home=A, away=B, goals=(1, 1), corners=(5, 5)):
    c.execute(text("INSERT INTO matches VALUES (:i,:s,:d,:h,:a,:hg,:ag)"),
              {"i": mid, "s": season_id, "d": d, "h": home, "a": away, "hg": goals[0], "ag": goals[1]})
    if corners is not None:
        c.execute(text("INSERT INTO match_stats VALUES (:i,10,10,4,4,10,10,:hc,:ac,1,1,0,0)"),
                  {"i": mid, "hc": corners[0], "ac": corners[1]})


def test_h2h_por_fecha_aunque_los_ids_de_temporada_vayan_al_reves(conn):
    base = date(2026, 1, 10)
    # 14 enfrentamientos previos repartidos entre las temporadas 31, 30 y 29
    for i in range(14):
        season = 31 if i < 5 else 30 if i < 10 else 29
        _match(conn, 100 + i, season, base - timedelta(days=200 - i * 10), home=A if i % 2 else B, away=B if i % 2 else A)
    _match(conn, 1, 29, base)                         # el partido que se analiza (temporada 29)
    _match(conn, 2, 29, base + timedelta(days=30))    # posterior: no debe contar

    h2h = _get_h2h_matches(conn, A, B, 1, 12)

    assert len(h2h) == 12                                       # tope de 12
    assert all(m["date"] < base for m in h2h)                   # solo anteriores
    assert 2 not in {m["id"] for m in h2h} and 1 not in {m["id"] for m in h2h}
    assert {m["season_id"] for m in h2h} >= {30, 29}            # incluye temporadas con id MAYOR (más viejas)
    assert [m["date"] for m in h2h] == sorted((m["date"] for m in h2h), reverse=True)


def test_denominador_cuenta_solo_h2h_con_dato_de_la_estadistica(conn):
    base = date(2026, 1, 10)
    for i in range(6):                                # 4 con corners y 2 sin estadísticas
        _match(conn, 100 + i, 30, base - timedelta(days=100 - i), corners=(6, 6) if i < 4 else None)
    _match(conn, 1, 29, base)
    h2h = _get_h2h_matches(conn, A, B, 1, 12)
    res = _calculate_scoring_by_stat({"corners": {"prediction": "OVER_9.5", "predicted_total": None, "line": 9.5}}, h2h, len(h2h))
    assert res["corners"]["valid_matches"] == 4       # el "4" de un 2/4
    assert res["corners"]["valid_matches"] < MIN_H2H_MATCHES
    assert res["corners"]["score"] == 4               # 12 corners >= 9.5 en los 4


@pytest.mark.parametrize("pred,expected", [
    ("OVER_9.5", ("OVER", 9.5)), ("UNDER_10.5", ("UNDER", 10.5)), ("OVER_2_5", ("OVER", 2.5)),
    ("UNDER_9.0", ("UNDER", 9.0)), ("", None), (None, None), ("YES", None),
])
def test_parse_prediction(pred, expected):
    assert parse_prediction(pred) == expected


def test_recuento_usa_la_linea_guardada_no_la_actual():
    preds = build_predictions({"corners": "OVER_9.5", "goles": "UNDER_2_5", "tiros": None})
    assert preds["corners"]["line"] == 9.5                 # la guardada (hoy sería 9.0)
    assert preds["goles"]["prediction"] == "UNDER_2_5"
    assert "tiros" not in preds
