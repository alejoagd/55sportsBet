#!/usr/bin/env python
"""Diagnóstico temporal (3ra vuelta): dereferencia un partido completo
(evento -> competición -> competidores -> equipo/marcador) para saber
cuántos pedidos hacen falta por partido y qué campos trae cada nivel.
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


# 1) un partido YA JUGADO (histórico), para ver cómo se ve el marcador final
events = get(f"{BASE}/arg.1/events?dates=20260201-20260228&limit=5")
ev_ref = events["items"][0]["$ref"]
print("=== evento (ya jugado, febrero) ===")
ev = get(ev_ref)
print(f"id={ev.get('id')} date={ev.get('date')} name={ev.get('name')}")

comp_ref = ev["competitions"][0]["$ref"] if isinstance(ev["competitions"][0], dict) and "$ref" in ev["competitions"][0] else None
print(f"\ncompetition ref: {comp_ref}")
comp = get(comp_ref) if comp_ref else ev["competitions"][0]
print("competition keys:", list(comp.keys()))

competitors = comp.get("competitors", [])
print(f"\n{len(competitors)} competitors")
for c in competitors:
    print(json.dumps(c, indent=2)[:800])
    print("---")

status_ref = comp.get("status", {}).get("$ref") if isinstance(comp.get("status"), dict) else None
if status_ref:
    print("\nstatus dereferenced:")
    print(json.dumps(get(status_ref), indent=2)[:600])
