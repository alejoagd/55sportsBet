"""
Indicadores destacados de los dos equipos de un partido.

Se calculan SOBRE LOS MISMOS DATOS DEL MÓDULO DE ESTADÍSTICAS (/api/team-statistics: temporada en
curso, fase actual en las ligas con Apertura/Clausura, sin mínimo de partidos), con la misma regla de
sus tablas "Mejor/Peor ...": todos los equipos de la liga ordenados por la estadística, y se mira si el
equipo está entre los TOP_N de arriba ("los que más") o entre los TOP_N de abajo ("los que menos").
Así, lo que dice la tarjeta del partido coincide con lo que el usuario ve en ese módulo.

Detalles para que coincida literalmente con el módulo:
- El orden de desempate es el del módulo: el endpoint entrega los equipos por nombre y el sort es
  estable (igual que en el frontend, Array.sort).
- El local se compara con lo que hacen los equipos de local (home_*) y el visitante con los de
  visitante (away_*), igual que sus tablas.
- Sin match_stats en la liga (las sudamericanas) el endpoint deja esas estadísticas en None: solo se
  evalúa la ofensiva (goles anotados). Un dato ausente nunca se trata como 0.
"""
from __future__ import annotations
from statistics import mean

TOP_N = 5
MIN_EQUIPOS = 2 * TOP_N          # con menos equipos, "los 5 de arriba" y "los 5 de abajo" se pisarían

# estadística -> campo del módulo (se le antepone home_ o away_)
CAMPOS = {
    "goals": "avg_goals_scored",
    "shots": "avg_shots",
    "shots_on_target": "avg_shots_target",
    "corners": "avg_corners",
    "fouls": "avg_fouls",
    "cards": "avg_cards",
}
# Los que dependen de match_stats; "goals" sale de matches y existe en todas las ligas
SOLO_CON_STATS = ("shots", "shots_on_target", "corners", "fouls", "cards")


def _posicion(equipos: list[dict], campo: str, team_id: int, descendente: bool) -> int | None:
    """Puesto (1 = primero) del equipo en la tabla ordenada, o None si no está entre los TOP_N.
    Igual que getTopTeams del módulo: sort estable y slice(0, TOP_N)."""
    orden = sorted(equipos, key=lambda t: t[campo], reverse=descendente)[:TOP_N]
    for i, t in enumerate(orden, start=1):
        if t["team_id"] == team_id:
            return i
    return None


def indicadores(equipos: list[dict], team_id: int, venue: str, con_stats: bool) -> list[dict]:
    """Estadísticas en las que el equipo sale en las tablas de arriba o de abajo del módulo.

    `equipos`: la lista `teams` de /api/team-statistics. `venue`: 'home' o 'away'.
    """
    out: list[dict] = []
    yo = next((t for t in equipos if t["team_id"] == team_id), None)
    if yo is None:
        return out
    pj = yo["home_matches"] if venue == "home" else yo["away_matches"]
    for stat, base in CAMPOS.items():
        if stat in SOLO_CON_STATS and not con_stats:
            continue
        campo = f"{venue}_{base}"
        validos = [t for t in equipos if t.get(campo) is not None]
        if len(validos) < MIN_EQUIPOS or yo.get(campo) is None:
            continue
        valores = [float(t[campo]) for t in validos]
        arriba = _posicion(validos, campo, team_id, True)
        abajo = _posicion(validos, campo, team_id, False)
        if arriba is None and abajo is None:
            continue
        if arriba is not None and (abajo is None or arriba <= abajo):
            direccion, rank = "most", arriba
        else:
            direccion, rank = "least", abajo
        out.append({
            "stat": stat, "direction": direccion, "rank": rank, "of": len(validos),
            "value": float(yo[campo]), "league_avg": round(mean(valores), 2), "pj": pj,
        })
    # el más marcado primero: mejor puesto y, a igual puesto, más alejado del promedio de la liga
    out.sort(key=lambda i: (i["rank"], -abs(i["value"] - i["league_avg"])))
    return out


def destacados(equipos: list[dict], home_id: int, away_id: int, con_stats: bool) -> dict:
    nombre = {t["team_id"]: t["team_name"] for t in equipos}
    return {
        "top_n": TOP_N,
        "has_match_stats": con_stats,
        "home": {"team_id": home_id, "team": nombre.get(home_id), "venue": "home",
                 "indicators": indicadores(equipos, home_id, "home", con_stats)},
        "away": {"team_id": away_id, "team": nombre.get(away_id), "venue": "away",
                 "indicators": indicadores(equipos, away_id, "away", con_stats)},
    }
