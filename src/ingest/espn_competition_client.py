# src/ingest/espn_competition_client.py
"""
Cliente ESPN genérico (sin autenticación, público) para la temporada EN CURSO
de cualquier competencia de fútbol identificada por su "slug" de ESPN.

Mismo mecanismo que ya usa seed_wc2026_r32_schedule.py para el Mundial, pero
parametrizado por slug en vez de hardcodeado a "fifa.world", y usado aquí para
las 5 competencias nuevas:
  Brasileirao          -> bra.1
  Liga Argentina       -> arg.1
  Liga Betplay         -> col.1
  Copa Libertadores    -> conmebol.libertadores
  Copa Sudamericana    -> conmebol.sudamericana

A diferencia del Mundial (donde ESPN/los CSVs de origen nunca decían la ronda
real de cada partido knockout, obligando a adivinar la topología del bracket
en el frontend), estas competencias CONMEBOL sí traen `series.title` por
partido (ej. "Round of 16") y el endpoint de standings ya devuelve los grupos
armados (`children[].name = "Group A"`) — confirmado en vivo el 2026-07-24.
"""
from __future__ import annotations
import time
from datetime import date, timedelta
import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_BASE = "https://site.api.espn.com/apis/v2/sports/soccer"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _extract_fixture(ev: dict) -> dict | None:
    comps = ev.get("competitions", [])
    if not comps:
        return None
    comp = comps[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    status = comp.get("status", {}).get("type", {})
    status_short = status.get("name", "")  # STATUS_SCHEDULED / STATUS_FINAL / STATUS_IN_PROGRESS
    is_final = status.get("completed", False)

    home_goals = away_goals = None
    if is_final:
        try:
            home_goals = int(home.get("score"))
            away_goals = int(away.get("score"))
        except (TypeError, ValueError):
            pass

    series = comp.get("series") or {}
    round_label = series.get("title")
    if not round_label:
        season_slug = ev.get("season", {}).get("slug", "")
        round_label = season_slug.replace("-", " ").title() if season_slug else None

    raw_date = comp.get("date") or ev.get("date") or ""
    match_date = raw_date.split("T")[0] if raw_date else None

    return {
        "espn_event_id": int(ev.get("id")),
        "date": match_date,
        "home_espn_id": int(home["team"]["id"]),
        "home_name": home["team"].get("displayName", ""),
        "away_espn_id": int(away["team"]["id"]),
        "away_name": away["team"].get("displayName", ""),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status_short": status_short,
        "is_final": is_final,
        "round_label": round_label,
    }


def fetch_scoreboard_for_date(slug: str, day: date) -> list[dict]:
    """Fixtures de una competencia en una fecha específica (formato ESPN: YYYYMMDD)."""
    events = None
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(
                f"{BASE}/{slug}/scoreboard",
                headers=HEADERS,
                params={"dates": day.strftime("%Y%m%d")},
                timeout=20,
            )
            resp.raise_for_status()
            events = resp.json().get("events", [])
            break
        except Exception as e:
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    if events is None:
        print(f"   ⚠️  ESPN error ({slug}, {day.isoformat()}) tras reintentos: {last_exc}")
        return []

    fixtures = []
    for ev in events:
        fx = _extract_fixture(ev)
        if fx:
            fixtures.append(fx)
    return fixtures


def fetch_scoreboard_range(slug: str, start: date, end: date, sleep_s: float = 0.25) -> list[dict]:
    """Recorre día a día [start, end] y deduplica por espn_event_id."""
    seen: dict[int, dict] = {}
    d = start
    while d <= end:
        for fx in fetch_scoreboard_for_date(slug, d):
            seen[fx["espn_event_id"]] = fx
        d += timedelta(days=1)
        time.sleep(sleep_s)
    return list(seen.values())


def fetch_groups(slug: str) -> dict[int, str]:
    """{espn_team_id: 'Group A'} para competencias con fase de grupos.
    Retorna {} si la competencia no tiene grupos (ligas regulares) o si
    el endpoint aún no publica standings (antes de que arranque la fase de grupos)."""
    try:
        resp = requests.get(f"{STANDINGS_BASE}/{slug}/standings", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"   ⚠️  ESPN standings error ({slug}): {e}")
        return {}

    groups: dict[int, str] = {}
    for child in data.get("children", []):
        group_name = child.get("name") or child.get("abbreviation")
        entries = (child.get("standings") or {}).get("entries", [])
        for entry in entries:
            team_id = entry.get("team", {}).get("id")
            if team_id and group_name:
                groups[int(team_id)] = group_name
    return groups
