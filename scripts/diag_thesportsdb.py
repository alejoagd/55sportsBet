#!/usr/bin/env python
"""Diagnóstico temporal: valida si TheSportsDB (plan gratis, key de prueba)
sirve como fuente alternativa para Liga Argentina, Liga Betplay, Copa
Libertadores y Copa Sudamericana — bloqueadas en ESPN desde 2026-08-04.

No requiere API key propia (usa la key de prueba pública "3"), así que se
puede probar sin pedirle nada al usuario todavía.
"""
import requests

API_KEY = "3"
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

TARGETS = {
    "Liga Argentina": ["Argentine Primera Division", "Argentina Primera Division", "Argentina"],
    "Liga Betplay": ["Colombian Primera A", "Colombia Primera A", "Colombia"],
    "Copa Libertadores": ["Copa Libertadores"],
    "Copa Sudamericana": ["Copa Sudamericana"],
}


def get(url: str, params: dict | None = None):
    resp = requests.get(url, params=params, timeout=20)
    print(f"  GET {resp.url} -> {resp.status_code}")
    resp.raise_for_status()
    return resp.json()


def main():
    print("=== all_leagues.php ===")
    try:
        data = get(f"{BASE}/all_leagues.php")
        leagues = data.get("leagues") or []
        print(f"  {len(leagues)} ligas totales en el catálogo")
    except Exception as e:
        print(f"  ERROR: {e}")
        leagues = []

    matches_found: dict[str, list] = {}
    for name in leagues:
        lname = name.get("strLeague", "")
        for key, patterns in TARGETS.items():
            for p in patterns:
                if p.lower() in lname.lower():
                    matches_found.setdefault(key, []).append((name.get("idLeague"), lname))

    for key in TARGETS:
        print(f"\n=== Candidatos para {key} ===")
        for lid, lname in matches_found.get(key, []):
            print(f"  idLeague={lid}  {lname}")

    # Para cada competencia, si encontramos un candidato, probamos traer
    # el calendario/resultados de la temporada 2026.
    for key, found in matches_found.items():
        if not found:
            continue
        lid, lname = found[0]
        print(f"\n=== eventsseason.php para {lname} (id={lid}, season=2026) ===")
        try:
            data = get(f"{BASE}/eventsseason.php", {"id": lid, "s": "2026"})
            events = data.get("events") or []
            print(f"  {len(events)} eventos encontrados")
            for ev in (events or [])[:3]:
                print(f"    {ev.get('dateEvent')} {ev.get('strHomeTeam')} {ev.get('intHomeScore')}-{ev.get('intAwayScore')} {ev.get('strAwayTeam')} status={ev.get('strStatus')}")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
