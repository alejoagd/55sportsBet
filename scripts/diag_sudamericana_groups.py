#!/usr/bin/env python
"""Diagnóstico temporal: ver si los partidos de fase de grupos de Copa
Sudamericana realmente comparten el mismo group id, o si cada uno tiene un
id distinto que casualmente comparte el mismo texto en 'name'."""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/conmebol.sudamericana"

for event_id in [401865384, 401865374, 401865380]:
    comp = requests.get(f"{BASE}/events/{event_id}/competitions/{event_id}", headers=HEADERS, timeout=20).json()
    groups_ref = comp.get("groups", {}).get("$ref")
    print(f"event {event_id}: groups ref = {groups_ref}")
    if groups_ref:
        g = requests.get(groups_ref, headers=HEADERS, timeout=20).json()
        print(f"   id={g.get('id')} name={g.get('name')!r} abbreviation={g.get('abbreviation')!r}")
