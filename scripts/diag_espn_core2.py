#!/usr/bin/env python
"""Diagnóstico temporal (2da vuelta): la primera pasada mostró que
sports.core.api.espn.com/.../events sin filtro solo trae un puñado de
eventos cercanos a hoy, no la temporada completa. Acá se imprime el objeto
liga completo (para ver qué sub-recursos trae, ej. seasons) y se prueba
pedir eventos por temporada/rango de fechas explícito.
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
    return r


print("=== objeto liga completo (arg.1) ===")
r = get(f"{BASE}/arg.1")
print(json.dumps(r.json(), indent=2)[:2000])

print("\n=== seasons de arg.1 ===")
r = get(f"{BASE}/arg.1/seasons")
data = r.json()
print(f"count={data.get('count')} items={len(data.get('items', []))}")
for it in data.get("items", [])[:5]:
    print(" ", it.get("$ref"))

print("\n=== detalle season 2026 (si existe) ===")
r = get(f"{BASE}/arg.1/seasons/2026")
print(f"status={r.status_code}")
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2)[:1500])

print("\n=== eventos de la season 2026 ===")
r = get(f"{BASE}/arg.1/seasons/2026/events", params={"limit": 1000})
print(f"status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"count={data.get('count')} pageCount={data.get('pageCount')} items={len(data.get('items', []))}")

print("\n=== events con parametro dates (rango amplio) ===")
r = get(f"{BASE}/arg.1/events", params={"dates": "20260101-20261231", "limit": 1000})
print(f"status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"count={data.get('count')} pageCount={data.get('pageCount')} items={len(data.get('items', []))}")
