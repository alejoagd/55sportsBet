"""
Genera ratings Weinston para el Mundial 2026 (season_id=76)
usando los datos históricos de los Mundiales 2006, 2010 y 2014.

Pasos:
1. Entrena Weinston en cada uno de los últimos 3 Mundiales con resultados
2. Para cada equipo del Mundial 2026, busca su rating más reciente
3. Inserta esos ratings en weinston_ratings para season_id=76
4. Inserta parámetros de liga promediando los últimos Mundiales

Uso:
  python populate_wc2026_ratings.py
"""
from sqlalchemy import text
from src.db import SessionLocal, engine
from src.weinston.fit import fit_weinston, save_ratings, save_league_params

WC_2026_SEASON_ID = 76
TRAINING_SEASONS = []  # se llenan dinámicamente
TARGET_RECENT_WC_COUNT = 3  # usar los últimos N Mundiales con datos suficientes


def get_wc_seasons_with_results(conn):
    """Obtiene todos los Mundiales con resultados completos, ordenados por año desc."""
    rows = conn.execute(text("""
        SELECT s.id, s.year_start, COUNT(m.id) as matches_with_results
        FROM seasons s
        JOIN leagues l ON l.id = s.league_id
        JOIN matches m ON m.season_id = s.id
        WHERE l.name = 'FIFA World Cup'
          AND m.home_goals IS NOT NULL
          AND m.away_goals IS NOT NULL
          AND s.id != :wc2026
        GROUP BY s.id, s.year_start
        HAVING COUNT(m.id) >= 20
        ORDER BY s.year_start DESC
    """), {"wc2026": WC_2026_SEASON_ID}).fetchall()
    return rows


def get_teams_in_2026(conn):
    """Retorna todos los team_ids que jugarán el Mundial 2026."""
    rows = conn.execute(text("""
        SELECT DISTINCT team_id FROM (
            SELECT home_team_id as team_id FROM matches WHERE season_id = :sid
            UNION
            SELECT away_team_id as team_id FROM matches WHERE season_id = :sid
        ) t
    """), {"sid": WC_2026_SEASON_ID}).fetchall()
    return {r.team_id for r in rows}


def get_league_id_for_season(conn, season_id):
    row = conn.execute(
        text("SELECT league_id FROM seasons WHERE id = :sid"),
        {"sid": season_id}
    ).fetchone()
    return row.league_id if row else None


def get_existing_ratings(conn, season_ids):
    """Obtiene todos los ratings de las temporadas indicadas."""
    rows = conn.execute(text("""
        SELECT season_id, team_id, atk_home, def_home, atk_away, def_away
        FROM weinston_ratings
        WHERE season_id = ANY(:sids)
    """), {"sids": list(season_ids)}).fetchall()
    return rows


def main():
    print("=" * 60)
    print("  Generando ratings Weinston para Mundial 2026")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. Obtener Mundiales históricos con resultados
        wc_seasons = get_wc_seasons_with_results(conn)
        if not wc_seasons:
            print("ERROR: No hay Mundiales históricos con resultados en la BD.")
            return

        print(f"\nMundiales disponibles para entrenamiento:")
        for s in wc_seasons:
            print(f"  Season {s.id}: World Cup {s.year_start} ({s.matches_with_results} partidos)")

        # Usar los últimos N Mundiales
        training_seasons = wc_seasons[:TARGET_RECENT_WC_COUNT]
        training_ids = [s.id for s in training_seasons]
        print(f"\nUsando para entrenamiento: {[s.year_start for s in training_seasons]}")

    # 2. Entrenar Weinston en cada temporada histórica
    print("\n" + "-" * 60)
    print("  Entrenando modelo Weinston en Mundiales históricos...")
    print("-" * 60)

    trained_ids = []
    with SessionLocal() as s:
        for season in training_seasons:
            try:
                print(f"\nEntrenando World Cup {season.year_start} (season_id={season.id})...")
                result = fit_weinston(s, season.id)
                save_ratings(season.id, result.team_ids, result.atk_home,
                             result.def_home, result.atk_away, result.def_away)
                save_league_params(season.id, float(result.mu_home),
                                   float(result.mu_away), float(result.home_adv),
                                   float(result.loss))
                trained_ids.append(season.id)
                print(f"  OK: {len(result.team_ids)} equipos entrenados")
            except Exception as e:
                print(f"  SKIP: {e}")

    if not trained_ids:
        print("\nERROR: No se pudo entrenar ninguna temporada.")
        return

    # 3. Copiar ratings más recientes a season 76
    print("\n" + "-" * 60)
    print("  Copiando ratings a Mundial 2026 (season_id=76)...")
    print("-" * 60)

    with engine.connect() as conn:
        teams_2026 = get_teams_in_2026(conn)
        league_id = get_league_id_for_season(conn, WC_2026_SEASON_ID)
        all_ratings = get_existing_ratings(conn, trained_ids)

        # Para cada equipo tomar el rating del Mundial más reciente disponible
        # (trained_ids ya está ordenado desc por año)
        best_rating = {}
        for r in all_ratings:
            tid = r.team_id
            if tid not in best_rating:
                best_rating[tid] = r

        # Promediar parámetros de liga de los Mundiales entrenados
        params_rows = conn.execute(text("""
            SELECT mu_home, mu_away, home_adv
            FROM weinston_params
            WHERE season_id = ANY(:sids)
        """), {"sids": trained_ids}).fetchall()

        if params_rows:
            avg_mu_home = sum(p.mu_home for p in params_rows) / len(params_rows)
            avg_mu_away = sum(p.mu_away for p in params_rows) / len(params_rows)
            avg_home_adv = sum(p.home_adv for p in params_rows) / len(params_rows)
        else:
            avg_mu_home, avg_mu_away, avg_home_adv = 1.4, 1.1, 1.05

    # Insertar ratings para season 76
    inserted = 0
    fallback = 0

    with SessionLocal() as s:
        for team_id in teams_2026:
            if team_id in best_rating:
                r = best_rating[team_id]
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
                    "ah": float(r.atk_home), "dh": float(r.def_home),
                    "aa": float(r.atk_away), "da": float(r.def_away),
                })
                inserted += 1
            else:
                # Equipo sin historial -> usar promedio neutro (1.0 = promedio)
                s.execute(text("""
                    INSERT INTO weinston_ratings
                        (season_id, team_id, league_id, atk_home, def_home, atk_away, def_away)
                    VALUES
                        (:sid, :tid, :lid, 1.0, 1.0, 1.0, 1.0)
                    ON CONFLICT (season_id, team_id) DO NOTHING
                """), {"sid": WC_2026_SEASON_ID, "tid": team_id, "lid": league_id})
                fallback += 1

        # Insertar parámetros de liga para season 76
        save_league_params(WC_2026_SEASON_ID, avg_mu_home, avg_mu_away, avg_home_adv, 0.0)
        s.commit()

    print(f"\nRatings insertados con historial  : {inserted}")
    print(f"Ratings sin historial (fallback)  : {fallback}")
    print(f"Parametros de liga (mu_home={avg_mu_home:.3f}, mu_away={avg_mu_away:.3f})")

    print("\n" + "=" * 60)
    print("  Listo. Ahora ejecuta:")
    print(f"  python -m src.predictions.cli upcoming --season-id {WC_2026_SEASON_ID} --from 2026-06-11 --to 2026-06-27")
    print("=" * 60)


if __name__ == "__main__":
    main()
