"""
Indicadores destacados: misma regla que las tablas del módulo de Estadísticas (todos los equipos
ordenados, los 5 de arriba y los 5 de abajo). Función pura: no toca la BD.
"""
import pytest

from src.analysis.team_highlights import MIN_EQUIPOS, destacados, indicadores


def liga(goles_local: list[float], **extra) -> list[dict]:
    """Equipos 1..N (con nombre en orden alfabético) y su ofensiva de local; `extra` agrega otras columnas."""
    equipos = []
    for i, g in enumerate(goles_local, start=1):
        t = {"team_id": i, "team_name": f"Equipo {i:02d}", "home_matches": 3, "away_matches": 3,
             "home_avg_goals_scored": g, "away_avg_goals_scored": g}
        for campo, valores in extra.items():
            t[campo] = valores[i - 1]
        equipos.append(t)
    return equipos


def test_el_que_menos_anota_es_el_peor_ofensiva_puesto_1():
    eq = liga([0.0] + [1.0 + i * 0.1 for i in range(11)])
    (ind,) = indicadores(eq, 1, "home", con_stats=False)
    assert (ind["stat"], ind["direction"], ind["rank"], ind["of"], ind["pj"]) == ("goals", "least", 1, 12, 3)


def test_el_que_mas_anota_es_la_mejor_ofensiva():
    eq = liga([9.0] + [1.0 + i * 0.1 for i in range(11)])
    (ind,) = indicadores(eq, 1, "home", con_stats=False)
    assert (ind["direction"], ind["rank"]) == ("most", 1)


def test_el_puesto_6_ya_no_aparece_igual_que_en_el_modulo():
    eq = liga([float(i) for i in range(12)])           # equipo 6 anota 5.0: sexto desde abajo
    assert indicadores(eq, 6, "home", con_stats=False) == []
    assert indicadores(eq, 5, "home", con_stats=False)[0]["rank"] == 5


def test_empate_en_el_corte_se_resuelve_como_el_modulo_por_orden_alfabetico():
    # Seis equipos empatados en el valor más bajo: el módulo muestra los 5 primeros en orden (sort estable)
    eq = liga([1.0] * 6 + [3.0 + i for i in range(6)])
    en_tabla = [t for t in range(1, 7) if indicadores(eq, t, "home", False)]
    assert en_tabla == [1, 2, 3, 4, 5]                 # el 6.º queda fuera de la tabla de abajo


def test_local_y_visitante_se_miran_por_separado():
    eq = liga([2.0] * 12)
    for t in eq:
        t["away_avg_goals_scored"] = 1.0 + t["team_id"] * 0.1
    eq[0]["home_avg_goals_scored"] = 0.0               # peor ofensiva de local, pero de visitante es el 1.º por abajo igual
    assert indicadores(eq, 1, "home", False)[0]["direction"] == "least"
    away = indicadores(eq, 1, "away", False)
    assert away and away[0]["direction"] == "least"


def test_con_pocos_equipos_no_se_muestra_nada():
    assert indicadores(liga([0.0] + [1.0] * (MIN_EQUIPOS - 2)), 1, "home", False) == []


def test_sin_estadisticas_solo_se_evalua_la_ofensiva():
    n = 12
    eq = liga([1.0 + i * 0.1 for i in range(n)], home_avg_corners=[1.0] + [6.0] * (n - 1),
              away_avg_corners=[1.0] + [6.0] * (n - 1))
    assert {i["stat"] for i in indicadores(eq, 1, "home", con_stats=False)} == {"goals"}
    assert "corners" in {i["stat"] for i in indicadores(eq, 1, "home", con_stats=True)}


def test_dato_ausente_no_se_trata_como_cero():
    n = 12
    eq = liga([1.0 + i * 0.1 for i in range(n)], home_avg_corners=[None] * n, away_avg_corners=[None] * n)
    assert "corners" not in {i["stat"] for i in indicadores(eq, 1, "home", con_stats=True)}


def test_el_mas_marcado_va_primero():
    n = 12
    eq = liga([1.0 + i * 0.01 for i in range(n)], home_avg_shots=[2.0] + [14.0 + i * 0.1 for i in range(n - 1)],
              away_avg_shots=[2.0] * n)
    eq[0]["home_avg_goals_scored"] = 0.99               # puesto 1 abajo en goles, pero muy poco alejado de la liga
    stats = [i["stat"] for i in indicadores(eq, 1, "home", con_stats=True)]
    assert stats[0] == "shots"


def test_destacados_arma_los_dos_lados():
    eq = liga([0.0] + [1.0 + i * 0.1 for i in range(11)])
    d = destacados(eq, 1, 2, con_stats=False)
    assert d["home"]["team"] == "Equipo 01" and d["away"]["team"] == "Equipo 02"
    assert d["home"]["indicators"][0]["direction"] == "least" and d["top_n"] == 5


def test_equipo_que_no_esta_en_la_lista_no_rompe():
    assert indicadores(liga([1.0] * 12), 999, "home", False) == []
