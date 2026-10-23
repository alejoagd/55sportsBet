"""
Indicadores destacados de los dos equipos de un partido.

Para cada equipo se mira cómo está posicionado en su liga en cada estadística (goles, tiros, tiros a
puerta, córners, faltas, tarjetas) SEGÚN SU CONDICIÓN EN ESTE PARTIDO: el local se compara con lo que
los equipos hacen de local, el visitante con lo que hacen de visitante. Un equipo "se destaca" si está
entre los TOP_N que MÁS o que MENOS hacen algo ("Forest: 1.º de 20 en tiros como visitante").

Decisiones (para que el ranking sea estable y no ruido):
- Ventana: los últimos VENTANA partidos del equipo en esa condición ANTES de este partido, incluyendo
  la temporada anterior: a mitad de temporada un equipo solo lleva 4 o 5 partidos de local.
- Un equipo entra al ranking de una estadística solo con MIN_PARTIDOS partidos con ese dato, y el
  ranking solo existe con MIN_EQUIPOS equipos. Si no se cumple, no se muestra nada: ningún dato
  faltante se rellena con 0.
- Solo participan los equipos de la temporada del partido (no los descendidos).
- Las ligas sudamericanas no tienen estadísticas de equipo: solo salen indicadores de goles.
"""
from __future__ import annotations
from statistics import mean, pstdev

from sqlalchemy import text
from sqlalchemy.engine import Connection

STATS = ("goals", "shots", "shots_on_target", "corners", "fouls", "cards")
VENTANA = 10
MIN_PARTIDOS = 5
TOP_N = 5
MIN_EQUIPOS = 10

# estadística -> (columna local, columna visitante) en match_stats; goles sale de matches
_COLS = {
    "shots": ("home_shots", "away_shots"),
    "shots_on_target": ("home_shots_on_target", "away_shots_on_target"),
    "corners": ("home_corners", "away_corners"),
    "fouls": ("home_fouls", "away_fouls"),
}

Medias = dict[int, dict[str, tuple[float, int]]]   # equipo -> estadística -> (media, partidos con dato)


def indicadores(medias: Medias, team_id: int) -> list[dict]:
    """Estadísticas en las que `team_id` está entre los TOP_N que más o que menos hacen. Función pura."""
    out: list[dict] = []
    for stat in STATS:
        pool = {t: v[stat][0] for t, v in medias.items() if stat in v and v[stat][1] >= MIN_PARTIDOS}
        if team_id not in pool or len(pool) < MIN_EQUIPOS:
            continue
        valor = pool[team_id]
        valores = list(pool.values())
        desv = pstdev(valores)
        if desv == 0:
            continue                      # todos iguales: nadie se destaca
        mayores = sum(1 for x in valores if round(x, 2) > round(valor, 2))
        menores = sum(1 for x in valores if round(x, 2) < round(valor, 2))
        rank_mas, rank_menos = mayores + 1, menores + 1
        if rank_mas <= TOP_N and rank_mas <= rank_menos:
            direccion, rank = "most", rank_mas
        elif rank_menos <= TOP_N:
            direccion, rank = "least", rank_menos
        else:
            continue
        out.append({
            "stat": stat, "direction": direccion, "rank": rank, "of": len(pool),
            "value": round(valor, 2), "league_avg": round(mean(valores), 2),
            "matches": medias[team_id][stat][1], "z": round((valor - mean(valores)) / desv, 2),
        })
    # el más marcado primero: mejor puesto y, a igual puesto, más alejado del promedio de la liga
    out.sort(key=lambda i: (i["rank"], -abs(i["z"])))
    return out


def _medias(conn: Connection, league_id: int, season_id: int, before, venue: str) -> Medias:
    """Medias por equipo (últimos VENTANA partidos en la condición `venue`) de los equipos de la temporada."""
    local = venue == "home"
    team_col = "m.home_team_id" if local else "m.away_team_id"
    goals_col = "m.home_goals" if local else "m.away_goals"
    sel = ",\n".join(
        f"ms.{c[0 if local else 1]} AS {k}" for k, c in _COLS.items()
    )
    yel, red = ("home_yellow_cards", "home_red_cards") if local else ("away_yellow_cards", "away_red_cards")
    rows = conn.execute(text(f"""
        WITH equipos AS (
            SELECT home_team_id AS t FROM matches WHERE season_id = :sid
            UNION SELECT away_team_id FROM matches WHERE season_id = :sid
        ), partidos AS (
            SELECT {team_col} AS team_id, m.date, m.id, {goals_col} AS goals,
                   {sel},
                   CASE WHEN ms.{yel} IS NULL THEN NULL ELSE ms.{yel} + COALESCE(ms.{red}, 0) END AS cards
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            LEFT JOIN match_stats ms ON ms.match_id = m.id
            WHERE s.league_id = :lid AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
              AND m.date < :before AND {team_col} IN (SELECT t FROM equipos)
        ), ventana AS (
            SELECT *, row_number() OVER (PARTITION BY team_id ORDER BY date DESC, id DESC) AS rn FROM partidos
        )
        SELECT team_id,
               count(goals) AS n_goals, avg(goals) AS goals,
               count(shots) AS n_shots, avg(shots) AS shots,
               count(shots_on_target) AS n_shots_on_target, avg(shots_on_target) AS shots_on_target,
               count(corners) AS n_corners, avg(corners) AS corners,
               count(fouls) AS n_fouls, avg(fouls) AS fouls,
               count(cards) AS n_cards, avg(cards) AS cards
        FROM ventana WHERE rn <= :ventana GROUP BY team_id
    """), {"sid": season_id, "lid": league_id, "before": before, "ventana": VENTANA}).mappings().all()
    medias: Medias = {}
    for r in rows:
        medias[r["team_id"]] = {
            s: (float(r[s]), int(r[f"n_{s}"])) for s in STATS if r[s] is not None and r[f"n_{s}"]
        }
    return medias


def destacados_del_partido(conn: Connection, match_id: int) -> dict | None:
    """None si el partido no existe."""
    m = conn.execute(text("""
        SELECT m.id, m.date, m.season_id, s.league_id, l.name AS league,
               m.home_team_id, m.away_team_id, th.name AS home, ta.name AS away
        FROM matches m JOIN seasons s ON s.id = m.season_id JOIN leagues l ON l.id = s.league_id
        JOIN teams th ON th.id = m.home_team_id JOIN teams ta ON ta.id = m.away_team_id
        WHERE m.id = :m"""), {"m": match_id}).mappings().first()
    if not m:
        return None
    en_casa = _medias(conn, m["league_id"], m["season_id"], m["date"], "home")
    de_visita = _medias(conn, m["league_id"], m["season_id"], m["date"], "away")
    return {
        "match_id": match_id, "league": m["league"],
        "window": VENTANA, "min_matches": MIN_PARTIDOS, "top_n": TOP_N,
        "home": {"team_id": m["home_team_id"], "team": m["home"], "venue": "home",
                 "indicators": indicadores(en_casa, m["home_team_id"])},
        "away": {"team_id": m["away_team_id"], "team": m["away"], "venue": "away",
                 "indicators": indicadores(de_visita, m["away_team_id"])},
    }
