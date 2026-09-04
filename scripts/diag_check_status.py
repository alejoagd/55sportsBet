#!/usr/bin/env python
"""Diagnóstico temporal: imprime el status/utcDate crudo de football-data.org
para los partidos de La Liga y Serie A de hoy, para confirmar si la API ya
confirmó la hora (TIMED) o sigue en SCHEDULED. Ver conversación sobre
'Hora por confirmar' en La Liga/Serie A pese a ser partidos de hoy.
"""
import os
import requests

API_KEY = os.environ["FOOTBALL_DATA_ORG_KEY"]
HEADERS = {"X-Auth-Token": API_KEY}

for name, comp_id in [("La Liga", 2014), ("Serie A", 2019)]:
    url = f"https://api.football-data.org/v4/competitions/{comp_id}/matches"
    resp = requests.get(url, headers=HEADERS, params={"status": "SCHEDULED,TIMED"}, timeout=30)
    resp.raise_for_status()
    matches = resp.json().get("matches", [])
    print(f"\n=== {name}: {len(matches)} partidos SCHEDULED/TIMED ===")
    for m in matches[:8]:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        print(f"  {m['utcDate']}  status={m['status']:<10} {home} vs {away}")
