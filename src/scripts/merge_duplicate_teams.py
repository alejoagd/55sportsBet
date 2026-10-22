"""
Fusiona clubes sudamericanos duplicados (mismo club, nombre distinto según la fuente).

Por qué: API-Football (2022-2024) y ESPN (resto de años) nombran distinto a muchos
clubes ("Newells Old Boys" vs "Newell's Old Boys", "Llaneros FC" vs "Llaneros").
Al cargar el histórico de ESPN se crearon equipos nuevos y el H2H, que se calcula
por id de equipo, quedaba partido en dos: un cruce con 4 partidos reales aparecía
con 1 o 2.

Cómo: la lista es EXPLÍCITA y por nombre exacto (los ids cambian entre local y
producción). Solo incluye casos inequívocos; los ambiguos (Nacional, Independiente,
Sport, Santa Fe, Junior, Libertad, Guaraní, Portuguesa, Wanderers, River Plate
Uruguay) quedaron fuera a propósito porque son clubes distintos o no hay certeza.
Por cada par se exige: ambos nombres existen una sola vez, nunca se enfrentaron
entre sí y no comparten temporada (un club no puede estar dos veces en la misma).
Se conserva el equipo con más partidos y se mueven a él partidos, ids externos
(así el sync diario de ESPN sigue resolviendo bien) y ratings de Weinston.

Uso (por defecto SIMULA y no escribe):
  python -m src.scripts.merge_duplicate_teams
  python -m src.scripts.merge_duplicate_teams --apply

Se niega a correr contra una BD que no sea local, salvo --allow-remote.
"""
from __future__ import annotations
import argparse
import sys

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.db import engine

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}

PARES = [
    ("Argentinos JRS", "Argentinos Juniors"),
    ("Sarmiento Junin", "Sarmiento (Junín)"),
    ("Newells Old Boys", "Newell's Old Boys"),
    ("Central Cordoba de Santiago", "Central Córdoba (Santiago del Estero)"),
    ("Godoy Cruz", "Godoy Cruz Antonio Tomba"),
    ("Union Santa Fe", "Unión (Santa Fe)"),
    ("Estudiantes L.P.", "Estudiantes de La Plata"),
    ("Talleres Cordoba", "Talleres (Córdoba)"),
    ("Colon Santa Fe", "Colón (Santa Fe)"),
    ("Belgrano Cordoba", "Belgrano (Córdoba)"),
    ("Instituto Cordoba", "Instituto (Córdoba)"),
    ("Envigado", "Envigado FC"),
    ("Jaguares", "Jaguares de Córdoba"),
    ("Independ. Rivadavia", "Independiente Rivadavia"),
    ("Metropolitanos FC", "Metropolitanos"),
    ("Cienciano", "Cienciano del Cusco"),
    ("FBC Melgar", "Melgar"),
    ("Melgar FBC", "Melgar"),
    ("Mushuc Runa SC", "Mushuc Runa"),
    ("Guairena FC", "Guaireña"),
    ("Delfin SC", "Delfín"),
    ("Everton de Vina", "Everton CD"),
    ("Estudiantes de Merida FC", "Estudiantes de Mérida"),
    ("Deportivo Tachira FC", "Deportivo Táchira"),
    ("Carabobo FC", "Carabobo"),
    ("Racing Montevideo", "Racing (Montevideo)"),
    ("Llaneros FC", "Llaneros"),
    ("Puerto Cabello", "Academia Puerto Cabello"),
    ("Jorge Wilstermann", "Wilstermann"),
    ("Alianza Valledupar", "Alianza FC"),
    ("Huila", "Atlético Huila"),
    ("Bucaramanga", "Atlético Bucaramanga"),
    ("Chico", "Boyacá Chicó FC"),
    ("Fortaleza EC", "Fortaleza"),
    ("Fortaleza FC", "Fortaleza CEIF"),
    ("Olimpia", "Club Olimpia"),
    # Verificados contra los rivales de cada uno por año y competición:
    ("Libertad Asuncion", "Libertad"),           # Paraguay (no confundir con "Libertad (Ecuador)")
    ("Club Guarani", "Guaraní"),                 # Paraguay
    ("Wanderers", "Montevideo Wanderers"),       # Uruguay (Santiago Wanderers es otro club)
    ("Club Nacional", "Nacional"),               # Uruguay (el paraguayo es "Nacional Asuncion")
]


def _team(conn, name: str):
    rows = conn.execute(text("""
        SELECT t.id, (SELECT count(*) FROM matches m WHERE t.id IN (m.home_team_id, m.away_team_id)) AS n
        FROM teams t WHERE t.name = :n"""), {"n": name}).fetchall()
    return rows[0] if len(rows) == 1 else None


def _seasons(conn, tid: int) -> set[int]:
    return {r[0] for r in conn.execute(text(
        "SELECT season_id FROM matches WHERE :t IN (home_team_id, away_team_id)"), {"t": tid})}


def _move(conn, table: str, col: str, drop: int, keep: int) -> None:
    """Mueve filas de `drop` a `keep`; si choca con una restricción única, esa fila ya existe en `keep`."""
    try:
        with conn.begin_nested():
            conn.execute(text(f"UPDATE {table} SET {col} = :k WHERE {col} = :d"), {"k": keep, "d": drop})
    except IntegrityError:
        with conn.begin_nested():
            conn.execute(text(f"DELETE FROM {table} WHERE {col} = :d"), {"d": drop})


def merge_pair(conn, a_name: str, b_name: str, apply: bool) -> tuple[str, str]:
    a, b = _team(conn, a_name), _team(conn, b_name)
    if a is None or b is None:
        return "omitido", f"no existe una sola vez ({a_name!r}: {'ok' if a else 'no'}, {b_name!r}: {'ok' if b else 'no'})"
    keep, drop = (a, b) if a.n >= b.n else (b, a)
    if conn.execute(text("""SELECT count(*) FROM matches WHERE (home_team_id=:a AND away_team_id=:b)
                            OR (home_team_id=:b AND away_team_id=:a)"""), {"a": a.id, "b": b.id}).scalar():
        return "omitido", "se enfrentaron entre sí: son clubes distintos"
    if _seasons(conn, a.id) & _seasons(conn, b.id):
        return "omitido", "comparten temporada: no es el mismo club"
    if apply:
        for col in ("home_team_id", "away_team_id"):
            conn.execute(text(f"UPDATE matches SET {col} = :k WHERE {col} = :d"), {"k": keep.id, "d": drop.id})
        # weinston_baseline_all es una vista (agrega weinston_ratings): no se actualiza.
        for table in ("team_external_ids", "weinston_ratings"):
            _move(conn, table, "team_id", drop.id, keep.id)
        conn.execute(text("DELETE FROM teams WHERE id = :d"), {"d": drop.id})
    return "fusionado", f"{drop.n} partidos de id {drop.id} pasan a id {keep.id} ({keep.n} partidos)"


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

    resumen = {"fusionado": 0, "omitido": 0}
    with engine.begin() as conn:
        for a, b in PARES:
            estado, detalle = merge_pair(conn, a, b, args.apply)
            resumen[estado] += 1
            print(f"  {'✅' if estado == 'fusionado' else '⚠️ '} {a} + {b}: {detalle}")
    print(f"\nFusionados: {resumen['fusionado']} · omitidos: {resumen['omitido']}")
    print("✅ Cambios escritos." if args.apply else "ℹ️  Simulación: no se escribió nada. Repite con --apply para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
