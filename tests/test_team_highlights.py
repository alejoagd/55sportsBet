"""
Indicadores destacados: selección pura (más/menos, empates, muestras mínimas) y el cálculo desde la
BD con tablas TEMP (no toca datos reales).
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from src.analysis import team_highlights as th
from src.analysis.team_highlights import destacados_del_partido, indicadores
from src.db import engine


def liga(valores: list[float], n: int = 10, stat: str = "corners") -> dict:
    """Equipos 1..len(valores) con ese valor y n partidos."""
    return {i + 1: {stat: (v, n)} for i, v in enumerate(valores)}


def test_el_que_menos_hace_queda_en_el_puesto_1():
    m = liga([3.0] + [5.0 + i * 0.1 for i in range(11)])            # equipo 1: el que menos córners hace
    (ind,) = indicadores(m, 1)
    assert (ind["stat"], ind["direction"], ind["rank"], ind["of"]) == ("corners", "least", 1, 12)


def test_el_que_mas_hace_queda_en_el_puesto_1():
    m = liga([9.0] + [5.0 + i * 0.1 for i in range(11)])
    (ind,) = indicadores(m, 1)
    assert (ind["direction"], ind["rank"]) == ("most", 1)


def test_mitad_de_tabla_no_se_destaca():
    m = liga([5.0 + i * 0.1 for i in range(12)])
    assert indicadores(m, 6) == []


def test_el_sexto_ya_no_cuenta():
    m = liga([1.0, 2.0, 3.0, 4.0, 5.0, 6.0] + [10.0 + i for i in range(6)])
    assert indicadores(m, 6) == []                                    # 6.º que menos hace
    assert indicadores(m, 5)[0]["rank"] == 5


def test_ranking_con_menos_equipos_de_los_minimos_no_se_muestra():
    assert indicadores(liga([3.0, 5.0, 6.0, 7.0, 8.0, 9.0, 4.0, 5.5]), 1) == []   # 8 equipos


def test_equipo_con_pocos_partidos_no_entra_al_ranking():
    m = liga([3.0] + [5.0 + i * 0.1 for i in range(11)])
    m[1]["corners"] = (3.0, th.MIN_PARTIDOS - 1)
    assert indicadores(m, 1) == []


def test_todos_iguales_nadie_se_destaca():
    assert indicadores(liga([5.0] * 12), 1) == []


def test_el_mas_marcado_va_primero():
    m = {i: {"corners": (5.0 + i * 0.1, 10), "shots": (14.0 + i * 0.1, 10)} for i in range(1, 13)}
    m[1] = {"corners": (4.7, 10), "shots": (5.0, 10)}                 # equipo 1: #1 menos en ambos, mucho más extremo en tiros
    assert [i["stat"] for i in indicadores(m, 1)] == ["shots", "corners"]


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("CREATE TEMP TABLE leagues (id INT, name TEXT)"))
        c.execute(text("CREATE TEMP TABLE seasons (id INT, league_id INT)"))
        c.execute(text("CREATE TEMP TABLE teams (id INT, name TEXT)"))
        c.execute(text("""CREATE TEMP TABLE matches (id INT, date DATE, season_id INT, home_team_id INT, away_team_id INT,
                          home_goals INT, away_goals INT)"""))
        c.execute(text("""CREATE TEMP TABLE match_stats (match_id INT, home_shots INT, away_shots INT, home_shots_on_target INT,
            away_shots_on_target INT, home_corners INT, away_corners INT, home_fouls INT, away_fouls INT,
            home_yellow_cards INT, away_yellow_cards INT, home_red_cards INT, away_red_cards INT)"""))
        c.execute(text("INSERT INTO leagues VALUES (1, 'Liga X')"))
        c.execute(text("INSERT INTO seasons VALUES (10, 1)"))
        for t in range(1, 13):
            c.execute(text("INSERT INTO teams VALUES (:t, :n)"), {"t": t, "n": f"Equipo {t}"})
        yield c
        tx.rollback()


def _jornadas(c, hasta: date):
    """Cada equipo juega 6 veces de local. El equipo 1 hace pocos córners; el resto 6."""
    mid, d = 1, hasta - timedelta(days=200)
    for ronda in range(6):
        for local in range(1, 13):
            visita = local % 12 + 1
            d += timedelta(days=1)
            c.execute(text("INSERT INTO matches VALUES (:i, :d, 10, :h, :a, 1, 1)"), {"i": mid, "d": d, "h": local, "a": visita})
            corners = 2 if local == 1 else 6
            c.execute(text("INSERT INTO match_stats VALUES (:i, 12, 11, 4, 4, :c, 5, 10, 10, 1, 1, NULL, NULL)"), {"i": mid, "c": corners})
            mid += 1
    return mid


def test_desde_la_bd_el_local_que_menos_corners_hace(conn):
    hoy = date(2026, 10, 23)
    sig = _jornadas(conn, hoy)
    conn.execute(text("INSERT INTO matches VALUES (:i, :d, 10, 1, 2, NULL, NULL)"), {"i": sig, "d": hoy})   # el partido a analizar
    d = destacados_del_partido(conn, sig)
    c = next(i for i in d["home"]["indicators"] if i["stat"] == "corners")
    assert (c["direction"], c["rank"], c["of"], c["value"]) == ("least", 1, 12, 2.0)
    assert d["home"]["team"] == "Equipo 1" and d["away"]["team"] == "Equipo 2"


def test_no_cuenta_el_propio_partido_ni_los_posteriores(conn):
    hoy = date(2026, 10, 23)
    sig = _jornadas(conn, hoy)
    conn.execute(text("INSERT INTO matches VALUES (:i, :d, 10, 1, 2, 3, 3)"), {"i": sig, "d": hoy})        # mismo día: no cuenta
    conn.execute(text("INSERT INTO match_stats VALUES (:i, 99, 99, 9, 9, 99, 99, 99, 99, 9, 9, 0, 0)"), {"i": sig})
    d = destacados_del_partido(conn, sig)
    c = next(i for i in d["home"]["indicators"] if i["stat"] == "corners")
    assert c["value"] == 2.0                                          # el 99 del propio partido no entró


def test_partido_inexistente(conn):
    assert destacados_del_partido(conn, 999999) is None
