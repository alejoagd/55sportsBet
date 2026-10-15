from datetime import date, timedelta

from src.predictions.attack_quality import compute_attack_quality, team_match_rows


def _match(i, home, away, hg, ag, hsot, asot, hs=12, as_=10):
    return dict(match_id=i, date=date(2025, 8, 1) + timedelta(days=i),
                home_team_id=home, away_team_id=away, home_goals=hg, away_goals=ag,
                home_sot=hsot, away_sot=asot, home_shots=hs, away_shots=as_)


def _league():
    # 4 equipos, todos contra todos dos veces: el 1 domina en tiros a puerta.
    ms, i = [], 0
    for _ in range(2):
        for h in (1, 2, 3, 4):
            for a in (1, 2, 3, 4):
                if h == a:
                    continue
                i += 1
                ms.append(_match(i, h, a, 3 if h == 1 else 1, 3 if a == 1 else 1,
                                 9 if h == 1 else 4, 9 if a == 1 else 4))
    return ms


def test_equipo_dominante_supera_100_y_los_demas_bajan():
    out = compute_attack_quality(team_match_rows(_league()))["teams"]
    assert out[1]["aqi"] > 100
    assert all(out[t]["aqi"] < 100 for t in (2, 3, 4))


def test_el_promedio_de_la_liga_ronda_100():
    out = compute_attack_quality(team_match_rows(_league()), window=38)["teams"]
    media = sum(t["aqi"] for t in out.values()) / len(out)
    assert 85 < media < 115


def test_pocos_partidos_devuelve_none_y_no_un_100_inventado():
    rows = team_match_rows([_match(1, 1, 2, 2, 0, 8, 2), _match(2, 3, 4, 1, 1, 5, 5)])
    out = compute_attack_quality(rows)["teams"]
    assert all(t["aqi"] is None for t in out.values())


def test_sin_datos_no_revienta():
    assert compute_attack_quality([]) == {"league": None, "teams": {}}


def test_la_conversion_extrema_se_regresa_a_la_media():
    # Mismos tiros a puerta; el equipo 1 convierte 6 goles de 18 SoT, el resto ~1.
    ms = _league()
    base = compute_attack_quality(team_match_rows(ms))["teams"][1]
    for m in ms:
        if m["home_team_id"] == 1:
            m["home_goals"] += 3
    boosted = compute_attack_quality(team_match_rows(ms))["teams"][1]
    assert boosted["aqi"] > base["aqi"]
    # la subida del AQI es mucho menor que la de los goles (se suaviza)
    assert boosted["aqi"] / base["aqi"] < boosted["avg_goals"] / base["avg_goals"]
