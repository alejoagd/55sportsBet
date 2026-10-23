"""
Sondeo en vivo de ESPN: lectura de estados (penales, pospuestos), mapeo por nombre y fecha,
y finalización del resultado. Tablas TEMP revertidas: no toca datos reales.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.db import engine
from src.live import store
from src.live.espn_live import LiveEvent, parse_event
from src.live.matching import encontrar_partido, parecido
from src.live.poller import es_rapido, Seguimiento


def raw(state="in", name="STATUS_SECOND_HALF", detail="73'", completed=False, hs="1", as_="0", hso=None, aso=None,
        home_winner=False, away_winner=False, details=None, date="2026-10-23T18:30Z"):
    return {"id": "401", "date": date, "status": {"displayClock": detail, "period": 2,
            "type": {"state": state, "name": name, "detail": detail, "completed": completed}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": hs, "shootoutScore": hso, "winner": home_winner, "team": {"id": "1", "displayName": "Flamengo"}},
                {"homeAway": "away", "score": as_, "shootoutScore": aso, "winner": away_winner, "team": {"id": "2", "displayName": "Estudiantes de La Plata"}}],
                "details": details or []}]}


def test_parse_en_juego():
    ev = parse_event(raw(), "Copa Libertadores")
    assert ev.en_juego and not ev.tiene_resultado and (ev.home_score, ev.away_score) == (1, 0)


def test_antes_de_empezar_no_hay_marcador():
    ev = parse_event(raw(state="pre", name="STATUS_SCHEDULED", detail="Fri 3:00 PM", hs="0", as_="0"), "La Liga")
    assert ev.home_score is None and ev.away_score is None and not ev.tiene_resultado


def test_penales_en_juego_no_es_resultado():
    ev = parse_event(raw(name="STATUS_SHOOTOUT", detail="Penalties", hs="0", as_="0", hso="1", aso="1"), "Copa Libertadores")
    assert ev.en_juego and not ev.tiene_resultado and (ev.home_shootout, ev.away_shootout) == (1, 1)


def test_final_por_penales_tiene_resultado_y_ganador():
    ev = parse_event(raw(state="post", name="STATUS_FINAL_PEN", detail="FT-Pens", completed=True, hs="0", as_="0",
                         hso="2", aso="3", away_winner=True), "Copa Libertadores")
    assert ev.tiene_resultado and ev.winner == "away"
    assert store.ganador_penales(ev, "Flamengo", "Estudiantes de La Plata") == "Estudiantes de La Plata"


@pytest.mark.parametrize("nombre", ["STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_ABANDONED"])
def test_pospuesto_o_cancelado_nunca_es_resultado(nombre):
    ev = parse_event(raw(state="post", name=nombre, detail="x", completed=True, hs="0", as_="0"), "La Liga")
    assert not ev.tiene_resultado


def test_post_sin_completed_no_es_resultado():
    assert not parse_event(raw(state="post", completed=False), "La Liga").tiene_resultado


def test_jugadas_se_leen_con_tarjetas_y_goles():
    d = [{"type": {"text": "Red Card"}, "clock": {"displayValue": "50'", "value": 2970.0}, "team": {"id": "1"}, "redCard": True},
         {"type": {"text": "Goal"}, "clock": {"displayValue": "70'", "value": 4150.0}, "team": {"id": "2"}, "scoringPlay": True}]
    ev = parse_event(raw(details=d), "Copa Libertadores")
    assert [(p["type"], p["red"], p["scoring"]) for p in ev.plays] == [("Red Card", True, False), ("Goal", False, True)]


def test_evento_malformado_se_ignora():
    assert parse_event({"id": "1"}, "La Liga") is None


@pytest.mark.parametrize("a,b", [("Man United", "Manchester United"), ("Nott'm Forest", "Nottingham Forest"),
                                 ("M'gladbach", "Borussia Mönchengladbach"), ("Ath Madrid", "Atlético Madrid"),
                                 ("Wolves", "Wolverhampton Wanderers"), ("FC Koln", "FC Cologne"), ("La Coruna", "Deportivo"),
                                 ("Espanol", "Espanyol"), ("Sociedad", "Real Sociedad")])
def test_mismo_club_distinto_nombre(a, b):
    assert parecido(a, b) >= 0.65


@pytest.mark.parametrize("a,b", [("Real Madrid", "Atlético Madrid"), ("Man City", "Manchester United"),
                                 ("Inter", "AC Milan"), ("Torino", "Monza"), ("Alaves", "Málaga")])
def test_clubes_distintos_no_se_confunden(a, b):
    assert parecido(a, b) < 0.65


@pytest.fixture
def conn():
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text("CREATE TEMP TABLE leagues (id INT, name TEXT)"))
        c.execute(text("CREATE TEMP TABLE seasons (id INT, league_id INT)"))
        c.execute(text("CREATE TEMP TABLE teams (id INT, name TEXT)"))
        c.execute(text("""CREATE TEMP TABLE matches (id INT, season_id INT, date DATE, home_team_id INT, away_team_id INT,
            home_goals INT, away_goals INT, fulltime_result TEXT, penalty_winner TEXT, espn_event_id BIGINT)"""))
        c.execute(text("INSERT INTO leagues VALUES (1, 'Bundesliga')"))
        c.execute(text("INSERT INTO seasons VALUES (10, 1)"))
        c.execute(text("INSERT INTO teams VALUES (1,'Stuttgart'),(2,'M''gladbach'),(3,'Dortmund'),(4,'Ein Frankfurt')"))
        c.execute(text("INSERT INTO matches (id, season_id, date, home_team_id, away_team_id) VALUES "
                       "(100, 10, '2026-10-23', 1, 2), (101, 10, '2026-10-24', 3, 4)"))
        yield c
        tx.rollback()


def ev_bl(local, visita, kick):
    return LiveEvent(espn_event_id=777, league="Bundesliga", kickoff=kick, home_name=local, away_name=visita, state="in",
                     status_name="STATUS_FIRST_HALF", detail="20'", clock="20'", period=1, completed=False, home_score=1, away_score=0)


K = datetime(2026, 10, 23, 18, 30, tzinfo=timezone.utc)


def test_mapea_por_nombre_y_fecha(conn):
    m, motivo = encontrar_partido(conn, ev_bl("VfB Stuttgart", "Borussia Mönchengladbach", K))
    assert m["id"] == 100 and motivo == "nombre+fecha"


def test_mapea_por_espn_event_id_aunque_los_nombres_no_se_parezcan(conn):
    conn.execute(text("UPDATE matches SET espn_event_id = 777 WHERE id = 101"))
    m, motivo = encontrar_partido(conn, ev_bl("Nombre raro", "Otro raro", K))
    assert m["id"] == 101 and motivo == "espn_event_id"


def test_no_mapea_si_la_fecha_esta_fuera_de_la_ventana(conn):
    m, _ = encontrar_partido(conn, ev_bl("VfB Stuttgart", "Borussia Mönchengladbach", K + timedelta(days=5)))
    assert m is None


def test_no_mapea_si_solo_un_equipo_coincide(conn):
    m, _ = encontrar_partido(conn, ev_bl("VfB Stuttgart", "Bayern Munich", K))
    assert m is None


def test_no_mapea_si_el_local_y_visitante_estan_invertidos(conn):
    m, _ = encontrar_partido(conn, ev_bl("Borussia Mönchengladbach", "VfB Stuttgart", K))
    assert m is None


def test_finalizar_guarda_resultado_ganador_de_penales_y_valida(conn, monkeypatch):
    llamadas = []
    monkeypatch.setattr(store, "validate_pending_best_bets", lambda c, sid: llamadas.append(sid))
    match = {"id": 100, "season_id": 10, "home_goals": None, "away_goals": None, "home": "Stuttgart", "away": "M'gladbach"}
    ev = LiveEvent(espn_event_id=777, league="Bundesliga", kickoff=K, home_name="x", away_name="y", state="post",
                   status_name="STATUS_FINAL_PEN", detail="FT-Pens", clock="90'", period=5, completed=True,
                   home_score=0, away_score=0, home_shootout=2, away_shootout=3)

    assert store.finalizar(conn, match, ev) == "nuevo"
    fila = conn.execute(text("SELECT home_goals, away_goals, fulltime_result, penalty_winner FROM matches WHERE id = 100")).one()
    assert tuple(fila) == (0, 0, "D", "M'gladbach") and llamadas == [10]


def test_finalizar_es_idempotente_y_corrige_si_cambia(conn, monkeypatch):
    monkeypatch.setattr(store, "validate_pending_best_bets", lambda c, sid: None)
    match = {"id": 100, "season_id": 10, "home_goals": None, "away_goals": None, "home": "Stuttgart", "away": "M'gladbach"}

    def ev(h, a):
        return LiveEvent(espn_event_id=777, league="Bundesliga", kickoff=K, home_name="x", away_name="y", state="post",
                         status_name="STATUS_FULL_TIME", detail="FT", clock="90'", period=2, completed=True, home_score=h, away_score=a)

    assert store.finalizar(conn, match, ev(2, 1)) == "nuevo"
    match.update(home_goals=2, away_goals=1)
    assert store.finalizar(conn, match, ev(2, 1)) == "igual"
    assert store.finalizar(conn, match, ev(2, 2)) == "corregido"
    assert conn.execute(text("SELECT fulltime_result FROM matches WHERE id = 100")).scalar() == "D"


def test_modo_rapido_solo_con_partidos_activos(monkeypatch):
    s = Seguimiento()
    en_juego = ev_bl("a", "b", K)
    assert es_rapido(en_juego, s, 0)
    lejano = ev_bl("a", "b", datetime.now(timezone.utc) + timedelta(hours=5))
    lejano.state = "pre"
    assert not es_rapido(lejano, s, 0)
    por_empezar = ev_bl("a", "b", datetime.now(timezone.utc) + timedelta(minutes=10))
    por_empezar.state = "pre"
    assert es_rapido(por_empezar, s, 0)


def test_candado_un_solo_sondeo_escribiendo_y_se_libera():
    from src.live import poller
    a = poller.adquirir_candado()
    assert a is not None
    try:
        assert poller.adquirir_candado() is None          # el segundo no puede mientras el primero vive
    finally:
        poller.liberar_candado(a)
    c = poller.adquirir_candado()                          # tras liberar (y cerrar de verdad la sesión) otro lo toma
    assert c is not None
    poller.liberar_candado(c)
