# src/predictions/upcoming_core.py
from __future__ import annotations
from sqlalchemy import text

def _blend(value, prior, n, k=5):
    """Shrinkage hacia el prior de liga para pocos partidos."""
    if value is None:
        value = prior
    return (n * value + k * prior) / (n + k)

def load_team_strengths(conn, season_id: int, n_recent: int = 20):
    """
    Calcula fortalezas por equipo a partir de TODO el histórico disponible
    (partidos con resultado y fecha < hoy). Usa últimos n_recent partidos
    por equipo (split home/away) + shrinkage al promedio de liga.

    Devuelve: (strengths: dict[team_id->{attack_home, defense_home, attack_away, defense_away}],
               lg_home_gf, lg_away_gf, HFA)
    """
    # 1) Liga (promedios sobre todo el histórico jugado)
    q_league = text("""
        SELECT AVG(home_goals)::float AS lg_home_gf,
               AVG(away_goals)::float AS lg_away_gf
        FROM matches
        WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
          AND date < CURRENT_DATE
    """)
    row = conn.execute(q_league).one_or_none()
    if not row or row[0] is None or row[1] is None:
        # Fallbacks sanos si no hay datos en absoluto
        return {}, 1.4, 1.1, 1.00

    lg_home_gf = float(row[0])
    lg_away_gf = float(row[1])
    HFA = 1.00  # puedes calibrar 1.05–1.10 si quisieras

    # 2) Últimos N por equipo (home/away) sobre todo el histórico
    q_strengths = text(f"""
        WITH played AS (
          SELECT id, date, home_team_id, away_team_id, home_goals, away_goals
          FROM matches
          WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
            AND date < CURRENT_DATE
        ),
        home_recent AS (
          SELECT p.*,
                 ROW_NUMBER() OVER (PARTITION BY home_team_id ORDER BY date DESC) AS rn
          FROM played p
        ),
        away_recent AS (
          SELECT p.*,
                 ROW_NUMBER() OVER (PARTITION BY away_team_id ORDER BY date DESC) AS rn
          FROM played p
        ),
        h AS (
          SELECT * FROM home_recent WHERE rn <= :n_recent
        ),
        a AS (
          SELECT * FROM away_recent WHERE rn <= :n_recent
        )
        SELECT
          t.id AS team_id,
          COALESCE(COUNT(h.id), 0)        AS n_home,
          AVG(h.home_goals)::float        AS home_gf,
          AVG(h.away_goals)::float        AS home_ga,
          COALESCE(COUNT(a.id), 0)        AS n_away,
          AVG(a.away_goals)::float        AS away_gf,
          AVG(a.home_goals)::float        AS away_ga
        FROM teams t
        LEFT JOIN h ON h.home_team_id = t.id
        LEFT JOIN a ON a.away_team_id = t.id
        GROUP BY t.id
    """)
    strengths = {}
    for tid, n_home, home_gf, home_ga, n_away, away_gf, away_ga in conn.execute(q_strengths, {"n_recent": n_recent}):
        n_home = int(n_home or 0); n_away = int(n_away or 0)

        # Shrinkage a promedio de liga si hay pocos partidos
        home_gf = _blend(home_gf, lg_home_gf, n_home)
        home_ga = _blend(home_ga, lg_away_gf, n_home)
        away_gf = _blend(away_gf, lg_away_gf, n_away)
        away_ga = _blend(away_ga, lg_home_gf, n_away)

        strengths[int(tid)] = {
            "attack_home":  (home_gf / lg_home_gf) if lg_home_gf > 0 else 1.0,
            "defense_home": (home_ga / lg_away_gf) if lg_away_gf > 0 else 1.0,
            "attack_away":  (away_gf / lg_away_gf) if lg_away_gf > 0 else 1.0,
            "defense_away": (away_ga / lg_home_gf) if lg_home_gf > 0 else 1.0,
        }

    return strengths, lg_home_gf, lg_away_gf, HFA

