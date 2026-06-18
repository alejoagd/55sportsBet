"""
update_wc2026_stats.py
Descarga estadísticas reales del Mundial 2026 desde ESPN o Fotmob (sin API key)
y las guarda en match_stats.

FUENTES (se intentan en orden):
  1. ESPN   — site.api.espn.com  (más estable, pública)
  2. Fotmob — www.fotmob.com/api (fallback)

LÓGICA:
  1. Crea match_stats y columna sofascore_id en matches si no existen
  2. Para cada fecha con partidos WC en la BD → busca en ESPN/Fotmob
     y mapea external_id ↔ match_id (por nombre de equipos)
  3. Para partidos completados sin stats → fetch estadísticas → INSERT

Uso:
  python update_wc2026_stats.py
  python update_wc2026_stats.py --dry-run
  python update_wc2026_stats.py --diagnose
"""
from __future__ import annotations
import sys
import time
import requests
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76

ESPN_BASE       = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUE     = "fifa.world"          # slug del Mundial en ESPN
FOTMOB_BASE     = "https://www.fotmob.com/api"
FOTMOB_WC_ID    = 77                    # tournament_id del Mundial en Fotmob (histórico)

HEADERS_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ── Mapeo nombres externos → BD ──────────────────────────────────────────────
EXT_TO_DB: dict[str, str] = {
    "Czech Republic":               "Czechia",
    "Czechia":                      "Czechia",
    "Cote d'Ivoire":                "Ivory Coast",
    "Ivory Coast":                  "Ivory Coast",
    "DR Congo":                     "Congo DR",
    "Congo DR":                     "Congo DR",
    "Democratic Republic of Congo": "Congo DR",
    "Cape Verde":                   "Cape Verde",
    "Cabo Verde":                   "Cape Verde",
    "Korea Republic":               "South Korea",
    "South Korea":                  "South Korea",
    "Bosnia-Herzegovina":           "Bosnia and Herzegovina",
    "Bosnia And Herzegovina":       "Bosnia and Herzegovina",
    "Bosnia and Herzegovina":       "Bosnia and Herzegovina",
    "United States":                "United States",
    "USA":                          "United States",
    "Iran":                         "Iran",
    "IR Iran":                      "Iran",
    "Curacao":                      "Curacao",
    "Curaçao":                      "Curacao",
    "New Zealand":                  "New Zealand",
}

_PASSTHROUGH = {
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Paraguay",
    "France", "England", "Belgium", "Portugal", "Spain", "Netherlands",
    "Germany", "Croatia", "Switzerland", "Norway", "Turkey", "Scotland",
    "Austria", "Sweden", "Morocco", "Senegal", "Algeria", "Tunisia",
    "Egypt", "Ghana", "South Africa", "Japan", "Australia",
    "Saudi Arabia", "Qatar", "Uzbekistan", "Jordan", "Iraq",
    "Mexico", "Canada", "Panama", "Haiti",
}


def normalize(name: str) -> str | None:
    if name in EXT_TO_DB:
        return EXT_TO_DB[name]
    if name in _PASSTHROUGH:
        return name
    return None


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, headers=HEADERS_BROWSER, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


# ── Tablas ───────────────────────────────────────────────────────────────────

def ensure_tables(conn) -> None:
    conn.execute(text("""
        ALTER TABLE matches ADD COLUMN IF NOT EXISTS sofascore_id INTEGER
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS match_stats (
            id                SERIAL PRIMARY KEY,
            match_id          INTEGER REFERENCES matches(id) UNIQUE,
            home_shots        INTEGER,
            home_shots_ot     INTEGER,
            home_fouls        INTEGER,
            home_yellow_cards INTEGER,
            home_red_cards    INTEGER,
            home_corners      INTEGER,
            home_possession   INTEGER,
            away_shots        INTEGER,
            away_shots_ot     INTEGER,
            away_fouls        INTEGER,
            away_yellow_cards INTEGER,
            away_red_cards    INTEGER,
            away_corners      INTEGER,
            away_possession   INTEGER,
            source            TEXT,
            fetched_at        TIMESTAMP DEFAULT NOW()
        )
    """))
    # Migración: agrega columnas que pueden faltar en tablas creadas con versiones anteriores
    for col in ("home_shots_ot", "away_shots_ot", "home_fouls", "away_fouls",
                "home_corners", "away_corners", "home_possession", "away_possession",
                "source", "fetched_at"):
        dtype = "TIMESTAMP DEFAULT NOW()" if col == "fetched_at" else "TEXT" if col == "source" else "INTEGER"
        conn.execute(text(f"ALTER TABLE match_stats ADD COLUMN IF NOT EXISTS {col} {dtype}"))


