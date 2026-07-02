"""
update_wc2026_scorers.py
Descarga anotadores del Mundial 2026 desde martj42/international_results
y enriquece con asistidores desde FotMob (fuente primaria) o ESPN (fallback).

FUENTES:
  1. martj42 goalscorers.csv  — anotador, minuto, autogol, penal
  2. FotMob matchDetails       — asistidores (fuente primaria, más completa)
  3. ESPN summary?event={id}  — asistidor ESPN (fallback via scoringPlays)

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
ESPN_BASE        = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUE      = "fifa.world"
SOFASCORE_BASE   = "https://api.sofascore.com/api/v1"
SOFASCORE_WC_ID  = 16  # SofaScore tournament ID for FIFA World Cup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

SOFASCORE_HEADERS = {
    **HEADERS,
    "Referer": "https://www.sofascore.com/",
    "Origin":  "https://www.sofascore.com",
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
    conn.execute(text(
        "ALTER TABLE wc_scoring_events ADD COLUMN IF NOT EXISTS assist_player TEXT"
    ))
    # Tabla para totales acumulados de jugadores (de ESPN leaders)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS wc_player_stats (
            id          SERIAL PRIMARY KEY,
            player_name TEXT NOT NULL UNIQUE,
            team        TEXT,
            goals       INTEGER DEFAULT 0,
            assists     INTEGER DEFAULT 0,
            source      TEXT DEFAULT 'espn_leaders',
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """))


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