def load_team_stat_profiles(conn, n_recent: int = 20):
    """
    Perfiles por equipo para SHOTS, SOT, FOULS, CARDS, CORNERS
    usando 'weinston_predictions' de partidos pasados (< hoy).
    Devuelve:
      profiles[team_id][stat_name] = {
         'home_for', 'home_against', 'away_for', 'away_against', 'n_home', 'n_away'
      }
      league_means[stat_name] = promedio de liga
    """
    # 1) Traer histórico con stats de Weinston (solo partidos pasados)
    q = text("""
        SELECT m.date, m.home_team_id, m.away_team_id,
               w.shots_home, w.shots_away, w.shots_target_home, w.shots_target_away,
               w.fouls_home, w.fouls_away, w.cards_home, w.cards_away,
               w.corners_home, w.corners_away
        FROM matches m
        JOIN weinston_predictions w ON w.match_id = m.id
        WHERE m.date < CURRENT_DATE
        ORDER BY m.date DESC
    """)
    rows = conn.execute(q).fetchall()

    stats = [
        ("shots_home","shots_away"),
        ("shots_target_home","shots_target_away"),
        ("fouls_home","fouls_away"),
        ("cards_home","cards_away"),
        ("corners_home","corners_away"),
    ]
    # nombres "compactos" para los dicts
    key_map = {
        ("shots_home","shots_away"): "shots",
        ("shots_target_home","shots_target_away"): "shots_target",
        ("fouls_home","fouls_away"): "fouls",
        ("cards_home","cards_away"): "cards",
        ("corners_home","corners_away"): "corners",
    }

    # 2) Acumular listas por equipo y condición
    from collections import defaultdict, deque
    prof = defaultdict(lambda: defaultdict(lambda: {
        "home_for": deque(maxlen=n_recent),
        "home_against": deque(maxlen=n_recent),
        "away_for": deque(maxlen=n_recent),
        "away_against": deque(maxlen=n_recent),
    }))
    league_sums = {key_map[s]: [0.0, 0] for s in stats}  # sum, cnt

    for (date, h, a,
         sh, sa, sth, sta, fh, fa, ch, ca, coh, coa) in rows:

        values = {
            "shots":        (sh, sa),
            "shots_target": (sth, sta),
            "fouls":        (fh, fa),
            "cards":        (ch, ca),
            "corners":      (coh, coa),
        }

        for name, (vh, va) in values.items():
            # liga
            if vh is not None:
                league_sums[name][0] += float(vh); league_sums[name][1] += 1
            if va is not None:
                league_sums[name][0] += float(va); league_sums[name][1] += 1
            # perfiles
            if vh is not None:
                prof[h][name]["home_for"].append(float(vh))
            if va is not None:
                prof[h][name]["home_against"].append(float(va))
            if va is not None:
                prof[a][name]["away_for"].append(float(va))
            if vh is not None:
                prof[a][name]["away_against"].append(float(vh))

    league_means = {}
    for name, (s, c) in league_sums.items():
        league_means[name] = (s / c) if c else 0.0

    # 3) Convertir de deque a promedios con shrinkage
    def avg(lst): 
        arr = list(lst); 
        return (sum(arr)/len(arr)) if arr else None

    out = {}
    for tid, per_stat in prof.items():
        out[tid] = {}
        for name, buckets in per_stat.items():
            hf = avg(buckets["home_for"])
            ha = avg(buckets["home_against"])
            af = avg(buckets["away_for"])
            aa = avg(buckets["away_against"])
            # cuenta de muestras usadas (aprox)
            n_h = len(buckets["home_for"]) + len(buckets["home_against"])
            n_a = len(buckets["away_for"]) + len(buckets["away_against"])
            lg = league_means[name] or 0.001
            out[tid][name] = {
                "home_for":      _blend(hf, lg, n_h),
                "home_against":  _blend(ha, lg, n_h),
                "away_for":      _blend(af, lg, n_a),
                "away_against":  _blend(aa, lg, n_a),
                "n_home": n_h, "n_away": n_a,
            }

    return out, league_means
