"""
Descarga los resultados más recientes desde martj42/international_results
y actualiza los marcadores de los partidos del Mundial 2026 (season_id=76).

FUENTE: https://github.com/martj42/international_results
  → results.csv: ~50k partidos históricos, se actualiza pocas horas después
    de cada partido internacional. El torneo FIFA World Cup aparece como
    tournament = "FIFA World Cup".

LÓGICA:
  1. Descarga results.csv desde raw.githubusercontent.com
  2. Filtra partidos con fecha >= 2026-06-11 y tournament = "FIFA World Cup"
     que ya tengan marcador (home_score / away_score no vacíos)
  3. Para cada partido encontrado, busca en nuestra BD (season_id=76)
     cruzando por fecha + nombres de equipo normalizados
  4. Si el partido está sin resultado en BD → actualiza home_goals/away_goals

Ejecutar manualmente o vía GitHub Actions:
  python update_wc2026_results.py
  python update_wc2026_results.py --dry-run
"""
from __future__ import annotations
import sys
import io
import csv
from datetime import date as DateType
from sqlalchemy import text
from src.db import engine

# ── Constantes ───────────────────────────────────────────────────────────────
WC_2026_SEASON_ID = 76
WC_START_DATE     = "2026-06-11"
WC_END_DATE       = "2026-07-19"

RESULTS_CSV_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/results.csv"
)

# ── Mapeo CSV → nombre en BD ─────────────────────────────────────────────────
# Reutiliza la misma lógica de ingest_qualifiers.py para consistencia.
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
}

# Equipos que aparecen con el mismo nombre en CSV y BD
_PASSTHROUGH = {
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Paraguay",
    "France", "England", "Belgium", "Portugal", "Spain", "Netherlands",
    "Germany", "Croatia", "Switzerland", "Norway", "Turkey", "Scotland",
    "Austria", "Sweden", "Morocco", "Senegal", "Algeria", "Tunisia",
    "Egypt", "Ghana", "South Africa", "Japan", "Australia", "Iran",
    "Saudi Arabia", "Qatar", "Uzbekistan", "Jordan", "Iraq",
    "Mexico", "Canada", "Panama", "Haiti", "Curacao", "New Zealand",
}


def normalize_name(csv_name: str) -> str | None:
    if csv_name in CSV_TO_DB:
        return CSV_TO_DB[csv_name]
    if csv_name in _PASSTHROUGH:
        return csv_name
    return None


# ── Paso 1: Descargar y filtrar ──────────────────────────────────────────────

def fetch_wc2026_results() -> list[dict]:
    import requests
    print(f"📥 Descargando results.csv desde GitHub...")
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

        # Solo partidos del Mundial 2026
        if not (WC_START_DATE <= date <= WC_END_DATE):
            continue
        if "world cup" not in tournament.lower():
            continue
        # Solo partidos terminados
        if not home_score or not away_score:
            continue
        try:
            hg = int(home_score)
            ag = int(away_score)
        except ValueError:
            continue

        home_db = normalize_name(home_csv)
        away_db = normalize_name(away_csv)
        if not home_db or not away_db:
            print(f"   ⚠️  Nombre no mapeado: '{home_csv}' vs '{away_csv}'")
            continue

        results.append({
            "date":       date,
            "home_team":  home_db,
            "away_team":  away_db,
            "home_goals": hg,
            "away_goals": ag,
        })

    print(f"   Partidos WC 2026 con resultado en CSV: {len(results)}")
    return results


# ── Paso 2: Actualizar BD ────────────────────────────────────────────────────

def _fulltime_result(hg: int, ag: int) -> str:
    if hg > ag: return "H"
    if ag > hg: return "A"
    return "D"


def update_db(results: list[dict], dry_run: bool = False) -> tuple[int, int, int]:
    """
    Retorna (actualizados, ya_tenían_resultado, no_encontrados).
    """
    updated   = 0
    skipped   = 0
    not_found = 0

    with engine.begin() as conn:
        for r in results:
            row = conn.execute(text("""
                SELECT m.id, m.home_goals
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE m.season_id = :sid
                  AND ht.name    = :home
                  AND at.name    = :away
                  AND m.date     = :date
            """), {
                "sid":  WC_2026_SEASON_ID,
                "home": r["home_team"],
                "away": r["away_team"],
                "date": r["date"],
            }).fetchone()

            if not row:
                print(f"   ⚠️  No encontrado en BD: {r['home_team']} vs {r['away_team']} ({r['date']})")
                not_found += 1
                continue

            if row.home_goals is not None:
                skipped += 1
                continue  # Ya tiene resultado

            label = "[DRY]" if dry_run else "✅"
            print(f"   {label} {r['home_team']} {r['home_goals']}-{r['away_goals']} {r['away_team']}  ({r['date']})")

            if not dry_run:
                conn.execute(text("""
                    UPDATE matches
                    SET home_goals      = :hg,
                        away_goals      = :ag,
                        fulltime_result = :res
                    WHERE id = :mid
                """), {
                    "hg":  r["home_goals"],
                    "ag":  r["away_goals"],
                    "res": _fulltime_result(r["home_goals"], r["away_goals"]),
                    "mid": row.id,
                })
            updated += 1

    return updated, skipped, not_found


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "ACTUALIZANDO BD"
    print("=" * 60)
    print(f"  WC 2026 Results Updater — {mode}")
    print(f"  Fuente: martj42/international_results")
    print("=" * 60)

    results = fetch_wc2026_results()

    if not results:
        print("\nℹ️  Sin resultados nuevos disponibles en el CSV.")
        return

    print(f"\n🔄 Procesando {len(results)} partido(s)...\n")
    updated, skipped, not_found = update_db(results, dry_run=dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Actualizados  : {updated}")
    print(f"  Ya tenían res : {skipped}")
    print(f"  No encontrados: {not_found}")
    if dry_run:
        print("  (Dry run — nada fue modificado)")
    print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
