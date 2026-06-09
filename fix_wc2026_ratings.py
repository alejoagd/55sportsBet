"""
Recalibra los ratings Weinston del Mundial 2026 (season_id=76)
usando puntos FIFA como proxy de fortaleza actual.

Corrige dos problemas detectados:
  1. mu_away = 2.88 (irreal) → sustituido por parámetros de torneo neutral
  2. 9 equipos con ratings fallback (1.0) por falta de historial en WC

Fórmula de conversión:
  strength = fifa_pts / avg_pts_of_48_teams
  atk_home = atk_away = strength          (equipo fuerte anota más)
  def_home = def_away = 1 / strength      (equipo fuerte concede menos)

Parámetros del torneo (sede neutral):
  mu_home  = mu_away  = 1.35  (~2.7 goles/partido, promedio WC 2010-2022)
  home_adv = 1.0               (sin ventaja local en sede neutral)

Uso:
  python fix_wc2026_ratings.py
"""
from sqlalchemy import text
from src.db import SessionLocal, engine

WC_2026_SEASON_ID = 76

# ── FIFA points (aproximados, escala April 2025) ────────────────────────────
# Fuente: FIFA World Ranking — refleja rendimiento reciente en clasificatorias
# y partidos de selecciones nacionales.
FIFA_POINTS: dict[str, float] = {
    # CONMEBOL
    "Argentina":              1901,
    "Brazil":                 1796,
    "Colombia":               1633,
    "Uruguay":                1627,
    "Ecuador":                1571,
    "Paraguay":               1402,
    # UEFA
    "France":                 1862,
    "England":                1838,
    "Belgium":                1790,
    "Portugal":               1771,
    "Spain":                  1767,
    "Netherlands":            1755,
    "Germany":                1661,
    "Croatia":                1642,
    "Switzerland":            1542,
    "Norway":                 1527,
    "Turkey":                 1510,
    "Scotland":               1327,
    "Austria":                1313,
    "Sweden":                 1309,
    "Czechia":                1290,
    "Bosnia and Herzegovina": 1283,
    # CAF
    "Morocco":                1641,
    "Senegal":                1587,
    "Algeria":                1485,
    "Ivory Coast":            1462,
    "Tunisia":                1411,
    "Egypt":                  1399,
    "Ghana":                  1385,
    "South Africa":           1367,
    "Congo DR":               1348,
    "Cape Verde":             1232,
    # AFC
    "Japan":                  1601,
    "South Korea":            1564,
    "Australia":              1549,
    "Iran":                   1412,
    "Saudi Arabia":           1389,
    "Qatar":                  1296,
    "Uzbekistan":             1265,
    "Jordan":                 1241,
    "Iraq":                   1210,
    # CONCACAF
    "United States":          1621,
    "Mexico":                 1617,
    "Canada":                 1545,
    "Panama":                 1230,
    "Haiti":                  1195,
    "Curacao":                1165,
    # OFC
    "New Zealand":            1272,
}

# Parámetros de torneo neutral (WC moderno, promedios 2010-2022)
MU_HOME  = 1.35
MU_AWAY  = 1.35
HOME_ADV = 1.00   # sin ventaja de local en sede neutral


def main() -> None:
    print("=" * 60)
    print("  Recalibrando ratings WC 2026 con puntos FIFA")
    print("=" * 60)

    # 1. Obtener todos los equipos del WC 2026
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT t.id, t.name, wr.league_id
            FROM teams t
            JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            LEFT JOIN weinston_ratings wr
                   ON wr.team_id = t.id AND wr.season_id = :sid
            WHERE m.season_id = :sid
        """), {"sid": WC_2026_SEASON_ID}).fetchall()

    teams = {r.name: {"id": r.id, "league_id": r.league_id} for r in rows}
    league_id = next(
        (v["league_id"] for v in teams.values() if v["league_id"]), None
    )

    # Mapear por nombre exacto
    matched: dict[str, dict] = {}
    unmatched: list[str] = []
    for db_name, info in teams.items():
        if db_name in FIFA_POINTS:
            matched[db_name] = {**info, "fifa_pts": FIFA_POINTS[db_name]}
        else:
            unmatched.append(db_name)

    if unmatched:
        print(f"\n⚠️  Equipos sin puntos FIFA mapeados ({len(unmatched)}):")
        for n in unmatched:
            print(f"   - {n}")

    # 2. Calcular fortaleza normalizada
    all_pts = list(FIFA_POINTS.values())
    avg_pts = sum(all_pts) / len(all_pts)
    print(f"\nPuntos FIFA promedio (48 equipos): {avg_pts:.0f}")

    print(f"\n{'Equipo':<30} {'FIFA pts':>8}  {'strength':>8}  {'atk':>6}  {'def':>6}")
    print("-" * 65)

    ratings: dict[int, dict] = {}
    for name, info in sorted(matched.items(), key=lambda x: -x[1]["fifa_pts"]):
        pts = info["fifa_pts"]
        strength = pts / avg_pts
        atk = strength          # lineal: equipo top ~1.30, equipo débil ~0.80
        defn = 1.0 / strength   # inverso: top defiende bien (< 1), débil defiende mal (> 1)
        ratings[info["id"]] = {
            "atk_home": atk, "def_home": defn,
            "atk_away": atk, "def_away": defn,
        }
        print(f"{name:<30} {pts:>8.0f}  {strength:>8.4f}  {atk:>6.4f}  {defn:>6.4f}")

    # Teams sin mapeo → fallback neutro (1.0)
    for name in unmatched:
        tid = teams[name]["id"]
        ratings[tid] = {"atk_home": 1.0, "def_home": 1.0, "atk_away": 1.0, "def_away": 1.0}
        print(f"{name:<30} {'N/A':>8}  {'1.0000':>8}  {'1.0000':>6}  {'1.0000':>6}  (fallback)")

    # 3. Actualizar BD
    print(f"\n{'─'*60}")
    print("  Actualizando ratings en BD...")

    with SessionLocal() as session:
        for team_id, r in ratings.items():
            session.execute(text("""
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

        # 4. Actualizar parámetros del torneo
        session.execute(text("""
            INSERT INTO weinston_params (season_id, mu_home, mu_away, home_adv, loss)
            VALUES (:sid, :mh, :ma, :ha, 0.0)
            ON CONFLICT (season_id) DO UPDATE SET
                mu_home  = EXCLUDED.mu_home,
                mu_away  = EXCLUDED.mu_away,
                home_adv = EXCLUDED.home_adv
        """), {"sid": WC_2026_SEASON_ID, "mh": MU_HOME, "ma": MU_AWAY, "ha": HOME_ADV})

        session.commit()

    print(f"\nRatings actualizados : {len(ratings)} equipos")
    print(f"Parámetros torneo    : mu_home={MU_HOME}  mu_away={MU_AWAY}  home_adv={HOME_ADV}")
    print("\n" + "=" * 60)
    print("  Listo. Ahora re-ejecuta las predicciones:")
    print(f"  python -m src.predictions.cli upcoming --season-id {WC_2026_SEASON_ID} "
          f"--from 2026-06-11 --to 2026-07-19")
    print("=" * 60)


if __name__ == "__main__":
    main()
