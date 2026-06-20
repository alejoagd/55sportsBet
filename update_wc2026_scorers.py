"""
update_wc2026_scorers.py
Descarga anotadores del Mundial 2026 desde martj42/international_results
y enriquece con asistidores desde ESPN (misma fuente que match stats).

FUENTES:
  1. martj42 goalscorers.csv  — anotador, minuto, autogol, penal
  2. ESPN summary?event={id}  — asistidor (via scoringPlays.participants)

Uso:
  python update_wc2026_scorers.py
  python update_wc2026_scorers.py --dry-run
"""
from __future__ import annotations
import sys
import io
import csv
import time
import requests
from collections import defaultdict
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76
WC_START_DATE     = "2026-06-11"
WC_END_DATE       = "2026-07-19"

GOALSCORERS_CSV_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/goalscorers.csv"
)
ESPN_BASE   = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUE = "fifa.world"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ── Normalización de nombres (igual que los otros scripts) ────────────────────
CSV_TO_DB: dict[str, str] = {
    "Bosnia-Herzegovina":               "Bosnia and Herzegovina",
    "Bosnia and Herzegovina":           "Bosnia and Herzegovina",
    "Czech Republic":                   "Czechia",
    "Czechia":                          "Czechia",
    "Côte d'Ivoire":                    "Ivory Coast",
    "Cote d'Ivoire":                    "Ivory Coast",
    "Ivory Coast":                      "Ivory Coast",
    "DR Congo":                         "Congo DR",
    "Congo DR":                         "Congo DR",
    "Democratic Republic of the Congo": "Congo DR",
    "Cabo Verde":                       "Cape Verde",
    "Cape Verde":                       "Cape Verde",
    "Korea Republic":                   "South Korea",
    "South Korea":                      "South Korea",
    "IR Iran":                          "Iran",
    "USA":                              "United States",
    "United States":                    "United States",
    "Curaçao":                     "Curacao",
    "CuraÇao":                     "Curacao",
}
_PASSTHROUGH = {
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Paraguay",
    "France", "England", "Belgium", "Portugal", "Spain", "Netherlands",
    "Germany", "Croatia", "Switzerland", "Norway", "Turkey", "Scotland",
    "Austria", "Sweden", "Morocco", "Senegal", "Algeria", "Tunisia",
    "Egypt", "Ghana", "South Africa", "Japan", "Australia", "Iran",
    "Saudi Arabia", "Qatar", "Uzbekistan", "Jordan", "Iraq",
    "Mexico", "Canada", "Panama", "Haiti", "Curacao", "New Zealand",
}


def normalize(name: str) -> str | None:
    if name in CSV_TO_DB:
        return CSV_TO_DB[name]
    if name in _PASSTHROUGH:
        return name
    return None


# ── Tablas ────────────────────────────────────────────────────────────────────

