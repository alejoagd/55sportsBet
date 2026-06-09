"""
Descarga los resultados internacionales de selecciones (2022-2025) desde
github.com/martj42/international_results y entrena ratings Weinston reales
para los 48 equipos del Mundial 2026.

FLUJO:
  1. Descarga results.csv (~50k partidos, actualizado regularmente)
  2. Filtra partidos 2022-2025 que incluyan al menos un equipo del WC 2026
     (clasificatorias + continentales + Nations League, excluye amistosos)
  3. Crea en BD: liga "WC 2026 Qualifiers" + temporada + equipos + partidos
  4. Entrena fit_weinston con regularización fuerte (λ=0.08) sobre esos datos
  5. Para los 48 equipos del WC 2026: mezcla 60% ratings reales + 40% FIFA pts
  6. Guarda en weinston_ratings para season_id=76
  7. Mantiene parámetros neutrales: mu=1.35, home_adv=1.0

REQUISITO: ejecutar en un entorno con acceso a internet (Render Shell).
  python ingest_qualifiers.py

Para solo ver qué datos se descargarían sin escribir en BD:
  python ingest_qualifiers.py --dry-run
"""
from __future__ import annotations
import sys
import io
import math
import requests
import numpy as np
from scipy.optimize import minimize, LinearConstraint, Bounds
from sqlalchemy import text
from src.db import SessionLocal, engine

# ── Configuración ────────────────────────────────────────────────────────────
WC_2026_SEASON_ID  = 76
DATE_FROM          = "2022-01-01"
DATE_TO            = "2025-12-31"
REGULARIZATION     = 0.08   # más fuerte que 1e-3 para muestras pequeñas
BLEND_WC           = 0.60   # 60% ratings entrenados con resultados reales
BLEND_FIFA         = 0.40   # 40% ratings basados en puntos FIFA

RESULTS_CSV_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/results.csv"
)

# Torneos a incluir (excluye amistosos, incluye todo lo competitivo)
COMPETITIVE_KEYWORDS = [
    "world cup",
    "qualification",
    "qualifier",
    "nations league",
    "copa america",
    "africa cup",
    "afcon",
    "asian cup",
    "concacaf gold cup",
    "euro ",
    "uefa euro",
    "oceania",
    "ofc",
    "finalissima",
]

# ── Puntos FIFA (proxy) — mismos que fix_wc2026_ratings.py ──────────────────
FIFA_POINTS: dict[str, float] = {
    "Argentina": 1901, "Brazil": 1796, "Colombia": 1633, "Uruguay": 1627,
    "Ecuador": 1571, "Paraguay": 1402,
    "France": 1862, "England": 1838, "Belgium": 1790, "Portugal": 1771,
    "Spain": 1767, "Netherlands": 1755, "Germany": 1661, "Croatia": 1642,
    "Switzerland": 1542, "Norway": 1527, "Turkey": 1510, "Scotland": 1327,
    "Austria": 1313, "Sweden": 1309, "Czechia": 1290,
    "Bosnia and Herzegovina": 1283,
    "Morocco": 1641, "Senegal": 1587, "Algeria": 1485, "Ivory Coast": 1462,
    "Tunisia": 1411, "Egypt": 1399, "Ghana": 1385, "South Africa": 1367,
    "Congo DR": 1348, "Cape Verde": 1232,
    "Japan": 1601, "South Korea": 1564, "Australia": 1549, "Iran": 1412,
    "Saudi Arabia": 1389, "Qatar": 1296, "Uzbekistan": 1265, "Jordan": 1241,
    "Iraq": 1210,
    "United States": 1621, "Mexico": 1617, "Canada": 1545, "Panama": 1230,
    "Haiti": 1195, "Curacao": 1165,
    "New Zealand": 1272,
}
ATK_POWER  = 2.5
DEF_POWER  = 0.5
MU_HOME    = 1.35
MU_AWAY    = 1.35
HOME_ADV   = 1.00