# ── ESPN ─────────────────────────────────────────────────────────────────────

def espn_events_for_date(date_str: str) -> list[dict]:
    """GET /fifa.world/scoreboard?dates=YYYYMMDD → lista de eventos."""
    compact = date_str.replace("-", "")
    data = _get(f"{ESPN_BASE}/{ESPN_LEAGUE}/scoreboard", {"dates": compact})
    return data.get("events", [])


def espn_stats(event_id: str) -> dict | None:
    """GET /fifa.world/summary?event={id} → estadísticas o None."""
    data = _get(f"{ESPN_BASE}/{ESPN_LEAGUE}/summary", {"event": event_id})
    box  = data.get("boxscore", {})
    teams = box.get("teams", [])
    if len(teams) < 2:
        return None

    def stat_val(stats_list: list, key: str) -> int | None:
        for s in stats_list:
            if s.get("name") == key:
                try:
                    return int(float(s.get("displayValue", "").replace("%", "") or 0))
                except (ValueError, TypeError):
                    return None
        return None

    # ESPN pone home primero, away segundo
    home_t = teams[0]
    away_t = teams[1]
    hs = home_t.get("statistics", [])
    as_ = away_t.get("statistics", [])

    return {
        "home_name":       home_t.get("team", {}).get("displayName", ""),
        "away_name":       away_t.get("team", {}).get("displayName", ""),
        "home_shots":      stat_val(hs, "totalShots"),
        "home_shots_ot":   stat_val(hs, "shotsOnTarget"),
        "home_fouls":      stat_val(hs, "fouls"),
        "home_yellow_cards": stat_val(hs, "yellowCards"),
        "home_red_cards":  stat_val(hs, "redCards"),
        "home_corners":    stat_val(hs, "cornerKicks"),
        "home_possession": stat_val(hs, "possessionPct"),
        "away_shots":      stat_val(as_, "totalShots"),
        "away_shots_ot":   stat_val(as_, "shotsOnTarget"),
        "away_fouls":      stat_val(as_, "fouls"),
        "away_yellow_cards": stat_val(as_, "yellowCards"),
        "away_red_cards":  stat_val(as_, "redCards"),
        "away_corners":    stat_val(as_, "cornerKicks"),
        "away_possession": stat_val(as_, "possessionPct"),
        "source":          "ESPN",
    }


# ── Fotmob ───────────────────────────────────────────────────────────────────

def fotmob_events_for_date(date_str: str) -> list[dict]:
    """GET /matches?date=YYYYMMDD → eventos del Mundial."""
    compact = date_str.replace("-", "")
    data = _get(f"{FOTMOB_BASE}/matches", {"date": compact})
    wc_events = []
    for league in data.get("leagues", []):
        name = league.get("name", "").lower()
        lid  = league.get("id")
        if "world cup" in name or lid == FOTMOB_WC_ID:
            wc_events.extend(league.get("matches", []))
    return wc_events


def fotmob_stats(match_id: int) -> dict | None:
    """GET /matchDetails?matchId={id} → estadísticas o None."""
    data = _get(f"{FOTMOB_BASE}/matchDetails", {"matchId": match_id})
    stats_raw = data.get("content", {}).get("stats", {}).get("Periods", {}).get("All", {}).get("stats", [])

    def find(title_kw: str, side: str) -> int | None:
        for group in stats_raw:
            for item in group.get("stats", []):
                if title_kw.lower() in item.get("title", "").lower():
                    val = item.get("stats", {}).get(side)
                    if val is None:
                        return None
                    try:
                        return int(str(val).replace("%", "").strip())
                    except (ValueError, TypeError):
                        return None
        return None

    home_info = data.get("general", {}).get("homeTeam", {})
    away_info = data.get("general", {}).get("awayTeam", {})

    return {
        "home_name":       home_info.get("name", ""),
        "away_name":       away_info.get("name", ""),
        "home_shots":      find("total shots", "home"),
        "home_shots_ot":   find("shots on target", "home"),
        "home_fouls":      find("fouls", "home"),
        "home_yellow_cards": find("yellow card", "home"),
        "home_red_cards":  find("red card", "home"),
        "home_corners":    find("corner", "home"),
        "home_possession": find("possession", "home"),
        "away_shots":      find("total shots", "away"),
        "away_shots_ot":   find("shots on target", "away"),
        "away_fouls":      find("fouls", "away"),
        "away_yellow_cards": find("yellow card", "away"),
        "away_red_cards":  find("red card", "away"),
        "away_corners":    find("corner", "away"),
        "away_possession": find("possession", "away"),
        "source":          "Fotmob",
    }


