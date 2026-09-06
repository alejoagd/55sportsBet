#!/usr/bin/env python
"""Diagnóstico temporal: busca dónde vive el nombre real de cada fase
(fase de grupos, octavos, cuartos, etc.) en sports.core.api.espn.com para
Copa Libertadores/Sudamericana. La ronda de un partido individual (notes)
solo trae "1st Leg"/"2nd Leg", no el nombre de la fase — se busca acá si
la temporada trae un calendario de fases con rango de fechas, y qué trae
dereferenciar el "groups" de un partido de fase de grupos vs uno de octavos.
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


def get(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


print("=== season 2026 completo (conmebol.libertadores) ===")
season = get(f"{BASE}/conmebol.libertadores/seasons/2026")
print(json.dumps(season, indent=2)[:3000])

print("\n=== types de la season (fases del torneo) ===")
types = get(f"{BASE}/conmebol.libertadores/seasons/2026/types")
print(f"count={types.get('count')}")
for it in types.get("items", []):
    ref = it.get("$ref")
    detail = get(ref)
    print(f"  id={detail.get('id')} name={detail.get('name')} slug={detail.get('slug')} start={detail.get('startDate')} end={detail.get('endDate')} hasGroups={detail.get('hasGroups')}")

print("\n=== dereferenciar 'groups' de un partido de fase de grupos (feb) ===")
events = get(f"{BASE}/conmebol.libertadores/events?dates=20260201-20260228&limit=3")
ev = get(events["items"][0]["$ref"])
comp = get(ev["competitions"][0]["$ref"])
if comp.get("groups"):
    group_detail = get(comp["groups"]["$ref"])
    print(json.dumps(group_detail, indent=2)[:1200])

print("\n=== dereferenciar 'groups' de un partido de knockout (septiembre) ===")
events2 = get(f"{BASE}/conmebol.libertadores/events?dates=20260901-20260930&limit=3")
ev2 = get(events2["items"][0]["$ref"])
print(f"evento: {ev2.get('name')} date={ev2.get('date')}")
comp2 = get(ev2["competitions"][0]["$ref"])
print("notes:", comp2.get("notes"))
if comp2.get("groups"):
    group_detail2 = get(comp2["groups"]["$ref"])
    print(json.dumps(group_detail2, indent=2)[:1200])
else:
    print("sin 'groups' en este partido")