# ── Mapeo: nombre en CSV → nombre en BD ─────────────────────────────────────
# El CSV usa algunos nombres distintos a los de nuestra BD.
CSV_TO_DB: dict[str, str] = {
    # CONMEBOL
    "Bolivia":                  "Bolivia",
    "Chile":                    "Chile",
    "Colombia":                 "Colombia",
    "Ecuador":                  "Ecuador",
    "Paraguay":                 "Paraguay",
    "Peru":                     "Peru",
    "Uruguay":                  "Uruguay",
    "Venezuela":                "Venezuela",
    # UEFA
    "Bosnia-Herzegovina":       "Bosnia and Herzegovina",
    "Bosnia and Herzegovina":   "Bosnia and Herzegovina",
    "Czech Republic":           "Czechia",
    "Czechia":                  "Czechia",
    "Northern Ireland":         "Northern Ireland",
    # CAF
    "Ivory Coast":              "Ivory Coast",
    "Côte d'Ivoire":            "Ivory Coast",
    "Cote d'Ivoire":            "Ivory Coast",
    "DR Congo":                 "Congo DR",
    "Democratic Republic of the Congo": "Congo DR",
    "Cape Verde":               "Cape Verde",
    "Cabo Verde":               "Cape Verde",
    "South Africa":             "South Africa",
    # AFC
    "Korea Republic":           "South Korea",
    "South Korea":              "South Korea",
    "IR Iran":                  "Iran",
    "Saudi Arabia":             "Saudi Arabia",
    # CONCACAF
    "United States":            "United States",
    "USA":                      "United States",
    # Neutral names that match directly (no mapping needed but listed for clarity)
    "Argentina": "Argentina", "France": "France", "Brazil": "Brazil",
    "England": "England", "Belgium": "Belgium", "Portugal": "Portugal",
    "Spain": "Spain", "Netherlands": "Netherlands", "Germany": "Germany",
    "Croatia": "Croatia", "Morocco": "Morocco", "Senegal": "Senegal",
    "Algeria": "Algeria", "Tunisia": "Tunisia", "Egypt": "Egypt",
    "Ghana": "Ghana", "Japan": "Japan", "Australia": "Australia",
    "Canada": "Canada", "Mexico": "Mexico", "Panama": "Panama",
    "Uruguay": "Uruguay", "Norway": "Norway", "Turkey": "Turkey",
    "Scotland": "Scotland", "Austria": "Austria", "Sweden": "Sweden",
    "Switzerland": "Switzerland", "Qatar": "Qatar", "Uzbekistan": "Uzbekistan",
    "Jordan": "Jordan", "Iraq": "Iraq", "Haiti": "Haiti",
    "Curacao": "Curacao", "New Zealand": "New Zealand",
}

# Nombres en BD de los 48 equipos clasificados
WC_2026_TEAMS = set(FIFA_POINTS.keys())


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_competitive(tournament: str) -> bool:
    t = tournament.lower()
    return any(kw in t for kw in COMPETITIVE_KEYWORDS)


def normalize_name(csv_name: str) -> str | None:
    """Devuelve nombre canónico en BD o None si no es equipo relevante."""
    if csv_name in CSV_TO_DB:
        return CSV_TO_DB[csv_name]
    if csv_name in WC_2026_TEAMS:
        return csv_name
    return None


# ── Paso 1: Descarga y filtrado ──────────────────────────────────────────────

def download_and_filter() -> list[dict]:
    print("📥 Descargando results.csv desde GitHub...")
    resp = requests.get(RESULTS_CSV_URL, timeout=60)
    resp.raise_for_status()
    print(f"   {len(resp.content) // 1024} KB descargados")

    import csv
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"   Total partidos en CSV: {len(rows)}")

    filtered = []
    for r in rows:
        date = r.get("date", "")
        if not (DATE_FROM <= date <= DATE_TO):
            continue
        tournament = r.get("tournament", "")
        if not is_competitive(tournament):
            continue

        home_db = normalize_name(r["home_team"])
        away_db = normalize_name(r["away_team"])

        # Al menos uno debe ser equipo del WC 2026
        if home_db not in WC_2026_TEAMS and away_db not in WC_2026_TEAMS:
            continue

        try:
            hg = int(r["home_score"])
            ag = int(r["away_score"])
        except (ValueError, KeyError):
            continue  # Partido sin resultado aún

        filtered.append({
            "date":       date,
            "home_name":  home_db or r["home_team"],
            "away_name":  away_db or r["away_team"],
            "home_goals": hg,
            "away_goals": ag,
            "neutral":    r.get("neutral", "False") == "True",
            "tournament": tournament,
        })

    print(f"   Partidos competitivos 2022-2025 con WC 2026 teams: {len(filtered)}")
    return filtered


# ── Paso 2: Insertar en BD ───────────────────────────────────────────────────

def get_or_create_league(conn) -> int:
    row = conn.execute(text(
        "SELECT id FROM leagues WHERE name = 'WC 2026 Qualifiers'"
    )).fetchone()
    if row:
        return row.id
    row = conn.execute(text(
        "INSERT INTO leagues (name, country) VALUES ('WC 2026 Qualifiers', 'International') RETURNING id"
    )).fetchone()
    return row.id


