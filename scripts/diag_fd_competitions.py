#!/usr/bin/env python
"""Diagnóstico temporal: lista todas las competencias de football-data.org
y su plan, para ver si alguna de las 5 que ESPN bloqueó (Brasileirao, Liga
Argentina, Liga Betplay, Copa Libertadores, Copa Sudamericana) está
disponible en el plan free que ya tenemos."""
import os
import requests

API_KEY = os.environ["FOOTBALL_DATA_ORG_KEY"]
resp = requests.get(
    "https://api.football-data.org/v4/competitions",
    headers={"X-Auth-Token": API_KEY},
    timeout=30,
)
resp.raise_for_status()
data = resp.json()
for c in data.get("competitions", []):
    name = c.get("name")
    area = (c.get("area") or {}).get("name")
    plan = c.get("plan")
    code = c.get("code")
    cid = c.get("id")
    print(f"{plan:<12} id={cid:<6} code={code:<6} {area:<20} {name}")