def fetch_espn_assists(espn_event_id: int) -> dict[int, list[str]]:
    """
    Devuelve {minute: [assister_name, ...]} desde ESPN match summary.
    Fuentes (en orden, se acumulan): scoringPlays, header.competitions.details, keyEvents.
    """
    url = f"{ESPN_BASE}/{ESPN_LEAGUE}/summary"
    try:
        resp = requests.get(url, headers=HEADERS, params={"event": espn_event_id}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    assists: dict[int, list[str]] = {}

    def _clock_to_min(play: dict) -> int | None:
        clock_val = play.get("clock", {}).get("value")
        if clock_val is not None:
            try:
                val = float(clock_val)
                return int(val / 60) if val > 120 else int(val)
            except (ValueError, TypeError):
                pass
        return None

    def _parse_plays(plays: list) -> None:
        """Parsea scoringPlays / keyEvents con campo 'participants'."""
        for play in plays:
            participants = play.get("participants", [])
            assister = None
            for p in participants:
                ptype = p.get("type", {}).get("text", "").lower()
                if "assist" in ptype:
                    assister = p.get("athlete", {}).get("displayName", "")
                    break
            if not assister and len(participants) >= 2:
                assister = participants[1].get("athlete", {}).get("displayName", "")
            if not assister:
                continue
            minute = _clock_to_min(play)
            if minute is not None:
                assists.setdefault(minute, []).append(assister)

    def _parse_details(details: list) -> None:
        """Parsea header.competitions[0].details con campo 'athletesInvolved'."""
        for detail in details:
            athletes = detail.get("athletesInvolved", [])
            assister = None
            for a in athletes:
                a_type = a.get("type", "").lower()
                if "assist" in a_type:
                    assister = a.get("displayName", "")
                    break
            if not assister and len(athletes) >= 2:
                assister = athletes[1].get("displayName", "")
            if not assister:
                continue
            minute = _clock_to_min(detail)
            if minute is not None and assister not in assists.get(minute, []):
                assists.setdefault(minute, []).append(assister)

    # 1) scoringPlays — fuente principal
    _parse_plays(data.get("scoringPlays", []))

    # 2) header.competitions[0].details — suele tener más cobertura de assists
    comps = data.get("header", {}).get("competitions", [])
    if comps:
        _parse_details(comps[0].get("details", []))

    # 3) keyEvents — fallback adicional
    _parse_plays(data.get("keyEvents", []))

    return assists


def fetch_espn_boxscore_assists(espn_event_id: int, debug: bool = False) -> dict[str, dict]:
    """
    Parsea el boxscore.players de ESPN para un partido específico.
    Retorna {player_name: {"team": team, "assists": n}} para jugadores con asistencias.
    """
    url = f"{ESPN_BASE}/{ESPN_LEAGUE}/summary"
    try:
        resp = requests.get(url, headers=HEADERS, params={"event": espn_event_id}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    result: dict[str, dict] = {}
    all_seen_keys: list[str] = []

    for team_block in data.get("boxscore", {}).get("players", []):
        team_name = team_block.get("team", {}).get("displayName", "")
        for stat_block in team_block.get("statistics", []):
            keys = stat_block.get("keys", [])
            all_seen_keys.extend(keys)
            # Búsqueda case-insensitive de cualquier key que contenga "assist"
            assists_idx = next(
                (i for i, k in enumerate(keys) if "assist" in k.lower()), None
            )
            if assists_idx is None:
                continue
            for athlete_entry in stat_block.get("athletes", []):
                player_name = athlete_entry.get("athlete", {}).get("displayName", "")
                stats = athlete_entry.get("stats", [])
                if not player_name or assists_idx >= len(stats):
                    continue
                try:
                    n = int(stats[assists_idx])
                except (ValueError, TypeError):
                    n = 0
                if n > 0:
                    result[player_name] = {"team": team_name, "assists": n}

    if debug:
        unique_keys = sorted(set(all_seen_keys))
        print(f"      [ESPN boxscore] event={espn_event_id} keys={unique_keys} assists_found={len(result)}")

    return result


def _fotmob_assist_name(ev: dict) -> str | None:
    """Extrae nombre del asistidor de un evento FotMob (prueba múltiples campos)."""
    # Intento 1: campo "assist" como dict o string
    assist_obj = ev.get("assist")
    if isinstance(assist_obj, dict):
        name = assist_obj.get("playerName") or assist_obj.get("name")
        if name:
            return name
    elif isinstance(assist_obj, str) and assist_obj:
        return assist_obj

    # Intento 2: campos directos alternativos
    for key in ("assistStr", "assistPlayerName", "assistedByPlayerName",
                "assist_player", "assistName"):
        val = ev.get(key)
        if val and isinstance(val, str):
            return val

    # Intento 3: campo "assistedBy" como dict
    ab = ev.get("assistedBy")
    if isinstance(ab, dict):
        return ab.get("playerName") or ab.get("name")

    return None


def fetch_fotmob_match_assists(date_str: str, home_team: str, away_team: str,
                               debug: bool = False) -> dict[str, dict]:
    """
    Obtiene asistidores de gol para un partido específico desde FotMob.
    FotMob tiene mejor cobertura de asistencias que ESPN para el Mundial.
    Retorna {player_name: {"team": team, "assists": count}}
    """
    compact = date_str.replace("-", "")
    try:
        data = requests.get(
            f"{FOTMOB_BASE}/matches", params={"date": compact},
            headers=HEADERS, timeout=20
        ).json()
    except Exception as e:
        if debug:
            print(f"      [FotMob] Error en /matches: {e}")
        return {}

    fotmob_id = None
    home_name_fm = away_name_fm = ""

    for league in data.get("leagues", []):
        lid  = league.get("id")
        name = league.get("name", "").lower()
        if "world cup" not in name and lid != FOTMOB_WC_ID:
            continue
        for match in league.get("matches", []):
            h_raw = match.get("home", {}).get("name", "")
            a_raw = match.get("away", {}).get("name", "")
            h_db  = normalize(h_raw) or h_raw
            a_db  = normalize(a_raw) or a_raw
            if h_db == home_team and a_db == away_team:
                fotmob_id    = match.get("id")
                home_name_fm = h_db
                away_name_fm = a_db
                break
        if fotmob_id:
            break

    if not fotmob_id:
        if debug:
            print(f"      [FotMob] Partido no encontrado: {home_team} vs {away_team} ({date_str})")
        return {}

    try:
        detail = requests.get(
            f"{FOTMOB_BASE}/matchDetails", params={"matchId": fotmob_id},
            headers=HEADERS, timeout=20
        ).json()
    except Exception as e:
        if debug:
            print(f"      [FotMob] Error en /matchDetails id={fotmob_id}: {e}")
        return {}

    # Mapa teamId → nombre de equipo normalizado
    general = detail.get("general", {})
    team_map: dict[int, str] = {}
    for side, db_name in [("homeTeam", home_name_fm), ("awayTeam", away_name_fm)]:
        tid = general.get(side, {}).get("id")
        if tid:
            team_map[tid] = db_name

    # Intentar múltiples paths donde FotMob puede poner los eventos
    content = detail.get("content", {})
    events: list[dict] = (
        content.get("events", {}).get("Events", [])
        or content.get("incidents", [])
        or detail.get("header", {}).get("events", {}).get("events", [])
    )

    if debug and not events:
        print(f"      [FotMob DEBUG] id={fotmob_id} — sin eventos. content keys: {list(content.keys())}")

    result: dict[str, dict] = {}

    for ev in events:
        ev_type = ev.get("type", "")
        # FotMob puede usar string ("Goal"), código numérico (41) o dict
        if isinstance(ev_type, int):
            is_goal = ev_type in (41, 42, 43)
        else:
            is_goal = "goal" in str(ev_type).lower()

        if not is_goal:
            continue
        if ev.get("isOwnGoal") or ev.get("ownGoal"):
            continue

        assist_name = _fotmob_assist_name(ev)
        if not assist_name:
            continue

        scoring_team_id = ev.get("teamId")
        team = team_map.get(scoring_team_id, home_name_fm)

        if assist_name not in result:
            result[assist_name] = {"team": team, "assists": 0}
        result[assist_name]["assists"] += 1

    return result


def fetch_sofascore_match_assists(date_str: str, home_team: str, away_team: str,
                                  debug: bool = False) -> dict[str, dict]:
    """
    Obtiene asistidores de gol para un partido desde SofaScore.
    Retorna {player_name: {"team": team, "assists": count}}
    """
    try:
        data = requests.get(
            f"{SOFASCORE_BASE}/sport/football/scheduled-events/{date_str}",
            headers=SOFASCORE_HEADERS, timeout=20
        ).json()
    except Exception as e:
        if debug:
            print(f"      [SofaScore] Error en scheduled-events: {e}")
        return {}

    ss_id = None
    home_name = away_name = ""

    for ev in data.get("events", []):
        # Filtrar por torneo (World Cup)
        t_id   = ev.get("tournament", {}).get("uniqueTournament", {}).get("id")
        t_name = ev.get("tournament", {}).get("name", "").lower()
        if t_id != SOFASCORE_WC_ID and "world cup" not in t_name:
            continue
        h_raw = ev.get("homeTeam", {}).get("name", "")
        a_raw = ev.get("awayTeam", {}).get("name", "")
        h_db  = normalize(h_raw) or h_raw
        a_db  = normalize(a_raw) or a_raw
        if h_db == home_team and a_db == away_team:
            ss_id     = ev.get("id")
            home_name = h_db
            away_name = a_db
            break

    if not ss_id:
        if debug:
            print(f"      [SofaScore] Partido no encontrado: {home_team} vs {away_team} ({date_str})")
        return {}

    try:
        inc_data = requests.get(
            f"{SOFASCORE_BASE}/event/{ss_id}/incidents",
            headers=SOFASCORE_HEADERS, timeout=20
        ).json()
    except Exception as e:
        if debug:
            print(f"      [SofaScore] Error en /incidents id={ss_id}: {e}")
        return {}

    result: dict[str, dict] = {}

    for inc in inc_data.get("incidents", []):
        if inc.get("incidentType") != "goal":
            continue
        if inc.get("incidentClass") in ("ownGoal", "ownGoalAssist"):
            continue

        assist1 = inc.get("assist1")
        if not assist1 or not isinstance(assist1, dict):
            continue
        assister_name = assist1.get("name", "")
        if not assister_name:
            continue

        is_home = inc.get("isHome", True)
        team = home_name if is_home else away_name

        if assister_name not in result:
            result[assister_name] = {"team": team, "assists": 0}
        result[assister_name]["assists"] += 1

    if debug:
        print(f"      [SofaScore] id={ss_id} {home_team} vs {away_team}: {len(result)} asistidor(es)")

    return result


def build_tournament_assists(conn) -> list[dict]:
    """
    Agrega asistencias de TODOS los partidos WC 2026 completados desde SofaScore.
    SofaScore registra asistencias de gol de forma completa.
    Retorna [{player, team, assists}, ...] ordenado desc.
    """
    rows = conn.execute(text("""
        SELECT th.name AS home_team, ta.name AS away_team, m.date::text
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id = :sid
           AND m.home_goals IS NOT NULL
         ORDER BY m.date
    """), {"sid": WC_2026_SEASON_ID}).fetchall()

    totals: dict[str, dict] = {}

    print(f"   Procesando {len(rows)} partidos completados (SofaScore)...")
    for idx, r in enumerate(rows):
        match_assists = fetch_sofascore_match_assists(
            r.date, r.home_team, r.away_team, debug=(idx < 3)
        )
        if match_assists:
            print(f"      [SS] {r.home_team} vs {r.away_team} ({r.date}): "
                  f"{len(match_assists)} asistidor(es): "
                  f"{', '.join(f'{p}({d[\"assists\"]})' for p,d in match_assists.items())}")
        for player, info in match_assists.items():
            if player not in totals:
                totals[player] = {"team": info["team"], "assists": 0}
            totals[player]["assists"] += info["assists"]
        time.sleep(0.35)

    result = [
        {"player": p, "team": d["team"], "assists": d["assists"]}
        for p, d in totals.items()
        if d["assists"] > 0
    ]
    result.sort(key=lambda x: (-x["assists"], x["player"]))
    print(f"   Total asistidores SofaScore: {len(result)}")
    return result


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

    # Eventos ya almacenados: {(match_id, player_name, minute): tiene_asistencia}
    existing: dict[tuple, bool] = {}
    for row in conn.execute(text(
        "SELECT match_id, player_name, minute, assist_player FROM wc_scoring_events"
    )).fetchall():
        existing[(row.match_id, row.player_name, row.minute)] = row.assist_player is not None

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

    inserted = updated = 0
    for match_key, match_events in by_match.items():
        match_id, espn_id = match_lookup[match_key]

        # Intentar conseguir asistidores desde ESPN
        assists_by_min: dict[int, list[str]] = {}
        if espn_id:
            assists_by_min = fetch_espn_assists(int(espn_id))
            time.sleep(0.25)

        # Track which minute-slots of this match have been consumed (para múltiples goles mismo minuto)
        minute_cursor: dict[int, int] = {}

        for ev in match_events:
            key3 = (match_id, ev["player_name"], ev["minute"])
            already_has_assist = existing.get(key3)  # True/False/None

            # Obtener asistencia para este minuto (soporte para múltiples goles mismo minuto)
            assist: str | None = None
            if ev["minute"] is not None and ev["minute"] in assists_by_min:
                candidates = assists_by_min[ev["minute"]]
                idx = minute_cursor.get(ev["minute"], 0)
                if idx < len(candidates):
                    assist = candidates[idx]
                    minute_cursor[ev["minute"]] = idx + 1

            # Skip solo si el evento ya existe Y ya tiene asistencia Y no tenemos nueva
            if already_has_assist is True and assist is None:
                continue
            # Skip si ya existe, ya tiene asistencia, y la nueva es la misma (sin cambio)
            if already_has_assist is True and assist is not None and key3 in existing:
                pass  # Igual corremos el UPSERT para no perder datos

            is_new = key3 not in existing
            goal_type = " (OG)" if ev["is_own_goal"] else " (P)" if ev["is_penalty"] else ""
            assist_str = f" -> {assist}" if assist else ""
            action = "nuevo" if is_new else "actualiza"
            label = "[DRY]" if dry_run else "ok"
            print(f"   [{label}] {action} {ev['team']} — {ev['player_name']}{goal_type} {ev['minute']}'{assist_str}")

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
                    "match_id":      match_id,
                    "team":          ev["team"],
                    "player_name":   ev["player_name"],
                    "minute":        ev["minute"],
                    "is_own_goal":   ev["is_own_goal"],
                    "is_penalty":    ev["is_penalty"],
                    "assist_player": assist,
                })
                existing[key3] = assist is not None
                if is_new:
                    inserted += 1
                else:
                    updated += 1

    return inserted, updated



