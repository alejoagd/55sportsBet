"""
Descarga estadísticas reales de los partidos del Mundial 2026 desde API-Football
y las guarda en la tabla match_stats.

FUENTE: https://api-sports.io  (plan gratuito: 100 req/día)
  - World Cup 2026: league_id=1, season=2026
  - Estadísticas: shots, shots on goal, fouls, cards, corners, possession

LÓGICA:
  1. Crea tablas si no existen (match_stats, columna apifootball_id en matches)
  2. Mapea fixture_ids de API-Football → match_id local (por fecha + equipos)
  3. Para cada partido completado sin stats → GET /fixtures/statistics → INSERT

Uso:
  python update_wc2026_stats.py
  python update_wc2026_stats.py --dry-run
"""
from __future__ import annotations
import os
import sys
import requests
from sqlalchemy import text
from src.db import engine

APIFOOTBALL_BASE  = "https://v3.football.api-sports.io"
WC_LEAGUE_ID      = 1
WC_SEASON         = 2026
WC_2026_SEASON_ID = 76

# ── Mapeo nombre API-Football → nombre en BD ─────────────────────────────────
AF_TO_DB: dict[str, str] = {
    "Czech Republic":             "Czechia",
    "Czechia":                    "Czechia",
    "Cote d'Ivoire":              "Ivory Coast",
    "Côte d'Ivoire":              "Ivory Coast",
    "Ivory Coast":                "Ivory Coast",
    "DR Congo":                   "Congo DR",
    "Congo DR":                   "Congo DR",
    "Democratic Republic of Congo": "Congo DR",
    "Cape Verde":                 "Cape Verde",
    "Cabo Verde":                 "Cape Verde",
    "Korea Republic":             "South Korea",
    "South Korea":                "South Korea",
    "Bosnia And Herzegovina":     "Bosnia and Herzegovina",
    "Bosnia and Herzegovina":     "Bosnia and Herzegovina",
    "United States":              "United States",
    "USA":                        "United States",
    "Iran":                       "Iran",
    "IR Iran":                    "Iran",
}

_PASSTHROUGH = {
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Paraguay",
    "France", "England", "Belgium", "Portugal", "Spain", "Netherlands",
    "Germany", "Croatia", "Switzerland", "Norway", "Turkey", "Scotland",
    "Austria", "Sweden", "Morocco", "Senegal", "Algeria", "Tunisia",
    "Egypt", "Ghana", "South Africa", "Japan", "Australia",
    "Saudi Arabia", "Qatar", "Uzbekistan", "Jordan", "Iraq",
    "Mexico", "Canada", "Panama", "Haiti", "Curacao",
    "New Zealand",
}


def normalize_af(name: str) -> str | None:
    if name in AF_TO_DB:
        return AF_TO_DB[name]
    if name in _PASSTHROUGH:
        return name
    return None


def _headers(api_key: str) -> dict:
    return {"x-apisports-key": api_key, "Accept": "application/json"}


# ── Paso 0: Crear tablas ─────────────────────────────────────────────────────

def ensure_tables(conn) -> None:
    conn.execute(text("""
        ALTER TABLE matches ADD COLUMN IF NOT EXISTS apifootball_id INTEGER
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
            fetched_at        TIMESTAMP DEFAULT NOW()
        )
    """))


# ── Paso 1: Mapear fixture IDs ───────────────────────────────────────────────

def map_fixture_ids(conn, api_key: str) -> int:
    """Llama /fixtures?league=1&season=2026 y guarda apifootball_id en matches."""
    resp = requests.get(
        f"{APIFOOTBALL_BASE}/fixtures",
        params={"league": WC_LEAGUE_ID, "season": WC_SEASON},
        headers=_headers(api_key),
        timeout=30,
    )
    resp.raise_for_status()
    fixtures = resp.json().get("response", [])
    print(f"   API-Football devolvió {len(fixtures)} fixtures")

    mapped = 0
    for fx in fixtures:
        date_str = fx["fixture"]["date"][:10]   # "2026-06-11T..."  →  "2026-06-11"
        home_af  = fx["teams"]["home"]["name"]
        away_af  = fx["teams"]["away"]["name"]
        fx_id    = fx["fixture"]["id"]

        home_db = normalize_af(home_af)
        away_db = normalize_af(away_af)
        if not home_db or not away_db:
            print(f"   ⚠️  Sin mapeo: '{home_af}' vs '{away_af}'")
            continue

        result = conn.execute(text("""
            UPDATE matches
               SET apifootball_id = :fxid
             WHERE season_id      = :sid
               AND date           = :date
               AND home_team_id   = (SELECT id FROM teams WHERE name = :home)
               AND away_team_id   = (SELECT id FROM teams WHERE name = :away)
               AND apifootball_id IS NULL
        """), {"fxid": fx_id, "sid": WC_2026_SEASON_ID,
               "date": date_str, "home": home_db, "away": away_db})
        if result.rowcount > 0:
            mapped += 1

    return mapped


# ── Paso 2: Descargar y guardar estadísticas ─────────────────────────────────

def _stat(stats: list, stat_type: str) -> int | None:
    for s in stats:
        if s["type"] == stat_type:
            val = s["value"]
            if val is None:
                return None
            try:
                return int(str(val).replace("%", "").strip())
            except (ValueError, TypeError):
                return None
    return None


