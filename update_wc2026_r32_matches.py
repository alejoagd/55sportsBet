"""
update_wc2026_r32_matches.py
Crea/actualiza registros de octavos de final del Mundial 2026 en la tabla matches.

FUENTE ÚNICA: martj42/international_results results.csv
  → Partidos jugados con fecha >= 2026-06-28 y tournament = "FIFA World Cup"
  → Solo crea registros de partidos ya jugados (con resultado confirmado)
  → Ejecutar cada vez que se jueguen nuevos partidos de la fase eliminatoria

Uso:
  python update_wc2026_r32_matches.py
  python update_wc2026_r32_matches.py --dry-run
"""
from __future__ import annotations
import sys
import io
import csv
import requests
from sqlalchemy import text
from src.db import engine

WC_2026_SEASON_ID = 76
WC_R32_START      = "2026-06-28"   # primer día de octavos

RESULTS_CSV_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/results.csv"
)
SHOOTOUTS_CSV_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/shootouts.csv"
)

# ── Normalización de nombres ──────────────────────────────────────────────────
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
    "Curaçao":                          "Curacao",
    "CuraÇao":                          "Curacao",
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


def _fulltime_result(hg: int, ag: int) -> str:
    if hg > ag: return "H"
    if ag > hg: return "A"
    return "D"


def fetch_shootout_winners() -> dict[tuple, str]:
    """Returns {(date, home_db, away_db): winner_db} for WC2026 knockout shootouts."""
    try:
        resp = requests.get(SHOOTOUTS_CSV_URL, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"   ⚠️  Error descargando shootouts.csv: {e}")
        return {}

    reader = csv.DictReader(io.StringIO(resp.text))
    result: dict[tuple, str] = {}
    for row in reader:
        date       = row.get("date", "")
        if date < WC_R32_START:
            continue
        home_raw   = row.get("home_team", "").strip()
        away_raw   = row.get("away_team", "").strip()
        winner_raw = row.get("winner", "").strip()
        home_db   = normalize(home_raw)
        away_db   = normalize(away_raw)
        winner_db = normalize(winner_raw)
        if not home_db or not away_db or not winner_db:
            print(f"   ⚠️  Shootout no mapeado: '{home_raw}' vs '{away_raw}' → '{winner_raw}'")
            continue
        # Store both orderings so we match regardless of how teams are stored in DB
        result[(date, home_db, away_db)] = winner_db
        result[(date, away_db, home_db)] = winner_db
    print(f"   Shootouts WC 2026 en CSV: {len(result) // 2 if result else 0}")
    return result


def update_penalty_winners(conn, shootout_winners: dict[tuple, str], dry_run: bool) -> int:
    """Updates penalty_winner column in matches for shootout-decided games."""
    if not shootout_winners:
        return 0
    rows = conn.execute(text("""
        SELECT m.id, m.date::text, th.name AS home_team, ta.name AS away_team
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id = :sid AND m.date >= :start
    """), {"sid": WC_2026_SEASON_ID, "start": WC_R32_START}).fetchall()

    updated = 0
    for r in rows:
        winner = shootout_winners.get((r.date, r.home_team, r.away_team))
        if not winner:
            continue
        label = "[DRY]" if dry_run else "🎯"
        print(f"   {label} penalty winner: {winner} ({r.home_team} vs {r.away_team} {r.date})")
        if not dry_run:
            conn.execute(text(
                "UPDATE matches SET penalty_winner=:w WHERE id=:mid"
            ), {"w": winner, "mid": r.id})
        updated += 1
    return updated


# ── Descargar partidos knockout jugados ───────────────────────────────────────

def fetch_knockout_matches() -> list[dict]:
    """Descarga results.csv y retorna partidos WC 2026 knockout ya jugados."""
    print("📥 Descargando results.csv desde GitHub...")
    resp = requests.get(RESULTS_CSV_URL, timeout=60)
    resp.raise_for_status()
    print(f"   {len(resp.content) // 1024} KB descargados")

    reader = csv.DictReader(io.StringIO(resp.text))
    results: list[dict] = []

    for row in reader:
        date       = row.get("date", "")
        tournament = row.get("tournament", "")
        home_csv   = row.get("home_team", "").strip()
        away_csv   = row.get("away_team", "").strip()
        home_score = row.get("home_score", "").strip()
        away_score = row.get("away_score", "").strip()

        if date < WC_R32_START:
            continue
        if "world cup" not in tournament.lower():
            continue
        if not home_score or not away_score:
            continue

        try:
            hg = int(home_score)
            ag = int(away_score)
        except ValueError:
            continue

        home_db = normalize(home_csv)
        away_db = normalize(away_csv)
        if not home_db or not away_db:
            print(f"   ⚠️  Nombre no mapeado: '{home_csv}' vs '{away_csv}'")
            continue

        results.append({
            "date": date, "home_team": home_db, "away_team": away_db,
            "home_goals": hg, "away_goals": ag,
        })

    print(f"   Partidos knockout WC 2026 en CSV: {len(results)}")
    return results


