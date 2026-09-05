# src/ingest/espn_core_client.py
"""
Cliente para sports.core.api.espn.com — superficie de API de ESPN DISTINTA
de site.api.espn.com (la que usa espn_competition_client.py), que devuelve
403 Forbidden en el 100% de los pedidos desde GitHub Actions desde
2026-08-04 (confirmado con ~450 pedidos reales en una corrida, y de nuevo
en el sync automático que corre a diario). Esta superficie (usada por las
apps oficiales de ESPN) SÍ responde 200 con los mismos datos.

Diferencia clave de diseño: site.api.espn.com devuelve cada fixture con
todo embebido en una sola respuesta (fecha, equipos, marcador). Esta API es
"por niveles" (hypermedia, cada campo es un {"$ref": ...} a dereferenciar):
evento -> competición -> {equipo, marcador} por cada lado -> estado. Eso
significa más pedidos por partido (hasta 6: evento, competición, status, y
equipo+marcador por cada uno de los 2 competidores) — el nombre/escudo de
cada equipo se cachea en memoria durante la corrida para no repetir el
pedido una vez ya visto.

Expone las mismas 2 funciones que espn_competition_client.py
(fetch_scoreboard_range, fetch_groups) con la misma forma de retorno, para
poder usarse como reemplazo directo en update_competitions_espn_sync.py.
"""
from __future__ import annotations
import time
from datetime import date, datetime
import requests

BASE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _get_json(url: str, params: dict | None = None) -> dict | None:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_exc = e
            time.sleep(1.0 * (attempt + 1))
    print(f"   ⚠️  ESPN core API error ({url}) tras reintentos: {last_exc}")
    return None


class _TeamCache:
    """Evita re-dereferenciar el mismo equipo en cada partido de la corrida."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def get(self, team_ref: str) -> dict:
        if team_ref not in self._cache:
            data = _get_json(team_ref) or {}
            logo = data.get("logo")
            if not logo:
                logos = data.get("logos") or []
                logo = logos[0].get("href") if logos else None
            self._cache[team_ref] = {
                "id": int(data.get("id")) if data.get("id") else None,
                "name": data.get("displayName") or data.get("name") or "",
                "logo": logo,
            }
        return self._cache[team_ref]


def _extract_event(event_ref: str, team_cache: _TeamCache) -> dict | None:
    ev = _get_json(event_ref)
    if not ev or not ev.get("competitions"):
        return None

    comp_entry = ev["competitions"][0]
    comp_ref = comp_entry.get("$ref") if isinstance(comp_entry, dict) else None
    comp = _get_json(comp_ref) if comp_ref else comp_entry
    if not comp:
        return None

    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    home_team = team_cache.get(home["team"]["$ref"])
    away_team = team_cache.get(away["team"]["$ref"])
    if not home_team.get("id") or not away_team.get("id"):
        return None

    status_ref = comp.get("status", {}).get("$ref") if isinstance(comp.get("status"), dict) else None
    status = _get_json(status_ref) if status_ref else (comp.get("status") or {})
    status_type = (status or {}).get("type", {})
    is_final = bool(status_type.get("completed"))
    status_short = status_type.get("name", "")

    home_goals = away_goals = None
    if is_final:
        home_score = _get_json(home["score"]["$ref"]) if "score" in home else None
        away_score = _get_json(away["score"]["$ref"]) if "score" in away else None
        try:
            home_goals = int(float(home_score.get("value"))) if home_score else None
            away_goals = int(float(away_score.get("value"))) if away_score else None
        except (TypeError, ValueError):
            pass

    notes = comp.get("notes") or []
    round_label = notes[0].get("headline") if notes else None

    raw_date = ev.get("date") or comp.get("date") or ""
    kickoff_at = None
    match_date = None
    if raw_date:
        kickoff_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        match_date = kickoff_at.date()

    return {
        "espn_event_id": int(ev.get("id")),
        "date": match_date,
        "kickoff_at": kickoff_at,
        "home_espn_id": home_team["id"],
        "home_name": home_team["name"],
        "home_logo": home_team.get("logo"),
        "away_espn_id": away_team["id"],
        "away_name": away_team["name"],
        "away_logo": away_team.get("logo"),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status_short": status_short,
        "is_final": is_final,
        "round_label": round_label,
    }


def fetch_scoreboard_range(slug: str, start: date, end: date) -> list[dict]:
    """Misma firma/forma de retorno que espn_competition_client.fetch_scoreboard_range,
    pero contra sports.core.api.espn.com (no bloqueado)."""
    date_param = f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    data = _get_json(f"{BASE}/{slug}/events", params={"dates": date_param, "limit": 1000})
    if not data:
        return []

    items = data.get("items", [])
    team_cache = _TeamCache()
    fixtures = []
    for item in items:
        ref = item.get("$ref")
        if not ref:
            continue
        fx = _extract_event(ref, team_cache)
        if fx:
            fixtures.append(fx)
    return fixtures


def fetch_groups(slug: str) -> dict[int, str]:
    """Placeholder — de las 4 competencias migradas a esta API, ninguna
    depende hoy de group_name real (Liga Argentina/Betplay son tabla única
    en la fase actual; Libertadores/Sudamericana usan round_label vía
    map_stage). Retorna {} igual que espn_competition_client.fetch_groups
    cuando la competencia no tiene grupos, para mantener la misma firma."""
    return {}