def store_tournament_stats(conn, leaders: list[dict], dry_run: bool) -> int:
    """
    Guarda la lista de líderes en wc_player_stats.
    leaders = [{"player": name, "team": team, "assists": n}, ...]
    """
    if not leaders:
        return 0
    upserted = 0
    for entry in leaders:
        label = "[DRY]" if dry_run else "ok"
        print(f"   [{label}] {entry['player']} ({entry['team']}) — {entry['assists']} asist.")
        if not dry_run:
            conn.execute(text("""
                INSERT INTO wc_player_stats (player_name, team, assists, source, updated_at)
                VALUES (:p, :t, :a, 'espn_leaders', NOW())
                ON CONFLICT (player_name) DO UPDATE SET
                    assists    = EXCLUDED.assists,
                    team       = EXCLUDED.team,
                    updated_at = NOW()
            """), {"p": entry["player"], "t": entry["team"], "a": entry["assists"]})
        upserted += 1
    return upserted


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
        inserted, updated = store_scorers(conn, events, dry_run)

    # Asistencias acumuladas desde SofaScore → wc_player_stats
    print(f"\n🎯 Agregando asistencias desde SofaScore...")
    with engine.begin() as conn:
        leaders = build_tournament_assists(conn)
    if leaders:
        with engine.begin() as conn:
            upserted = store_tournament_stats(conn, leaders, dry_run)
        print(f"   Líderes guardados en wc_player_stats: {upserted}")
    else:
        print("   Sin datos de SofaScore disponibles")
        upserted = 0

    print(f"\n{'=' * 60}")
    print(f"  Goles nuevos insertados   : {inserted}")
    print(f"  Asistencias actualizadas  : {updated}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
