# src/predictions/attack_quality.py
"""
Índice de Calidad de Ataque (AQI) por equipo.

Idea: los goles pasados son una medida ruidosa de qué tan bueno es un ataque.
Backtest sobre 38.000 partidos de las 4 ligas europeas: los tiros a puerta
(0.32 goles c/u; los tiros fuera/bloqueados aportan ~0) predicen los goles
siguientes igual que los propios goles y con más estabilidad, y ajustar por
cuánto concede la defensa rival sube el R² fuera de muestra de 0.078 a 0.101.
La "eficiencia de definición" (goles por tiro a puerta) casi no persiste, así
que se regresa fuertemente hacia el promedio de la liga.

AQI = 100 × (tiros a puerta ajustados por rival / promedio liga)
          × (conversión suavizada / conversión liga) ^ 0.5

La conversión entra con raíz cuadrada: en el backtest semanal (9.264
equipo-partidos, 2022-2026) el exponente 0.5 dio la mejor correlación con los
goles siguientes (0.249 vs 0.242 sin conversión y 0.241 con exponente 1).

100 = ataque promedio de la liga; 120 = se espera un 20 % más de goles que el
promedio. Es una función pura (sin BD) para poder testearla y reutilizarla
desde el API y desde los modelos.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

# Ventana de partidos recientes y mínimo para publicar un valor. Con menos
# partidos el índice es puro ruido y se devuelve None (nunca un 100 inventado).
DEFAULT_WINDOW = 10
DEFAULT_MIN_MATCHES = 5

# Tiros a puerta "a priori" con los que se mezcla la conversión del equipo
# antes de compararla con la de la liga: con ~30 tiros a puerta (≈3 partidos)
# el equipo pesa lo mismo que el promedio de la liga.
CONVERSION_PRIOR_SOT = 30.0

# Mínimo de partidos del rival para ajustar por su defensa; con menos se usa
# el promedio de la liga (factor 1.0) para no amplificar muestras diminutas.
MIN_OPP_MATCHES = 5

# Peso de la eficiencia de definición dentro del AQI (ver docstring del módulo).
FINISHING_EXPONENT = 0.5


def compute_attack_quality(
    rows: Iterable[dict],
    window: int = DEFAULT_WINDOW,
    min_matches: int = DEFAULT_MIN_MATCHES,
) -> dict:
    """
    rows: un dict por equipo y partido terminado CON estadísticas, con las
    claves: match_id, date, team_id, opp_id, gf (goles a favor), sot (tiros a
    puerta propios), shots (tiros propios), sot_against (tiros a puerta del
    rival). Los partidos sin match_stats deben excluirse antes de llamar.

    Devuelve {"league": {...}, "teams": {team_id: {...}}}. Un equipo con menos
    de `min_matches` partidos con estadísticas queda con aqi=None.
    """
    rows = sorted(rows, key=lambda r: (r["date"], r["match_id"]))
    if not rows:
        return {"league": None, "teams": {}}

    n = len(rows)
    league_sot = sum(r["sot"] for r in rows) / n
    league_conv = sum(r["gf"] for r in rows) / max(sum(r["sot"] for r in rows), 1)
    league_precision = sum(r["sot"] for r in rows) / max(sum(r["shots"] for r in rows), 1)
    if league_sot <= 0 or league_conv <= 0:
        return {"league": None, "teams": {}}

    # Cuánto concede cada defensa (tiros a puerta por partido, toda la muestra).
    conceded = defaultdict(list)
    for r in rows:
        conceded[r["team_id"]].append(r["sot_against"])
    # Dos filas por partido (una por equipo): el "rival" de una fila es el
    # equipo cuya defensa enfrentó, y esa defensa ya está en `conceded`.
    def_factor = {}
    for team_id, vals in conceded.items():
        if len(vals) >= MIN_OPP_MATCHES:
            def_factor[team_id] = (sum(vals) / len(vals)) / league_sot
        else:
            def_factor[team_id] = 1.0

    by_team = defaultdict(list)
    for r in rows:
        by_team[r["team_id"]].append(r)

    teams = {}
    for team_id, games in by_team.items():
        last = games[-window:]
        k = len(last)
        if k < min_matches:
            teams[team_id] = {"matches_used": k, "aqi": None}
            continue

        # Tiros a puerta ajustados: un tiro a puerta contra una defensa que
        # concede mucho vale menos que uno contra una que concede poco.
        adj_sot = [
            g["sot"] / max(def_factor.get(g["opp_id"], 1.0), 0.5) for g in last
        ]
        sot_avg = sum(adj_sot) / k
        goals = sum(g["gf"] for g in last)
        sot_total = sum(g["sot"] for g in last)
        shots_total = sum(g["shots"] for g in last)

        volume_idx = sot_avg / league_sot
        conv_shrunk = (goals + CONVERSION_PRIOR_SOT * league_conv) / (
            sot_total + CONVERSION_PRIOR_SOT
        )
        finishing_idx = conv_shrunk / league_conv
        precision = sot_total / shots_total if shots_total else None

        teams[team_id] = {
            "matches_used": k,
            "aqi": round(100.0 * volume_idx * finishing_idx ** FINISHING_EXPONENT, 1),
            "volume_idx": round(100.0 * volume_idx, 1),
            "finishing_idx": round(100.0 * finishing_idx, 1),
            "precision_pct": round(100.0 * precision, 1) if precision is not None else None,
            "precision_idx": (
                round(100.0 * precision / league_precision, 1)
                if precision is not None and league_precision
                else None
            ),
            "avg_shots_on_target": round(sot_total / k, 2),
            "avg_goals": round(goals / k, 2),
            "expected_goals": round(sot_avg * conv_shrunk, 2),
        }

    return {
        "league": {
            "avg_shots_on_target": round(league_sot, 3),
            "goals_per_shot_on_target": round(league_conv, 4),
            "precision_pct": round(100.0 * league_precision, 1),
            "matches": n // 2,
        },
        "teams": teams,
    }


def team_match_rows(match_rows: Iterable[dict]) -> list[dict]:
    """Convierte filas por partido (local/visitante) al formato por equipo."""
    out = []
    for m in match_rows:
        out.append({
            "match_id": m["match_id"], "date": m["date"],
            "team_id": m["home_team_id"], "opp_id": m["away_team_id"],
            "gf": m["home_goals"], "sot": m["home_sot"],
            "shots": m["home_shots"], "sot_against": m["away_sot"],
        })
        out.append({
            "match_id": m["match_id"], "date": m["date"],
            "team_id": m["away_team_id"], "opp_id": m["home_team_id"],
            "gf": m["away_goals"], "sot": m["away_sot"],
            "shots": m["away_shots"], "sot_against": m["home_sot"],
        })
    return out
