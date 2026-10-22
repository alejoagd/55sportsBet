"""
Consolida partidos duplicados (misma temporada, local, visitante, fecha, fase y ronda).

Por qué: un partido aplazado entra primero como fixture con una fecha provisional y,
cuando se juega, el CSV de resultados lo inserta de nuevo con la fecha real; después
el sync de fixtures corrige la fecha de la fila vieja y quedan dos filas idénticas.
Efecto visible: temporadas con más partidos de los posibles (La Liga 2025/26 tenía
407 jugados en vez de 380, equipos con 43 partidos en 38 jornadas), posiciones y
métricas de Evolución contando dos veces, y la misma apuesta recomendada duplicada
en best_bets_history.

Qué hace, por cada grupo de duplicados:
- Elige UNA fila: la que tiene resultado; si empatan, la que tiene más datos colgados
  (estadísticas, predicciones, líneas, H2H, apuestas); si empatan, la de id menor.
- Rellena en esa fila los campos vacíos con los de las otras (árbitro, medio tiempo,
  ids externos, etc.). Nunca pisa un valor que ya tenga.
- De cada tabla dependiente conserva la fila de la elegida y pasa a ella lo que solo
  tenía la otra (si ambas tienen lo mismo, queda la de la elegida).
- prediction_outcomes de la fila descartada se borra y se regenera con evaluate()
  desde las predicciones que quedaron, para que no se mezcle una predicción con el
  acierto de otra.
- Se omite (y se avisa) cualquier grupo con resultados distintos entre sus filas.

Uso (por defecto SIMULA y no escribe):
  python -m src.scripts.dedupe_matches
  python -m src.scripts.dedupe_matches --apply

Se niega a correr contra una BD que no sea local, salvo --allow-remote.
"""
from __future__ import annotations
import argparse
import collections
import sys

from sqlalchemy import text

from src.db import engine

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}

# (tabla, columnas que, junto con match_id, identifican la fila)
DEPENDIENTES = [
    ("match_stats", []),
    ("poisson_predictions", []),
    ("weinston_predictions", []),
    ("h2h_scoring", []),
    ("betting_lines_predictions", ["model"]),
    ("h2h_recommended_picks", ["stat"]),
    ("best_bets_history", ["model", "bet_type"]),
    ("wc_scoring_events", ["team", "player_name", "minute"]),
]
# Campos de matches que la fila elegida hereda si los tiene vacíos
HEREDABLES = [
    "halftime_homegoal", "halftime_awaygoal", "halftime_result", "referee", "apifootball_id",
    "sofascore_id", "penalty_winner", "stage", "round_label", "group_name",
    "api_football_fixture_id", "espn_event_id", "kickoff_at",
]
GRUPO = "season_id, home_team_id, away_team_id, date, COALESCE(stage, ''), COALESCE(round_label, '')"


def _carga(conn, mid: int) -> int:
    """Cuántos datos cuelgan de este partido (sirve para desempatar)."""
    total = 0
    for tabla, _ in DEPENDIENTES:
        total += conn.execute(text(f"SELECT count(*) FROM {tabla} WHERE match_id = :m"), {"m": mid}).scalar()
    return total


def encontrar_grupos(conn) -> list[list[dict]]:
    rows = conn.execute(text(f"""
        SELECT m.id, m.season_id, m.home_goals, m.away_goals, m.date,
               dense_rank() OVER (ORDER BY {GRUPO}) AS g
        FROM matches m
        WHERE ({GRUPO}) IN (SELECT {GRUPO} FROM matches GROUP BY {GRUPO} HAVING count(*) > 1)
        ORDER BY g, m.id""")).mappings().all()
    grupos: dict[int, list[dict]] = collections.defaultdict(list)
    for r in rows:
        grupos[r["g"]].append(dict(r))
    return list(grupos.values())


def resolver_grupo(conn, filas: list[dict]) -> tuple[str, dict]:
    """('ok'|'omitido', info). No escribe."""
    resultados = {(f["home_goals"], f["away_goals"]) for f in filas if f["home_goals"] is not None}
    if len(resultados) > 1:
        return "omitido", {"motivo": f"resultados distintos {sorted(resultados)}", "ids": [f["id"] for f in filas]}
    for f in filas:
        f["carga"] = _carga(conn, f["id"])
    filas.sort(key=lambda f: (f["home_goals"] is None, -f["carga"], f["id"]))
    return "ok", {"keeper": filas[0]["id"], "losers": [f["id"] for f in filas[1:]], "season_id": filas[0]["season_id"]}


