"""
Recuenta el H2H Score de las filas YA guardadas (h2h_scoring y
h2h_recommended_picks) con la búsqueda de H2H corregida (por fecha) y guarda el
denominador (`<stat>_valid` / `valid_matches`).

Por qué: el puntaje se calculó con una lista de H2H mal armada (filtraba por id
de temporada y los ids van al revés del tiempo), y nunca se guardó de cuántos
enfrentamientos salió. Sin el denominador no se puede exigir "12 H2H" ni
separar un 2/2 de un 2/12.

Qué NO toca: ninguna predicción ni línea (se usa la que cada fila ya tiene
guardada, p. ej. OVER_9.5), `<stat>_hit`, Weinston, betting lines ni
league_parameters. Solo actualiza `<stat>_score` y `<stat>_valid`.

Uso (por defecto SIMULA y no escribe):
  python -m src.scripts.recount_h2h_scoring
  python -m src.scripts.recount_h2h_scoring --apply

Se niega a correr contra una BD que no sea local, salvo --allow-remote.
"""
from __future__ import annotations
import argparse
import collections
import re
import sys

from sqlalchemy import text

from src.db import engine
from src.predictions.h2h_scoring_system import (
    MIN_H2H_MATCHES, _calculate_scoring_by_stat, _get_h2h_matches,
)

STATS = ("goles", "tiros", "tiros_al_arco", "corners", "tarjetas", "faltas")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}


def parse_prediction(pred: str | None) -> tuple[str, float] | None:
    """'OVER_9.5' -> ('OVER', 9.5); 'UNDER_2_5' -> ('UNDER', 2.5)."""
    m = re.fullmatch(r"(OVER|UNDER)_(\d+)[._](\d+)", (pred or "").strip())
    if not m:
        return None
    return m.group(1), float(f"{m.group(2)}.{m.group(3)}")


def build_predictions(stored: dict[str, str | None]) -> dict[str, dict]:
    """Arma el dict que espera _calculate_scoring_by_stat desde lo ya guardado."""
    preds: dict[str, dict] = {}
    for stat, pred in stored.items():
        parsed = parse_prediction(pred)
        if parsed:
            preds[stat] = {"prediction": pred, "predicted_total": None, "line": parsed[1]}
    return preds


def recount_row(conn, match_id: int, home_id: int, away_id: int, stored: dict[str, str | None]) -> dict[str, tuple]:
    """{stat: (score, valid)} recontado para un partido con la línea ya guardada."""
    preds = build_predictions(stored)
    if not preds:
        return {}
    h2h = _get_h2h_matches(conn, home_id, away_id, match_id, 12)
    res = _calculate_scoring_by_stat(preds, h2h, len(h2h))
    return {s: (res[s]["score"], res[s]["valid_matches"]) for s in preds if s in res}


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

    changed = unchanged = 0
    valid_dist: dict[str, collections.Counter] = {s: collections.Counter() for s in STATS}
    score_moves = collections.Counter()

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT h.match_id, m.home_team_id, m.away_team_id,
                   {", ".join(f"h.{s}_prediction AS {s}_pred, h.{s}_score AS {s}_old" for s in STATS)}
            FROM h2h_scoring h JOIN matches m ON m.id = h.match_id
            ORDER BY h.match_id
        """)).mappings().all()
        print(f"h2h_scoring: {len(rows)} filas")

        for r in rows:
            stored = {s: r[f"{s}_pred"] for s in STATS}
            new = recount_row(conn, r["match_id"], r["home_team_id"], r["away_team_id"], stored)
            sets, params = [], {"mid": r["match_id"]}
            for stat, (score, valid) in new.items():
                valid_dist[stat]["12" if valid >= MIN_H2H_MATCHES else ("0" if valid == 0 else "1-11")] += 1
                if score != r[f"{stat}_old"]:
                    score_moves[stat] += 1
                sets += [f"{stat}_score = :{stat}_s", f"{stat}_valid = :{stat}_v"]
                params[f"{stat}_s"], params[f"{stat}_v"] = score, valid
            if not sets:
                unchanged += 1
                continue
            changed += 1
            if args.apply:
                conn.execute(text(f"UPDATE h2h_scoring SET {', '.join(sets)} WHERE match_id = :mid"), params)

        # Picks recomendados: solo se completa el denominador (el puntaje con el
        # que se mostraron queda como estaba, es lo que vio el usuario).
        picks = conn.execute(text("""
            SELECT p.id, p.match_id, p.stat, p.prediction, p.score, m.home_team_id, m.away_team_id
            FROM h2h_recommended_picks p JOIN matches m ON m.id = p.match_id
        """)).mappings().all()
        pick_den = collections.Counter()
        pick_score_diff = 0
        for p in picks:
            new = recount_row(conn, p["match_id"], p["home_team_id"], p["away_team_id"], {p["stat"]: p["prediction"]})
            if p["stat"] not in new:
                continue
            score, valid = new[p["stat"]]
            pick_den["12" if valid >= MIN_H2H_MATCHES else str(valid)] += 1
            if score != p["score"]:
                pick_score_diff += 1
            if args.apply:
                conn.execute(text("UPDATE h2h_recommended_picks SET valid_matches = :v WHERE id = :id"),
                             {"v": valid, "id": p["id"]})


    print(f"\nFilas de h2h_scoring con algo que actualizar: {changed} · sin pronósticos parseables: {unchanged}")
    print("Denominador recontado por estadística (12 = cumple la regla):")
    for s in STATS:
        d = valid_dist[s]
        total = sum(d.values()) or 1
        print(f"  {s:<14} total {total:>5} | 12 H2H: {d['12']:>5} ({100*d['12']/total:4.0f}%) | 1-11: {d['1-11']:>5} | 0: {d['0']:>4} | puntaje cambió: {score_moves[s]}")
    print(f"\nPicks recomendados: {len(picks)} · denominadores {dict(sorted(pick_den.items(), key=lambda kv: (len(kv[0]), kv[0])))}")
    print(f"  (puntaje distinto al mostrado en su momento: {pick_score_diff})")
    print("\n✅ Cambios escritos." if args.apply else "\nℹ️  Simulación: no se escribió nada. Repite con --apply para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