# ── Obtener team_ids y partidos existentes ────────────────────────────────────

def get_team_ids(conn) -> dict[str, int]:
    rows = conn.execute(text("SELECT id, name FROM teams")).fetchall()
    return {r.name: r.id for r in rows}


def get_existing_knockout_matches(conn) -> dict[tuple, dict]:
    """Retorna {(date, home, away): {id, has_result}} para partidos >= WC_R32_START."""
    rows = conn.execute(text("""
        SELECT m.id, m.date::text, m.home_goals,
               th.name AS home_team, ta.name AS away_team
          FROM matches m
          JOIN teams th ON th.id = m.home_team_id
          JOIN teams ta ON ta.id = m.away_team_id
         WHERE m.season_id = :sid AND m.date >= :start
    """), {"sid": WC_2026_SEASON_ID, "start": WC_R32_START}).fetchall()

    return {
        (r.date, r.home_team, r.away_team): {
            "id": r.id,
            "has_result": r.home_goals is not None,
        }
        for r in rows
    }


# ── Procesar ──────────────────────────────────────────────────────────────────

def process(conn, matches: list[dict], dry_run: bool) -> tuple[int, int, int]:
    team_ids = get_team_ids(conn)
    existing = get_existing_knockout_matches(conn)
    inserted = updated = skipped = 0

    for r in matches:
        key     = (r["date"], r["home_team"], r["away_team"])
        key_rev = (r["date"], r["away_team"], r["home_team"])
        hid = team_ids.get(r["home_team"])
        aid = team_ids.get(r["away_team"])

        if not hid:
            print(f"   ⚠️  Equipo no encontrado en BD: {r['home_team']}")
            continue
        if not aid:
            print(f"   ⚠️  Equipo no encontrado en BD: {r['away_team']}")
            continue

        hg, ag = r["home_goals"], r["away_goals"]

        if key in existing or key_rev in existing:
            rec = existing.get(key) or existing.get(key_rev)
            if rec and not rec["has_result"]:
                # Tiene registro pero sin resultado → actualizar
                reversed_order = key not in existing
                actual_hg = ag if reversed_order else hg
                actual_ag = hg if reversed_order else ag
                label = "[DRY]" if dry_run else "📝"
                print(f"   {label} resultado: {r['home_team']} {hg}-{ag} {r['away_team']} ({r['date']})")
                if not dry_run:
                    conn.execute(text("""
                        UPDATE matches
                        SET home_goals=:hg, away_goals=:ag, fulltime_result=:res
                        WHERE id=:mid
                    """), {
                        "hg": actual_hg, "ag": actual_ag,
                        "res": _fulltime_result(actual_hg, actual_ag),
                        "mid": rec["id"],
                    })
                updated += 1
            else:
                skipped += 1
        else:
            # Registro nuevo
            label = "[DRY]" if dry_run else "✅"
            print(f"   {label} nuevo: {r['home_team']} {hg}-{ag} {r['away_team']} ({r['date']})")
            if not dry_run:
                conn.execute(text("""
                    INSERT INTO matches
                        (season_id, date, home_team_id, away_team_id,
                         home_goals, away_goals, fulltime_result)
                    VALUES
                        (:sid, :date, :hid, :aid, :hg, :ag, :res)
                """), {
                    "sid": WC_2026_SEASON_ID,
                    "date": r["date"],
                    "hid": hid, "aid": aid,
                    "hg": hg, "ag": ag,
                    "res": _fulltime_result(hg, ag),
                })
            inserted += 1

    return inserted, updated, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "ACTUALIZANDO BD"
    print("=" * 60)
    print(f"  WC 2026 Octavos de Final — {mode}")
    print(f"  Fuente: martj42/international_results (results.csv + shootouts.csv)")
    print("=" * 60)

    # Ensure penalty_winner column exists
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS penalty_winner TEXT"
        ))

    matches = fetch_knockout_matches()

    if not matches:
        print("\nℹ️  Sin partidos knockout disponibles en el CSV aún.")
        return

    print(f"\n🔄 Procesando {len(matches)} partido(s)...\n")
    with engine.begin() as conn:
        inserted, updated, skipped = process(conn, matches, dry_run)

    print(f"\n📥 Descargando shootouts.csv...")
    shootout_winners = fetch_shootout_winners()
    if shootout_winners:
        print(f"\n🔄 Actualizando penalty winners...\n")
        with engine.begin() as conn:
            pen_updated = update_penalty_winners(conn, shootout_winners, dry_run)
    else:
        pen_updated = 0

    print(f"\n{'=' * 60}")
    print(f"  Insertados      : {inserted}")
    print(f"  Actualizados    : {updated}")
    print(f"  Ya existían     : {skipped}")
    print(f"  Penalty winners : {pen_updated}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
