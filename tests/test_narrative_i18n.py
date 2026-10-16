"""
Narrativa H2H en es/en/pt/fr. El español debe seguir siendo EXACTAMENTE el de
siempre (referencia en tests/data/narrative_h2h_es.json, generada antes de
mover los textos a src/narrative_i18n.py).
"""
import json
from pathlib import Path

import pytest

from src.api import generate_match_narrative, _venue_stat_items
from src.narrative_i18n import SUPPORTED_LANGS, TEXT, norm_lang

GOLDEN = json.loads((Path(__file__).parent / "data" / "narrative_h2h_es.json").read_text(encoding="utf-8"))


def _stats(avg_total=3.4, btts=70, over=65, corners=10.2, cards=4.6):
    v = lambda **k: k
    return {"has_data": True, "total_matches": 8, "avg_total_goals": avg_total, "btts_percentage": btts,
            "over25_percentage": over, "avg_total_corners": corners, "avg_total_cards": cards,
            "home_venue": v(avg_home_goals=2.1, avg_away_goals=1.3, avg_home_shots=13.5, avg_away_shots=9.2,
                            avg_home_shots_on_target=5.1, avg_away_shots_on_target=3.3, avg_home_corners=6.0, avg_away_corners=4.1,
                            avg_home_fouls=12.2, avg_away_fouls=13.0, avg_home_cards=2.0, avg_away_cards=2.8),
            "away_venue": v(avg_team_goals=1.0, avg_opponent_goals=1.8, avg_team_shots=8.0, avg_opponent_shots=12.0,
                            avg_team_shots_on_target=3.0, avg_opponent_shots_on_target=4.5, avg_team_corners=3.9, avg_opponent_corners=5.8,
                            avg_team_fouls=11.0, avg_opponent_fouls=12.5, avg_team_cards=1.9, avg_opponent_cards=2.4)}


H2H_HOME = [{"home_goals": 2, "away_goals": 1, "btts": True, "over25": True},
            {"home_goals": 1, "away_goals": 1, "btts": True, "over25": False},
            {"home_goals": 0, "away_goals": 2, "btts": False, "over25": False}]
H2H_AWAY = [{"team_goals": 1, "opponent_goals": 3, "btts": True, "over25": True},
            {"team_goals": 2, "opponent_goals": 0, "btts": False, "over25": False}]
MI = {"home_team": "Barcelona", "away_team": "Real Madrid", "pred_home_goals": 2.4, "pred_away_goals": 1.6}


def _cases(lang):
    return {
        "alto": generate_match_narrative(MI, _stats(), H2H_HOME, H2H_AWAY, lang),
        "bajo": generate_match_narrative({**MI, "pred_home_goals": 0.7, "pred_away_goals": 0.6}, _stats(1.4, 20, 10, None, None), H2H_HOME, [], lang),
        "medio": generate_match_narrative({**MI, "pred_home_goals": 1.3, "pred_away_goals": 1.2}, _stats(2.4, 45, 50), [], H2H_AWAY, lang),
        "sin_datos": generate_match_narrative(MI, {"has_data": False}, [], [], lang),
        "items": _venue_stat_items(_stats()["home_venue"], "home", "away", lang),
    }


def test_espanol_identico_al_original():
    assert _cases("es") == GOLDEN
    assert _cases("") == GOLDEN       # idioma vacío -> español
    assert _cases("de") == GOLDEN     # idioma no soportado -> español


def test_todos_los_idiomas_tienen_las_mismas_claves():
    base = set(TEXT["es"])
    for lang in SUPPORTED_LANGS:
        assert set(TEXT[lang]) == base, lang


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_otros_idiomas_no_dejan_texto_en_espanol(lang):
    spanish_markers = ("Promedio", "partidos", "Cuando", "Predicción", "Tendencia", "tarjetas", "goles")
    for name, case in _cases(lang).items():
        text = json.dumps(case, ensure_ascii=False)
        assert not any(w in text for w in spanish_markers), (lang, name)
    assert _cases(lang)["alto"]["full_narrative"] != GOLDEN["alto"]["full_narrative"]


def test_norm_lang():
    assert norm_lang("EN-us") == "en"
    assert norm_lang(None) == "es"
    assert norm_lang("zz") == "es"
