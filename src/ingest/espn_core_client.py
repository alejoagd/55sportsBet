# src/ingest/espn_core_client.py
"""
Cliente para sports.core.api.espn.com — superficie de API de ESPN DISTINTA
de site.api.espn.com (la que usa espn_competition_client.py), que devuelve
403 Forbidden en el 100% de los pedidos desde GitHub Actions desde
2026-08-04 (confirmado con ~450 pedidos reales en una corrida, y de nuevo
en el sync automático que corre a diario). Esta superficie (usada por las
apps oficiales de ESPN) SÍ responde 200 con los mismos datos.

Diferencia clave de diseño: site.api.espn.com devuelve cada fixture con
todo embebido en una sola respuesta (fecha, equipos, marcador, ronda). Esta
API es "por niveles" (hypermedia, cada campo es un {"$ref": ...} a
dereferenciar): evento -> competición -> {equipo, marcador} por cada lado
-> estado. El nombre/escudo de cada equipo se cachea en memoria durante la
corrida para no repetir el pedido una vez ya visto.

Ronda/grupo real (para las copas): el partido individual NO trae el nombre
de la ronda (`notes` solo da "1st Leg"/"2nd Leg"). Sí lo trae la TEMPORADA:
`seasons/{year}/types` devuelve las fases del torneo con nombre y rango de
fechas exacto (ej. "Group Stage" 2026-03-14→2026-05-30, "Round of 16"
2026-05-30→2026-08-22, etc. — confirmado en vivo para Libertadores/
Sudamericana). Se piden una sola vez por temporada (barato) y cada partido
se ubica en su fase por fecha, sin pedidos extra — solo cuando la fase
tiene fase de grupos (`hasGroups`) se dereferencia el grupo del partido
(`competition.groups`) para el nombre real (ej. "Group 1").

Expone las mismas 2 funciones que espn_competition_client.py
(fetch_scoreboard_range, fetch_groups) con la misma forma de retorno, más
"group_name" embebido en cada fixture, para poder usarse como reemplazo
directo en update_competitions_espn_sync.py.
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


class _GroupCache:
    """Evita re-dereferenciar el mismo grupo (ej. 'Group 1') repetidas veces."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def get(self, group_ref: str) -> str | None:
        if group_ref not in self._cache:
            data = _get_json(group_ref) or {}
            self._cache[group_ref] = data.get("name")
        return self._cache[group_ref]


def _fetch_season_phases(slug: str, year: int) -> list[dict]:
    """Fases de la temporada (nombre + rango de fechas + si tiene grupos),
    ordenadas cronológicamente. [] si la competencia no publica fases
    (ligas regulares tipo Liga Argentina/Betplay no las tienen)."""
    data = _get_json(f"{BASE}/{slug}/seasons/{year}/types")
    if not data:
        return []
    phases = []
    for item in data.get("items", []):
        ref = item.get("$ref")
        if not ref:
            continue
        detail = _get_json(ref)
        if not detail or not detail.get("startDate") or not detail.get("endDate"):
            continue
        phases.append({
            "name": detail.get("name"),
            "start": datetime.fromisoformat(detail["startDate"].replace("Z", "+00:00")),
            "end": datetime.fromisoformat(detail["endDate"].replace("Z", "+00:00")),
            "has_groups": bool(detail.get("hasGroups")),
        })
    phases.sort(key=lambda p: p["start"])
    return phases


def _phase_for(phases: list[dict], kickoff_at: datetime | None) -> dict | None:
    if not kickoff_at:
        return None
    for p in phases:
        if p["start"] <= kickoff_at <= p["end"]:
            return p
    return None


def _extract_event(event_ref: str, team_cache: _TeamCache, group_cache: _GroupCache, phases: list[dict]) -> dict | None:
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

    raw_date = ev.get("date") or comp.get("date") or ""
    kickoff_at = None
    match_date = None
    if raw_date:
        kickoff_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        match_date = kickoff_at.date()

    # Ronda real: la fase de la temporada en la que cae la fecha del
    # partido (ej. "Group Stage", "Round of 16") — mucho más preciso que
    # el "1st Leg"/"2nd Leg" que trae el partido individual.
    phase = _phase_for(phases, kickoff_at)
    round_label = phase["name"] if phase else None

    group_name = None
    if phase and phase["has_groups"] and comp.get("groups", {}).get("$ref"):
        group_name = group_cache.get(comp["groups"]["$ref"])

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
        "group_name": group_name,
    }


def fetch_scoreboard_range(slug: str, start: date, end: date) -> list[dict]:
    """Misma firma/forma de retorno que espn_competition_client.fetch_scoreboard_range
    (más "group_name" embebido), pero contra sports.core.api.espn.com (no bloqueado)."""
    date_param = f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    data = _get_json(f"{BASE}/{slug}/events", params={"dates": date_param, "limit": 1000})
    if not data:
        return []

    # Fases de la(s) temporada(s) que cubre el rango pedido — casi siempre
    # un solo año, pero un rango que cruza fin de año pide ambas.
    phases: list[dict] = []
    for year in {start.year, end.year}:
        phases.extend(_fetch_season_phases(slug, year))

    items = data.get("items", [])
    team_cache = _TeamCache()
    group_cache = _GroupCache()
    fixtures = []
    for item in items:
        ref = item.get("$ref")
        if not ref:
            continue
        fx = _extract_event(ref, team_cache, group_cache, phases)
        if fx:
            fixtures.append(fx)
    return fixtures


def fetch_groups(slug: str) -> dict[int, str]:
    """No usada por las competencias actuales: el grupo ya viene embebido
    por partido en fetch_scoreboard_range (ver "group_name"). Se mantiene
    solo para conservar la misma firma que espn_competition_client.py."""
    return {}