def consolidar(conn, keeper: int, losers: list[int]) -> dict:
    """Pasa a `keeper` lo que cuelga de `losers` y borra los partidos sobrantes."""
    stats = collections.Counter()
    for loser in losers:
        # 1) Heredar campos vacíos. Se lee antes de borrar nada.
        cols = ", ".join(HEREDABLES)
        vals = conn.execute(text(f"SELECT {cols} FROM matches WHERE id = :m"), {"m": loser}).mappings().one()
        sets = ", ".join(f"{c} = COALESCE({c}, :{c})" for c in HEREDABLES)
        conn.execute(text(f"UPDATE matches SET {sets} WHERE id = :k"), {**dict(vals), "k": keeper})

        # 2) Dependientes: si la elegida ya tiene esa fila se descarta la otra; si no, se mueve.
        for tabla, claves in DEPENDIENTES:
            igual = "".join(f" AND k.{c} IS NOT DISTINCT FROM l.{c}" for c in claves)
            borradas = conn.execute(text(f"""
                DELETE FROM {tabla} l WHERE l.match_id = :loser
                  AND EXISTS (SELECT 1 FROM {tabla} k WHERE k.match_id = :keeper{igual})"""),
                {"loser": loser, "keeper": keeper}).rowcount
            movidas = conn.execute(text(f"UPDATE {tabla} SET match_id = :keeper WHERE match_id = :loser"),
                                   {"loser": loser, "keeper": keeper}).rowcount
            stats[f"{tabla}: movidas"] += movidas
            stats[f"{tabla}: descartadas"] += borradas

        # 3) Aciertos: se regeneran con evaluate() desde las predicciones que quedaron.
        stats["prediction_outcomes: borradas"] += conn.execute(
            text("DELETE FROM prediction_outcomes WHERE match_id = :m"), {"m": loser}).rowcount
        conn.execute(text("DELETE FROM matches WHERE id = :m"), {"m": loser})
        stats["partidos borrados"] += 1
    return dict(stats)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Escribe los cambios (por defecto solo simula)")
    ap.add_argument("--allow-remote", action="store_true", help="Permite correr contra una BD no local")
    args = ap.parse_args()

    host = engine.url.host
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"⛔ La BD configurada es '{host}' (no local). Abortado: usa --allow-remote solo si es intencional.")
        return 2
    print(f"BD: {host or 'socket local'}/{engine.url.database} · modo: {'APLICAR' if args.apply else 'SIMULACIÓN'}")

    total = collections.Counter()
    omitidos: list[dict] = []
    temporadas: set[int] = set()
    with engine.begin() as conn:
        grupos = encontrar_grupos(conn)
        print(f"Grupos de partidos duplicados: {len(grupos)}")
        for filas in grupos:
            estado, info = resolver_grupo(conn, filas)
            if estado == "omitido":
                omitidos.append(info)
                continue
            temporadas.add(info["season_id"])
            if args.apply:
                total.update(consolidar(conn, info["keeper"], info["losers"]))
            else:
                total["partidos que se borrarían"] += len(info["losers"])

    print("\nResumen:")
    for k, v in sorted(total.items()):
        print(f"  {k}: {v}")
    for o in omitidos:
        print(f"  ⚠️  omitido {o['ids']}: {o['motivo']}")
    print(f"  temporadas afectadas: {sorted(temporadas)}")

    if args.apply and temporadas:
        # Se regeneran los aciertos desde las predicciones que quedaron. evaluate() abre su
        # propia transacción, por eso va después de confirmar la consolidación.
        import contextlib, io
        from src.predictions.evaluate import evaluate
        with engine.connect() as c:
            con_outcomes = {r[0] for r in c.execute(text(
                "SELECT DISTINCT m.season_id FROM prediction_outcomes po JOIN matches m ON m.id = po.match_id"))}
        for sid in sorted(temporadas & con_outcomes):
            with contextlib.redirect_stdout(io.StringIO()):  # evaluate() imprime cada partido
                res = evaluate(season_id=sid)
            print(f"  aciertos regenerados season_id={sid}: {res}")
    print("\n✅ Cambios escritos." if args.apply else "\nℹ️  Simulación: no se escribió nada. Repite con --apply para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