# ── Mapeo de IDs ─────────────────────────────────────────────────────────────

def map_ids(conn) -> int:
    dates = conn.execute(text("""
        SELECT DISTINCT date::text
          FROM matches
         WHERE season_id   = :sid
           AND sofascore_id IS NULL
         ORDER BY date
    """), {"sid": WC_2026_SEASON_ID}).fetchall()

    mapped = 0
    for (date_str,) in dates:
        events = []

        # Intentar ESPN primero
        try:
            raw = espn_events_for_date(date_str)
            for ev in raw:
                comps = ev.get("competitions", [{}])[0]
                competitors = comps.get("competitors", [])
                if len(competitors) < 2:
                    continue
                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
                events.append({
                    "id":   ev["id"],
                    "home": home.get("team", {}).get("displayName", ""),
                    "away": away.get("team", {}).get("displayName", ""),
                    "src":  "ESPN",
                })
            if events:
                print(f"   {date_str}: {len(events)} eventos ESPN")
        except Exception as e:
            print(f"   {date_str}: ESPN falló ({e}), intentando Fotmob...")

        # Fotmob como fallback
        if not events:
            try:
                raw = fotmob_events_for_date(date_str)
                for ev in raw:
                    events.append({
                        "id":   ev["id"],
                        "home": ev.get("home", {}).get("name", ""),
                        "away": ev.get("away", {}).get("name", ""),
                        "src":  "Fotmob",
                    })
                if events:
                    print(f"   {date_str}: {len(events)} eventos Fotmob")
                else:
                    print(f"   {date_str}: 0 eventos WC en ESPN y Fotmob")
            except Exception as e2:
                print(f"   {date_str}: Fotmob también falló ({e2})")

        for ev in events:
            home_db = normalize(ev["home"])
            away_db = normalize(ev["away"])
            if not home_db or not away_db:
                print(f"      ⚠️  Sin mapeo: '{ev['home']}' vs '{ev['away']}'")
                continue

            res = conn.execute(text("""
                UPDATE matches
                   SET sofascore_id = :eid
                 WHERE season_id    = :sid
                   AND date         = :date
                   AND home_team_id = (SELECT id FROM teams WHERE name = :home)
                   AND away_team_id = (SELECT id FROM teams WHERE name = :away)
                   AND sofascore_id IS NULL
            """), {"eid": int(ev["id"]), "sid": WC_2026_SEASON_ID,
                   "date": date_str, "home": home_db, "away": away_db})
            if res.rowcount > 0:
                print(f"      ✓ [{ev['src']}] {home_db} vs {away_db} → id={ev['id']}")
                mapped += 1

        time.sleep(0.3)

    return mapped


# ── Fetch + store stats ───────────────────────────────────────────────────────

