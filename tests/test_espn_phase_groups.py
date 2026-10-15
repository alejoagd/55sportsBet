"""
fetch_phase_groups: zonas por fase de la API core de ESPN (sin red).

Regresión: fetch_groups() devolvía {} y la Liga Argentina se veía como una
sola tabla de 30 equipos en vez de Grupo A / Grupo B.
"""
from src.ingest import espn_core_client as core

U = "http://x/leagues/arg.1/seasons/2026/types"


def _fake_get_json(url, params=None):
    table = {
        U: {"items": [{"$ref": f"{U}/6"}, {"$ref": f"{U}/7"}]},
        f"{U}/6": {"id": "6", "name": "Torneo Clausura", "hasGroups": True},
        f"{U}/7": {"id": "7", "name": "Clausura - Round of 16", "hasGroups": False},
        f"{U}/6/groups": {"items": [{"$ref": f"{U}/6/groups/1"}, {"$ref": f"{U}/6/groups/2"}]},
        f"{U}/6/groups/1": {"name": "Group A", "standings": {"$ref": f"{U}/6/groups/1/standings"}},
        f"{U}/6/groups/2": {"name": "Group B", "standings": {"$ref": f"{U}/6/groups/2/standings"}},
        f"{U}/6/groups/1/standings": {"items": [{"$ref": f"{U}/6/groups/1/standings/0"}]},
        f"{U}/6/groups/2/standings": {"items": [{"$ref": f"{U}/6/groups/2/standings/0"}]},
        f"{U}/6/groups/1/standings/0": {"standings": [
            {"team": {"$ref": "http://x/seasons/2026/teams/5?lang=en"}},
            {"team": {"$ref": "http://x/seasons/2026/teams/8?lang=en"}},
        ]},
        f"{U}/6/groups/2/standings/0": {"standings": [
            {"team": {"$ref": "http://x/seasons/2026/teams/11?lang=en"}},
        ]},
    }
    return table.get(url)


def test_zonas_por_fase(monkeypatch):
    monkeypatch.setattr(core, "BASE", "http://x/leagues")
    monkeypatch.setattr(core, "_get_json", _fake_get_json)

    assert core.fetch_phase_groups("arg.1", 2026) == {
        "Torneo Clausura": {5: "Group A", 8: "Group A", 11: "Group B"},
    }


def test_sin_fases_con_grupos(monkeypatch):
    monkeypatch.setattr(core, "_get_json", lambda url, params=None: None)
    assert core.fetch_phase_groups("bra.1", 2026) == {}
