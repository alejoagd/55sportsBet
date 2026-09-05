#!/usr/bin/env python
"""Diagnóstico temporal (4ta vuelta): revisa 'notes'/'groups' de una
competición de copa (Libertadores) para ver si la ronda viene embebida sin
pedidos extra, y confirma el marcador final dereferenciando score.
"""
import json
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}
BASE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


events = get(f"{BASE}/conmebol.libertadores/events?dates=20260201-20260331&limit=5")
print(f"eventos encontrados: {events.get('count')}")
if events["items"]:
    ev = get(events["items"][0]["$ref"])
    print(f"evento: {ev.get('name')} date={ev.get('date')}")
    comp = get(ev["competitions"][0]["$ref"])
    print("\nnotes:", json.dumps(comp.get("notes"), indent=2))
    print("\ngroups:", json.dumps(comp.get("groups"), indent=2)[:500])

    # marcador final de un partido de esta copa
    for c in comp.get("competitors", []):
        score = get(c["score"]["$ref"])
        team = get(c["team"]["$ref"])
        print(f"  {team.get('displayName')} ({c.get('homeAway')}): score={score.get('value')} displayValue={score.get('displayValue')}")