def get_or_create_season(conn, league_id: int) -> int:
    row = conn.execute(text(
        "SELECT id FROM seasons WHERE league_id = :lid AND year_start = 2022"
    ), {"lid": league_id}).fetchone()
    if row:
        return row.id
    row = conn.execute(text(
        "INSERT INTO seasons (league_id, year_start, year_end) VALUES (:lid, 2022, 2025) RETURNING id"
    ), {"lid": league_id}).fetchone()
    return row.id


def get_or_create_team(conn, name: str) -> int:
    row = conn.execute(text("SELECT id FROM teams WHERE name = :n"), {"n": name}).fetchone()
    if row:
        return row.id
    row = conn.execute(text(
        "INSERT INTO teams (name) VALUES (:n) RETURNING id"
    ), {"n": name}).fetchone()
    return row.id


def insert_matches(matches: list[dict]) -> int:
    """Inserta partidos en BD y devuelve el season_id creado."""
    with engine.begin() as conn:
        league_id = get_or_create_league(conn)
        season_id = get_or_create_season(conn, league_id)

        # Limpiar partidos existentes de esta temporada (re-run seguro)
        conn.execute(text("DELETE FROM matches WHERE season_id = :sid"), {"sid": season_id})

        inserted = 0
        for m in matches:
            home_id = get_or_create_team(conn, m["home_name"])
            away_id = get_or_create_team(conn, m["away_name"])
            conn.execute(text("""
                INSERT INTO matches
                    (season_id, date, home_team_id, away_team_id, home_goals, away_goals)
                VALUES (:sid, :d, :h, :a, :hg, :ag)
            """), {
                "sid": season_id, "d": m["date"],
                "h": home_id, "a": away_id,
                "hg": m["home_goals"], "ag": m["away_goals"],
            })
            inserted += 1

    print(f"   {inserted} partidos insertados en season_id={season_id} (liga: WC 2026 Qualifiers)")
    return season_id


# ── Paso 3: Entrenar Weinston con regularización fuerte ─────────────────────

def fit_with_regularization(season_id: int) -> dict:
    """Entrena ratings con λ=REGULARIZATION para evitar overfitting."""
    with SessionLocal() as s:
        rows = s.execute(text("""
            SELECT home_team_id, away_team_id, home_goals, away_goals
            FROM matches
            WHERE season_id = :sid AND home_goals IS NOT NULL
        """), {"sid": season_id}).fetchall()

    if len(rows) < 10:
        raise ValueError(f"Solo {len(rows)} partidos — insuficiente para entrenar.")

    all_ids = set()
    for r in rows:
        all_ids.add(r.home_team_id)
        all_ids.add(r.away_team_id)

    team_ids = sorted(all_ids)
    idx = {tid: i for i, tid in enumerate(team_ids)}
    n = len(team_ids)

    H  = np.array([idx[r.home_team_id] for r in rows])
    A  = np.array([idx[r.away_team_id] for r in rows])
    HG = np.array([r.home_goals for r in rows], float)
    AG = np.array([r.away_goals for r in rows], float)

    mu_h0 = float(np.mean(HG))
    mu_a0 = float(np.mean(AG))
    x0 = np.r_[np.ones(n), np.ones(n), np.ones(n), np.ones(n), mu_h0, mu_a0, 1.1]

    def unp(x):
        aL = x[0:n].clip(0.1, 10)
        dA = x[n:2*n].clip(0.1, 10)
        aA = x[2*n:3*n].clip(0.1, 10)
        dH = x[3*n:4*n].clip(0.1, 10)
        mh = max(0.1, min(5.0, x[4*n]))
        ma = max(0.1, min(5.0, x[4*n+1]))
        ha = max(0.5, min(4.0, x[4*n+2]))
        return aL, dH, aA, dA, mh, ma, ha

    def loss(x):
        aL, dH, aA, dA, mh, ma, ha = unp(x)
        lh = np.clip(mh * aL[H] * dA[A] * ha, 1e-6, 50)
        la = np.clip(ma * aA[A] * dH[H], 1e-6, 50)
        nll = np.sum(lh - HG * np.log(lh) + la - AG * np.log(la))
        reg = REGULARIZATION * (
            np.sum((aL - 1)**2) + np.sum((aA - 1)**2) +
            np.sum((dH - 1)**2) + np.sum((dA - 1)**2)
        )
        return nll + reg

    Aeq = np.zeros((4, x0.size))
    Aeq[0, 0:n] = 1/n;      Aeq[1, n:2*n] = 1/n
    Aeq[2, 2*n:3*n] = 1/n;  Aeq[3, 3*n:4*n] = 1/n
    lc  = LinearConstraint(Aeq, [1,1,1,1], [1,1,1,1])
    bnd = Bounds(np.r_[np.full(4*n, 0.1), 0.1, 0.1, 0.5],
                 np.r_[np.full(4*n, 10),  5.0, 5.0, 4.0])

    print(f"   Entrenando Weinston: {n} equipos, {len(rows)} partidos, λ={REGULARIZATION}...")
    res = minimize(loss, x0, method="trust-constr",
                   constraints=[lc], bounds=bnd,
                   options={"gtol": 1e-4, "xtol": 1e-4, "maxiter": 600})

    aL, dH, aA, dA, mh, ma, ha = unp(res.x)
    print(f"   Convergencia: {'OK' if res.success else 'parcial'}  loss={res.fun:.1f}")
    print(f"   μ_home={mh:.3f}  μ_away={ma:.3f}  HFA={ha:.3f}")

    return {
        "team_ids": team_ids,
        "atk_home": {tid: float(aL[i]) for i, tid in enumerate(team_ids)},
        "def_home": {tid: float(dH[i]) for i, tid in enumerate(team_ids)},
        "atk_away": {tid: float(aA[i]) for i, tid in enumerate(team_ids)},
        "def_away": {tid: float(dA[i]) for i, tid in enumerate(team_ids)},
    }