def ensure_tables(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS wc_scoring_events (
            id            SERIAL PRIMARY KEY,
            match_id      INTEGER REFERENCES matches(id),
            team          TEXT NOT NULL,
            player_name   TEXT NOT NULL,
            minute        INTEGER,
            is_own_goal   BOOLEAN DEFAULT FALSE,
            is_penalty    BOOLEAN DEFAULT FALSE,
            assist_player TEXT,
            source        TEXT DEFAULT 'martj42',
            UNIQUE(match_id, team, player_name, minute)
        )
    """))
    # Columna assist_player por si la tabla existía antes sin ella
    conn.execute(text(
        "ALTER TABLE wc_scoring_events ADD COLUMN IF NOT EXISTS assist_player TEXT"
    ))


# ── martj42: anotadores ───────────────────────────────────────────────────────

def fetch_scorers_csv() -> list[dict]:
    """Descarga goalscorers.csv y filtra entradas del Mundial 2026."""
    print("📥 Descargando goalscorers.csv desde GitHub...")
    resp = requests.get(GOALSCORERS_CSV_URL, timeout=60)
    resp.raise_for_status()
    print(f"   {len(resp.content) // 1024} KB descargados")

    reader = csv.DictReader(io.StringIO(resp.text))
    events: list[dict] = []

    for row in reader:
        date = row.get("date", "")
        if not (WC_START_DATE <= date <= WC_END_DATE):
            continue

        home_csv = row.get("home_team", "").strip()
        away_csv = row.get("away_team", "").strip()
        team_csv = row.get("team", "").strip()
        scorer   = row.get("scorer", "").strip()

        if not scorer:
            continue

        home_db = normalize(home_csv)
        away_db = normalize(away_csv)
        team_db = normalize(team_csv)
        if not home_db or not away_db or not team_db:
            print(f"   ⚠️  Nombre no mapeado: {home_csv} vs {away_csv} ({team_csv})")
            continue

        minute_raw = row.get("minute", "").strip()
        try:
            minute = int(float(minute_raw)) if minute_raw else None
        except (ValueError, TypeError):
            minute = None

        is_og  = row.get("own_goal", "FALSE").upper().strip() == "TRUE"
        is_pen = row.get("penalty",  "FALSE").upper().strip() == "TRUE"

        events.append({
            "date":       date,
            "home_team":  home_db,
            "away_team":  away_db,
            "team":       team_db,
            "player_name": scorer,
            "minute":     minute,
            "is_own_goal": is_og,
            "is_penalty":  is_pen,
        })

    print(f"   Eventos WC 2026 en CSV: {len(events)}")
    return events


# ── ESPN: asistidores ─────────────────────────────────────────────────────────

def fetch_espn_assists(espn_event_id: int) -> dict[int, str]:
    """
    Devuelve {minute: assister_name} desde ESPN match summary.
    Intenta 'scoringPlays' primero, luego 'keyEvents'.
    """
    url = f"{ESPN_BASE}/{ESPN_LEAGUE}/summary"
    try:
        resp = requests.get(url, headers=HEADERS, params={"event": espn_event_id}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    assists: dict[int, str] = {}

    def _parse_plays(plays: list, minute_field: str = "clock") -> None:
        for play in plays:
            participants = play.get("participants", [])
            if len(participants) < 2:
                continue
            assister = participants[1].get("athlete", {}).get("displayName", "")
            if not assister:
                continue
            clock_val = play.get(minute_field, {}).get("value")
            if clock_val is not None:
                try:
                    # ESPN clock puede ser segundos o minutos; normalizar
                    val = float(clock_val)
                    minute = int(val / 60) if val > 120 else int(val)
                    assists[minute] = assister
                except (ValueError, TypeError):
                    pass

    _parse_plays(data.get("scoringPlays", []))
    if not assists:
        _parse_plays(data.get("keyEvents", []))

    return assists


# ── Almacenar en BD ───────────────────────────────────────────────────────────

def store_scorers(conn, events: list[dict], dry_run: bool = False) -> int:
    # Obtener partidos WC completados con su ESPN ID
    matches_rows = conn.execute(text("""
        SELECT m.id AS match_id, m.date::text, m.sofascore_id,
               th.name AS home_team, ta.name AS away_team
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id = :sid AND m.home_goals IS NOT NULL
    """), {"sid": WC_2026_SEASON_ID}).fetchall()

    match_lookup: dict[tuple, tuple] = {}
    for row in matches_rows:
        key = (row.date, row.home_team, row.away_team)
        match_lookup[key] = (row.match_id, row.sofascore_id)

    # Eventos ya almacenados para no duplicar
    existing: set[tuple] = set()
    for row in conn.execute(text(
        "SELECT match_id, player_name, minute FROM wc_scoring_events"
    )).fetchall():
        existing.add((row.match_id, row.player_name, row.minute))

    # Agrupar eventos CSV por partido
    by_match: dict[tuple, list[dict]] = defaultdict(list)
    for ev in events:
        key  = (ev["date"], ev["home_team"], ev["away_team"])
        rkey = (ev["date"], ev["away_team"], ev["home_team"])  # autogoles pueden invertir
        if key in match_lookup:
            by_match[key].append(ev)
        elif rkey in match_lookup:
            by_match[rkey].append(ev)

    # Partidos en CSV sin match en BD
    unmapped = sum(
        1 for ev in events
        if (ev["date"], ev["home_team"], ev["away_team"]) not in match_lookup
        and (ev["date"], ev["away_team"], ev["home_team"]) not in match_lookup
    )
    if unmapped:
        print(f"   ⚠️  {unmapped} evento(s) sin partido en BD — puede ser fecha sin resultados aún")

    inserted = 0
    for match_key, match_events in by_match.items():
        match_id, espn_id = match_lookup[match_key]

        # Intentar conseguir asistidores desde ESPN
        assists_by_min: dict[int, str] = {}
        if espn_id:
            assists_by_min = fetch_espn_assists(int(espn_id))
            time.sleep(0.25)

        for ev in match_events:
            key3 = (match_id, ev["player_name"], ev["minute"])
            if key3 in existing:
                continue

            assist = assists_by_min.get(ev["minute"]) if ev["minute"] is not None else None

            goal_type = " (OG)" if ev["is_own_goal"] else " (P)" if ev["is_penalty"] else ""
            assist_str = f" → 🎯 {assist}" if assist else ""
            label = "[DRY]" if dry_run else "⚽"
            print(f"   {label} {ev['team']} — {ev['player_name']}{goal_type} {ev['minute']}'{assist_str}")

            if not dry_run:
                conn.execute(text("""
                    INSERT INTO wc_scoring_events
                        (match_id, team, player_name, minute,
                         is_own_goal, is_penalty, assist_player)
                    VALUES
                        (:match_id, :team, :player_name, :minute,
                         :is_own_goal, :is_penalty, :assist_player)
                    ON CONFLICT (match_id, team, player_name, minute) DO UPDATE SET
                        assist_player = COALESCE(EXCLUDED.assist_player, wc_scoring_events.assist_player),
                        is_own_goal   = EXCLUDED.is_own_goal,
                        is_penalty    = EXCLUDED.is_penalty
                """), {
                    "match_id":     match_id,
                    "team":         ev["team"],
                    "player_name":  ev["player_name"],
                    "minute":       ev["minute"],
                    "is_own_goal":  ev["is_own_goal"],
                    "is_penalty":   ev["is_penalty"],
                    "assist_player": assist,
                })
                existing.add(key3)
                inserted += 1

    return inserted


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "ACTUALIZANDO BD"
    print("=" * 60)
    print(f"  WC 2026 Scorers Updater — {mode}")
    print("=" * 60)

    with engine.begin() as conn:
        print("\n🔧 Verificando tablas...")
        ensure_tables(conn)
        print("   ✓ OK")

        print("\n⚽ Descargando anotadores...")
        events = fetch_scorers_csv()

        print(f"\n💾 Almacenando en BD...")
        inserted = store_scorers(conn, events, dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Eventos nuevos insertados : {inserted}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
