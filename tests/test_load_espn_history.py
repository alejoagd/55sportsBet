"""
Cargador histórico de ESPN: parseo de años y protección contra años ya cubiertos
por otra fuente (evita duplicar partidos de API-Football por diferencias de fecha UTC).
"""
from datetime import date

from src.ingest.load_espn_history import YA_CARGADOS, parse_years


def test_parse_years_acepta_rangos_y_sueltos():
    assert parse_years(["2025", "2013-2015"]) == [2013, 2014, 2015, 2025]


def test_parse_years_sin_repetidos_y_ordenado():
    assert parse_years(["2015", "2013-2015", "2014"]) == [2013, 2014, 2015]


def test_anos_ya_cargados_incluyen_api_football_y_el_actual():
    assert {2022, 2023, 2024} <= YA_CARGADOS
    assert date.today().year in YA_CARGADOS
    assert 2025 not in YA_CARGADOS or date.today().year == 2025