# ── Paso 4: Mezcla ratings reales + FIFA points ──────────────────────────────

def compute_fifa_rating(pts: float, avg_pts: float) -> dict:
    s = pts / avg_pts
    return {
        "atk_home": s ** ATK_POWER,
        "def_home": (1.0 / s) ** DEF_POWER,
        "atk_away": s ** ATK_POWER,
        "def_away": (1.0 / s) ** DEF_POWER,
    }


def blend_ratings(trained: dict) -> dict[int, dict]:
    """
    Para cada equipo del WC 2026:
      - Si tiene rating entrenado: mezcla BLEND_WC * real + BLEND_FIFA * fifa
      - Si no:                     usa 100% fifa
    Devuelve {team_id: {atk_home, def_home, atk_away, def_away}}
    """
    avg_pts = sum(FIFA_POINTS.values()) / len(FIFA_POINTS)

    # Mapeo nombre_bd → team_id para los 48 equipos del WC 2026
    with SessionLocal() as s:
        wc26_rows = s.execute(text("""
            SELECT DISTINCT t.id, t.name
            FROM matches m
            JOIN teams t ON t.id IN (m.home_team_id, m.away_team_id)
            WHERE m.season_id = :sid
        """), {"sid": WC_2026_SEASON_ID}).fetchall()
    name_to_id = {r.name: r.id for r in wc26_rows}

    # Mapeo team_id → nombre para el dict entrenado
    with SessionLocal() as s:
        id_to_name = {r.id: r.name for r in s.execute(text(
            "SELECT id, name FROM teams WHERE id = ANY(:ids)"
        ), {"ids": trained["team_ids"]}).fetchall()}

    result: dict[int, dict] = {}
    covered_trained = 0
    covered_fifa_only = 0

    for db_name, team_id in sorted(name_to_id.items()):
        fifa_r = compute_fifa_rating(FIFA_POINTS.get(db_name, avg_pts), avg_pts)

        # ¿Tiene rating entrenado?
        if team_id in trained["atk_home"]:
            tr = {
                "atk_home": trained["atk_home"][team_id],
                "def_home": trained["def_home"][team_id],
                "atk_away": trained["atk_away"][team_id],
                "def_away": trained["def_away"][team_id],
            }
            blended = {
                k: BLEND_WC * tr[k] + BLEND_FIFA * fifa_r[k]
                for k in tr
            }
            result[team_id] = blended
            covered_trained += 1
        else:
            result[team_id] = fifa_r
            covered_fifa_only += 1

    print(f"\n   Con datos clasificatorios : {covered_trained}/48")
    print(f"   Solo puntos FIFA          : {covered_fifa_only}/48")
    return result


# ── Paso 5: Guardar ratings en season_id=76 ──────────────────────────────────

