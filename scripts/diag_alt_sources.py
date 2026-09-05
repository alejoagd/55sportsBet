#!/usr/bin/env python
"""Diagnóstico temporal: prueba 2 candidatos más como alternativa a ESPN
(site.api.espn.com, bloqueado desde 2026-08-04) para Liga Argentina, Liga
Betplay, Copa Libertadores y Copa Sudamericana:

1. sports.core.api.espn.com — una superficie de API distinta de la misma
   ESPN (usada por sus propias apps para detalles de evento/liga), separada
   de site.api.espn.com que es la que está bloqueada. Vale la pena probar
   si el bloqueo es específico de ese subdominio o de todo ESPN.
2. Wikipedia (API pública oficial, sin autenticación) — las páginas de
   "temporada actual" de estas 4 competencias suelen tener tablas de
   resultados/calendario mantenidas al día por editores.
"""
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

print("=== 1) sports.core.api.espn.com ===")
# leagues catalog endpoint, liviano, para ver si responde en absoluto
try:
    r = requests.get(
        "https://sports.core.api.espn.com/v2/sports/soccer/leagues/arg.1",
        headers=HEADERS, timeout=20,
    )
    print(f"  GET leagues/arg.1 -> {r.status_code}")
    if r.status_code == 200:
        print(f"  {str(r.json())[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

try:
    r = requests.get(
        "https://sports.core.api.espn.com/v2/sports/soccer/leagues/arg.1/events",
        params={"limit": 5}, headers=HEADERS, timeout=20,
    )
    print(f"  GET leagues/arg.1/events -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  count={data.get('count')} pageCount={data.get('pageCount')}")
except Exception as e:
    print(f"  ERROR: {e}")


print("\n=== 2) Wikipedia API ===")
WIKI_PAGES = [
    "2026 Argentine Primera División season",
    "2026 Categoría Primera A season",
    "2026 Copa Libertadores",
    "2026 Copa Sudamericana",
]
for title in WIKI_PAGES:
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "titles": title, "prop": "revisions",
                "rvprop": "content", "rvslots": "main", "format": "json",
                "formatversion": "2",
            },
            headers=HEADERS, timeout=20,
        )
        print(f"  GET query title='{title}' -> {r.status_code}")
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", [])
            if pages and not pages[0].get("missing"):
                content = pages[0]["revisions"][0]["slots"]["main"]["content"]
                print(f"    encontrada, {len(content)} caracteres de wikitext")
                # Buscar si trae una tabla de resultados (heurística simple)
                has_results = "wikitable" in content and ("Results" in content or "results" in content)
                print(f"    parece tener tabla de resultados: {has_results}")
            else:
                print("    página no encontrada con ese título exacto")
    except Exception as e:
        print(f"  ERROR: {e}")
