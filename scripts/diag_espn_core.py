#!/usr/bin/env python
"""Diagnóstico temporal: profundiza en sports.core.api.espn.com (no
bloqueado, a diferencia de site.api.espn.com) para las 4 competencias que
necesitamos. Revisa: paginación completa de eventos, y el detalle de un
evento individual (fecha, equipos, marcador) para confirmar que trae todo
lo necesario para reemplazar al sync actual.
"""
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}
BASE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"

SLUGS = {
    "Liga Argentina": "arg.1",
    "Liga Betplay": "col.1",
    "Copa Libertadores": "conmebol.libertadores",
    "Copa Sudamericana": "conmebol.sudamericana",
}


def main():
    for name, slug in SLUGS.items():
        print(f"\n=== {name} ({slug}) ===")
        try:
            r = requests.get(f"{BASE}/{slug}/events", params={"limit": 1000}, headers=HEADERS, timeout=30)
            print(f"  GET events?limit=1000 -> {r.status_code}")
            if r.status_code != 200:
                print(f"  body: {r.text[:200]}")
                continue
            data = r.json()
            items = data.get("items", [])
            print(f"  count={data.get('count')} pageCount={data.get('pageCount')} items_devueltos={len(items)}")

            if not items:
                continue

            # Traer el detalle del primer y último evento de la lista
            for label, ev_ref in [("primero", items[0]), ("ultimo", items[-1])]:
                ref_url = ev_ref["$ref"]
                er = requests.get(ref_url, headers=HEADERS, timeout=20)
                if er.status_code != 200:
                    print(f"  [{label}] detalle -> {er.status_code}")
                    continue
                ev = er.json()
                print(f"  [{label}] id={ev.get('id')} date={ev.get('date')} name={ev.get('name')}")
                comps = ev.get("competitions", [])
                if comps:
                    comp = comps[0]
                    comp_ref_url = comp.get("$ref") if isinstance(comp, dict) and "$ref" in comp else None
                    if comp_ref_url:
                        cr = requests.get(comp_ref_url, headers=HEADERS, timeout=20)
                        comp = cr.json() if cr.status_code == 200 else {}
                    competitors = comp.get("competitors", [])
                    print(f"       competitors: {len(competitors)}  status={comp.get('status')}")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