def save_to_wc2026(ratings: dict[int, dict]) -> None:
    with SessionLocal() as s, s.begin():
        # league_id para WC 2026
        league_id = s.execute(text("""
            SELECT s.league_id FROM seasons s WHERE s.id = :sid
        """), {"sid": WC_2026_SEASON_ID}).scalar()

        for team_id, r in ratings.items():
            s.execute(text("""
                INSERT INTO weinston_ratings
                    (season_id, team_id, league_id, atk_home, def_home, atk_away, def_away)
                VALUES
                    (:sid, :tid, :lid, :ah, :dh, :aa, :da)
                ON CONFLICT (season_id, team_id) DO UPDATE SET
                    atk_home = EXCLUDED.atk_home,
                    def_home = EXCLUDED.def_home,
                    atk_away = EXCLUDED.atk_away,
                    def_away = EXCLUDED.def_away
            """), {
                "sid": WC_2026_SEASON_ID, "tid": team_id, "lid": league_id,
                "ah": r["atk_home"], "dh": r["def_home"],
                "aa": r["atk_away"], "da": r["def_away"],
            })

        # Asegurar parámetros neutrales
        s.execute(text("""
            INSERT INTO weinston_params (season_id, mu_home, mu_away, home_adv, loss)
            VALUES (:sid, :mh, :ma, :ha, 0.0)
            ON CONFLICT (season_id) DO UPDATE SET
                mu_home  = EXCLUDED.mu_home,
                mu_away  = EXCLUDED.mu_away,
                home_adv = EXCLUDED.home_adv
        """), {"sid": WC_2026_SEASON_ID, "mh": MU_HOME, "ma": MU_AWAY, "ha": HOME_ADV})

    print(f"\n   {len(ratings)} ratings guardados para season_id={WC_2026_SEASON_ID}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    print("=" * 65)
    print("  Ingestión de clasificatorias WC 2026")
    print("=" * 65)

    # 1. Descargar y filtrar
    matches = download_and_filter()
    if not matches:
        print("ERROR: No se encontraron partidos. Verifica la conexión.")
        return

    # Estadísticas por equipo
    from collections import Counter
    match_count: Counter = Counter()
    for m in matches:
        if m["home_name"] in WC_2026_TEAMS:
            match_count[m["home_name"]] += 1
        if m["away_name"] in WC_2026_TEAMS:
            match_count[m["away_name"]] += 1

    print(f"\nPartidos por equipo WC 2026 (top 10 / bottom 10):")
    sorted_teams = sorted(match_count.items(), key=lambda x: -x[1])
    for name, cnt in sorted_teams[:10]:
        print(f"  {name:<28} {cnt:>3} partidos")
    print("  ...")
    for name, cnt in sorted_teams[-10:]:
        print(f"  {name:<28} {cnt:>3} partidos")

    sin_datos = [t for t in WC_2026_TEAMS if t not in match_count]
    if sin_datos:
        print(f"\nEquipos sin datos competitivos (usarán solo FIFA pts): {sin_datos}")

    if dry_run:
        print("\n[DRY RUN] No se escribió nada en BD.")
        return

    # 2. Insertar en BD
    print("\n📦 Insertando partidos en BD...")
    qualifier_season_id = insert_matches(matches)

    # 3. Entrenar Weinston
    print("\n🔧 Entrenando ratings Weinston...")
    trained = fit_with_regularization(qualifier_season_id)

    # 4. Mezclar con FIFA
    print("\n⚖️  Mezclando ratings reales + FIFA points...")
    final_ratings = blend_ratings(trained)

    # 5. Mostrar comparación
    avg_pts = sum(FIFA_POINTS.values()) / len(FIFA_POINTS)
    print(f"\n{'Equipo':<28} {'atk_real':>9} {'atk_fifa':>9} {'atk_final':>10}  {'def_final':>10}")
    print("-" * 72)
    with SessionLocal() as s:
        id_name = {r.id: r.name for r in s.execute(text(
            "SELECT id, name FROM teams"
        )).fetchall()}
    for tid, r in sorted(final_ratings.items(), key=lambda x: -x[1]["atk_home"])[:15]:
        name = id_name.get(tid, str(tid))
        fifa_r = compute_fifa_rating(FIFA_POINTS.get(name, avg_pts), avg_pts)
        trained_atk = trained["atk_home"].get(tid, None)
        print(f"{name:<28} {str(round(trained_atk,3)) if trained_atk else 'N/A':>9}"
              f" {fifa_r['atk_home']:>9.3f} {r['atk_home']:>10.3f}  {r['def_home']:>10.3f}")

    # 6. Guardar
    print("\n💾 Guardando en BD (season_id=76)...")
    save_to_wc2026(final_ratings)

    print(f"\n{'='*65}")
    print("  Listo. Regenera predicciones:")
    print(f"  python -m src.predictions.cli upcoming --season-id 76 "
          f"--from 2026-06-11 --to 2026-07-19")
    print("=" * 65)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
