"""
seed_wc2026_r32_schedule.py
Descarga el calendario de Octavos de Final (R32) del Mundial 2026 desde ESPN
e inserta los partidos en la tabla matches (con o sin marcador según estado).

Ejecutar una vez cuando el schedule de R32 esté disponible:
  python seed_wc2026_r32_schedule.py
  python seed_wc2026_r32_schedule.py --dry-run

Después de ejecutar este script, correr predicciones:
  python -m src.predictions.cli upcoming --season-id 76
"""
from __future__ import annotations
import sys
import time
import requests
from datetime import date, timedelta
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76
WC_R32_START = "2026-06-28"
WC_R32_END   = "2026-07-05"   # Last R32 day (8 días × 2 partidos = 16 total)

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

# ── Normalización de nombres ──────────────────────────────────────────────────
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
    "CuraÇao":                      "Curacao",
}
_PASSTHROUGH = {
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Paraguay",
    "France", "England", "Belgium", "Portugal", "Spain", "Netherlands",
    "Germany", "Croatia", "Switzerland", "Norway", "Turkey", "Scotland",
    "Austria", "Sweden", "Morocco", "Senegal", "Algeria", "Tunisia",
    "Egypt", "Ghana", "South Africa", "Japan", "Australia", "Iran",
    "Saudi Arabia", "Qatar", "Uzbekistan", "Jordan", "Iraq",
    "Mexico", "Canada", "Panama", "Haiti", "New Zealand",
}


def normalize(name: str) -> str | None:
    if name in EXT_TO_DB:
        return EXT_TO_DB[name]
    if name in _PASSTHROUGH:
        return name
    return None


def _fulltime_result(hg: int, ag: int) -> str:
    if hg > ag: return "H"
    if ag > hg: return "A"
    return "D"


# ── ESPN ─────────────────────────────────────────────────────────────────────

def espn_events_for_date(date_str: str) -> list[dict]:
    compact = date_str.replace("-", "")
    try:
        resp = requests.get(
            f"{ESPN_BASE}/{ESPN_LEAGUE}/scoreboard",
            headers=HEADERS,
            params={"dates": compact},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"   ⚠️  ESPN error para {date_str}: {e}")
        return []


def fetch_r32_fixtures() -> list[dict]:
    """Descarga todos los fixtures R32 WC2026 desde ESPN (June 28 – July 5)."""
    fixtures: list[dict] = []
    d = date.fromisoformat(WC_R32_START)
    end = date.fromisoformat(WC_R32_END)

    while d <= end:
        date_str = d.isoformat()
        events = espn_events_for_date(date_str)

        if events:
            print(f"   {date_str}: {len(events)} evento(s) encontrado(s)")
        else:
            print(f"   {date_str}: sin eventos")

        for ev in events:
            comps = ev.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                # fallback: first=home, second=away
                home, away = competitors[0], competitors[1]

            home_raw = home.get("team", {}).get("displayName", "")
            away_raw = away.get("team", {}).get("displayName", "")

            home_db = normalize(home_raw)
            away_db = normalize(away_raw)
            if not home_db or not away_db:
                print(f"      ⚠️  Nombre no mapeado: '{home_raw}' / '{away_raw}'")
                continue

            # Extraer marcador si el partido terminó o está en curso
            home_goals = away_goals = None
            status_name = comp.get("status", {}).get("type", {}).get("name", "")
            if status_name == "STATUS_FINAL":
                try:
                    home_goals = int(home.get("score", ""))
                    away_goals = int(away.get("score", ""))
                except (ValueError, TypeError):
                    pass

            espn_id = ev.get("id")

            # Use actual event date from ESPN (UTC), not the query date
            raw_date = comp.get("date", "") or ev.get("date", "")
            event_date = raw_date.split("T")[0] if raw_date else date_str

            fixtures.append({
                "date":       event_date,
                "home_team":  home_db,
                "away_team":  away_db,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "espn_id":    int(espn_id) if espn_id else None,
                "status":     status_name,
            })

        d += timedelta(days=1)
        time.sleep(0.3)

    return fixtures


# ── Base de datos ─────────────────────────────────────────────────────────────

def ensure_column(conn) -> None:
    conn.execute(text(
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS sofascore_id INTEGER"
    ))


def get_team_ids(conn) -> dict[str, int]:
    rows = conn.execute(text("SELECT id, name FROM teams")).fetchall()
    return {r.name: r.id for r in rows}