def fetch_and_store_stats(conn, dry_run: bool = False) -> tuple[int, int]:
    pending = conn.execute(text("""
        SELECT m.id AS match_id, m.sofascore_id,
               th.name AS home_team, ta.name AS away_team, m.date
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id    = :sid
           AND m.home_goals   IS NOT NULL
           AND m.sofascore_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM match_stats ms WHERE ms.match_id = m.id)
         ORDER BY m.date
    """), {"sid": WC_2026_SEASON_ID}).fetchall()

    no_id = conn.execute(text("""
        SELECT COUNT(*) FROM matches
         WHERE season_id  = :sid
           AND home_goals IS NOT NULL
           AND sofascore_id IS NULL
    """), {"sid": WC_2026_SEASON_ID}).scalar() or 0

    print(f"   Partidos completados sin stats       : {len(pending)}")
    print(f"   Partidos completados sin external_id : {no_id}")

    updated = 0
    for row in pending:
        stats = None

        # Intentar ESPN primero
        try:
            stats = espn_stats(str(row.sofascore_id))
        except Exception:
            pass

        # Fotmob como fallback
        if not stats:
            try:
                stats = fotmob_stats(row.sofascore_id)
            except Exception as e:
                print(f"   ⚠️  Sin stats para {row.home_team} vs {row.away_team}: {e}")
                time.sleep(0.5)
                continue

        if not stats:
            print(f"   ⚠️  Stats vacías para {row.home_team} vs {row.away_team}")
            continue

        data = {k: v for k, v in stats.items() if k not in ("home_name", "away_name")}
        data["match_id"] = row.match_id

        label = "[DRY]" if dry_run else "✅"
        print(f"   {label} [{data.get('source')}] {row.home_team} vs {row.away_team} ({row.date})")
        print(f"        Tiros: {data.get('home_shots')}-{data.get('away_shots')} | "
              f"SOT: {data.get('home_shots_ot')}-{data.get('away_shots_ot')} | "
              f"Corners: {data.get('home_corners')}-{data.get('away_corners')} | "
              f"Posesión: {data.get('home_possession')}%-{data.get('away_possession')}%")

        if not dry_run:
            conn.execute(text("""
                INSERT INTO match_stats (
                    match_id,
                    home_shots, home_shots_ot, home_fouls,
                    home_yellow_cards, home_red_cards, home_corners, home_possession,
                    away_shots, away_shots_ot, away_fouls,
                    away_yellow_cards, away_red_cards, away_corners, away_possession,
                    source
                ) VALUES (
                    :match_id,
                    :home_shots, :home_shots_ot, :home_fouls,
                    :home_yellow_cards, :home_red_cards, :home_corners, :home_possession,
                    :away_shots, :away_shots_ot, :away_fouls,
                    :away_yellow_cards, :away_red_cards, :away_corners, :away_possession,
                    :source
                ) ON CONFLICT (match_id) DO UPDATE SET
                    home_shots        = EXCLUDED.home_shots,
                    home_shots_ot     = EXCLUDED.home_shots_ot,
                    home_fouls        = EXCLUDED.home_fouls,
                    home_yellow_cards = EXCLUDED.home_yellow_cards,
                    home_red_cards    = EXCLUDED.home_red_cards,
                    home_corners      = EXCLUDED.home_corners,
                    home_possession   = EXCLUDED.home_possession,
                    away_shots        = EXCLUDED.away_shots,
                    away_shots_ot     = EXCLUDED.away_shots_ot,
                    away_fouls        = EXCLUDED.away_fouls,
                    away_yellow_cards = EXCLUDED.away_yellow_cards,
                    away_red_cards    = EXCLUDED.away_red_cards,
                    away_corners      = EXCLUDED.away_corners,
                    away_possession   = EXCLUDED.away_possession,
                    source            = EXCLUDED.source,
                    fetched_at        = NOW()
            """), data)
        updated += 1
        time.sleep(0.3)

    return updated, int(no_id)


# ── Diagnóstico ───────────────────────────────────────────────────────────────

def diagnose() -> None:
    print("=" * 60)
    print("  DIAGNÓSTICO — ESPN & Fotmob WC 2026")
    print("=" * 60)

    for date_str in ["2026-06-11", "2026-06-12"]:
        print(f"\n📅 {date_str}")

        print("  ESPN:")
        try:
            events = espn_events_for_date(date_str)
            print(f"    Total eventos: {len(events)}")
            for ev in events[:6]:
                comps = ev.get("competitions", [{}])[0]
                competitors = comps.get("competitors", [])
                teams = " vs ".join(c.get("team", {}).get("displayName", "?") for c in competitors)
                print(f"    id={ev['id']} | {teams}")
        except Exception as e:
            print(f"    ❌ {e}")

        print("  Fotmob:")
        try:
            events = fotmob_events_for_date(date_str)
            print(f"    Eventos WC: {len(events)}")
            for ev in events[:6]:
                home = ev.get("home", {}).get("name", "?")
                away = ev.get("away", {}).get("name", "?")
                print(f"    id={ev['id']} | {home} vs {away}")
        except Exception as e:
            print(f"    ❌ {e}")

        time.sleep(0.5)

    print("\n" + "=" * 60)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    if "--diagnose" in sys.argv:
        diagnose()
        return

    mode = "DRY RUN" if dry_run else "ACTUALIZANDO BD"
    print("=" * 60)
    print(f"  WC 2026 Stats Updater — {mode}")
    print(f"  Fuentes: ESPN → Fotmob (fallback)")
    print("=" * 60)

    with engine.begin() as conn:
        print("\n🔧 Verificando tablas...")
        ensure_tables(conn)
        print("   ✓ OK")

        print("\n🗺️  Mapeando IDs externos...")
        mapped = map_ids(conn)
        print(f"   {mapped} partido(s) nuevos mapeados")

        print("\n📊 Descargando estadísticas...")
        updated, no_id = fetch_and_store_stats(conn, dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Stats actualizadas   : {updated}")
    print(f"  Sin external_id      : {no_id}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