def fetch_and_store_stats(conn, api_key: str, dry_run: bool = False) -> tuple[int, int]:
    """Retorna (actualizados, sin_fixture_id)."""
    pending = conn.execute(text("""
        SELECT m.id AS match_id, m.apifootball_id,
               th.name AS home_team, ta.name AS away_team, m.date
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id       = :sid
           AND m.home_goals      IS NOT NULL
           AND m.apifootball_id  IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM match_stats ms WHERE ms.match_id = m.id)
         ORDER BY m.date
    """), {"sid": WC_2026_SEASON_ID}).fetchall()

    no_fixture_id = conn.execute(text("""
        SELECT COUNT(*) FROM matches
         WHERE season_id   = :sid
           AND home_goals  IS NOT NULL
           AND apifootball_id IS NULL
    """), {"sid": WC_2026_SEASON_ID}).scalar() or 0

    print(f"   Partidos completados sin stats       : {len(pending)}")
    print(f"   Partidos completados sin fixture_id  : {no_fixture_id}")

    updated = 0
    for row in pending:
        resp = requests.get(
            f"{APIFOOTBALL_BASE}/fixtures/statistics",
            params={"fixture": row.apifootball_id},
            headers=_headers(api_key),
            timeout=30,
        )
        if not resp.ok:
            print(f"   ⚠️  HTTP {resp.status_code} para fixture {row.apifootball_id}")
            continue

        teams_data = resp.json().get("response", [])
        if len(teams_data) < 2:
            print(f"   ⚠️  Sin stats: {row.home_team} vs {row.away_team} ({row.date})")
            continue

        # Asignar por nombre de equipo (no por índice) para mayor seguridad
        home_stats = away_stats = None
        for td in teams_data:
            db_name = normalize_af(td["team"]["name"])
            if db_name == row.home_team:
                home_stats = td["statistics"]
            elif db_name == row.away_team:
                away_stats = td["statistics"]

        if not home_stats or not away_stats:
            print(f"   ⚠️  No se pudo identificar equipos en stats de fixture {row.apifootball_id}")
            continue

        data = {
            "match_id":           row.match_id,
            "home_shots":         _stat(home_stats, "Total Shots"),
            "home_shots_ot":      _stat(home_stats, "Shots on Goal"),
            "home_fouls":         _stat(home_stats, "Fouls"),
            "home_yellow_cards":  _stat(home_stats, "Yellow Cards"),
            "home_red_cards":     _stat(home_stats, "Red Cards"),
            "home_corners":       _stat(home_stats, "Corner Kicks"),
            "home_possession":    _stat(home_stats, "Ball Possession"),
            "away_shots":         _stat(away_stats, "Total Shots"),
            "away_shots_ot":      _stat(away_stats, "Shots on Goal"),
            "away_fouls":         _stat(away_stats, "Fouls"),
            "away_yellow_cards":  _stat(away_stats, "Yellow Cards"),
            "away_red_cards":     _stat(away_stats, "Red Cards"),
            "away_corners":       _stat(away_stats, "Corner Kicks"),
            "away_possession":    _stat(away_stats, "Ball Possession"),
        }

        label = "[DRY]" if dry_run else "✅"
        print(f"   {label} {row.home_team} vs {row.away_team} ({row.date})")
        print(f"        Tiros: {data['home_shots']}-{data['away_shots']} | "
              f"SOT: {data['home_shots_ot']}-{data['away_shots_ot']} | "
              f"Corners: {data['home_corners']}-{data['away_corners']} | "
              f"Faltas: {data['home_fouls']}-{data['away_fouls']}")

        if not dry_run:
            conn.execute(text("""
                INSERT INTO match_stats (
                    match_id,
                    home_shots, home_shots_ot, home_fouls,
                    home_yellow_cards, home_red_cards, home_corners, home_possession,
                    away_shots, away_shots_ot, away_fouls,
                    away_yellow_cards, away_red_cards, away_corners, away_possession
                ) VALUES (
                    :match_id,
                    :home_shots, :home_shots_ot, :home_fouls,
                    :home_yellow_cards, :home_red_cards, :home_corners, :home_possession,
                    :away_shots, :away_shots_ot, :away_fouls,
                    :away_yellow_cards, :away_red_cards, :away_corners, :away_possession
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
                    fetched_at        = NOW()
            """), data)
        updated += 1

    return updated, int(no_fixture_id)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    api_key = os.getenv("APIFOOTBALL_KEY", "")
    if not api_key:
        print("❌  APIFOOTBALL_KEY no configurada.")
        print("   Agrégala al .env o exporta: $env:APIFOOTBALL_KEY='tu_key'")
        sys.exit(1)

    mode = "DRY RUN" if dry_run else "ACTUALIZANDO BD"
    print("=" * 60)
    print(f"  WC 2026 Stats Updater — {mode}")
    print(f"  Fuente: api-sports.io (API-Football)")
    print("=" * 60)

    with engine.begin() as conn:
        print("\n🔧 Verificando tablas...")
        ensure_tables(conn)
        print("   ✓ match_stats OK | columna apifootball_id OK")

        print("\n🗺️  Mapeando fixture IDs de API-Football...")
        mapped = map_fixture_ids(conn, api_key)
        print(f"   {mapped} fixture(s) nuevos mapeados")

        print("\n📊 Descargando estadísticas de partidos completados...")
        updated, no_fx = fetch_and_store_stats(conn, api_key, dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Stats actualizadas : {updated}")
    print(f"  Sin fixture_id     : {no_fx}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