def get_existing_r32(conn) -> dict[tuple, dict]:
    """Retorna {(date, home, away): {id, has_result}} para partidos >= R32_START."""
    rows = conn.execute(text("""
        SELECT m.id, m.date::text, m.home_goals,
               th.name AS home, ta.name AS away
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id = :sid AND m.date >= :start
    """), {"sid": WC_2026_SEASON_ID, "start": WC_R32_START}).fetchall()
    return {
        (r.date, r.home, r.away): {"id": r.id, "has_result": r.home_goals is not None}
        for r in rows
    }


def process(conn, fixtures: list[dict], dry_run: bool) -> tuple[int, int, int]:
    team_ids = get_team_ids(conn)
    existing = get_existing_r32(conn)
    inserted = updated = skipped = 0

    for f in fixtures:
        key     = (f["date"], f["home_team"], f["away_team"])
        key_rev = (f["date"], f["away_team"], f["home_team"])
        hid = team_ids.get(f["home_team"])
        aid = team_ids.get(f["away_team"])

        if not hid:
            print(f"   ⚠️  Equipo no encontrado en BD: {f['home_team']}")
            continue
        if not aid:
            print(f"   ⚠️  Equipo no encontrado en BD: {f['away_team']}")
            continue

        hg, ag = f["home_goals"], f["away_goals"]
        status = f.get("status", "")

        if key in existing or key_rev in existing:
            rec = existing.get(key) or existing.get(key_rev)
            # Actualizar marcador si ahora está disponible y antes no lo estaba
            if rec and not rec["has_result"] and hg is not None:
                reversed_order = key not in existing
                actual_hg = ag if reversed_order else hg
                actual_ag = hg if reversed_order else ag
                label = "[DRY]" if dry_run else "📝"
                print(f"   {label} resultado: {f['home_team']} {hg}-{ag} {f['away_team']}")
                if not dry_run:
                    conn.execute(text("""
                        UPDATE matches SET home_goals=:hg, away_goals=:ag,
                               fulltime_result=:res
                        WHERE id=:mid
                    """), {"hg": actual_hg, "ag": actual_ag,
                           "res": _fulltime_result(actual_hg, actual_ag),
                           "mid": rec["id"]})
                updated += 1
            else:
                skipped += 1
        else:
            fulltime = _fulltime_result(hg, ag) if hg is not None else None
            label = "[DRY]" if dry_run else "✅"
            score = f"{hg}-{ag}" if hg is not None else "programado"
            print(f"   {label} nuevo: {f['home_team']} vs {f['away_team']} ({f['date']}) [{score}]")
            if not dry_run:
                conn.execute(text("""
                    INSERT INTO matches
                        (season_id, date, home_team_id, away_team_id,
                         home_goals, away_goals, fulltime_result, sofascore_id)
                    VALUES
                        (:sid, :date, :hid, :aid, :hg, :ag, :res, :eid)
                """), {
                    "sid":  WC_2026_SEASON_ID,
                    "date": f["date"],
                    "hid":  hid,
                    "aid":  aid,
                    "hg":   hg,
                    "ag":   ag,
                    "res":  fulltime,
                    "eid":  f.get("espn_id"),
                })
            inserted += 1

    return inserted, updated, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "INSERTANDO EN BD"
    print("=" * 60)
    print(f"  WC 2026 R32 Schedule Seeder — {mode}")
    print(f"  Rango: {WC_R32_START} → {WC_R32_END}")
    print("=" * 60)

    print("\n📥 Descargando fixtures R32 desde ESPN...")
    fixtures = fetch_r32_fixtures()

    if not fixtures:
        print("\nℹ️  No se encontraron fixtures R32 en ESPN.")
        return

    print(f"\n   Total fixtures encontrados: {len(fixtures)}")
    print(f"\n🔄 Procesando...")

    with engine.begin() as conn:
        ensure_column(conn)
        inserted, updated, skipped = process(conn, fixtures, dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Insertados  : {inserted}")
    print(f"  Actualizados: {updated}")
    print(f"  Ya existían : {skipped}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)

    if not dry_run and inserted > 0:
        print("\n💡 Siguiente paso: generar predicciones para los nuevos partidos:")
        print("   python -m src.predictions.cli upcoming --season-id 76")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
