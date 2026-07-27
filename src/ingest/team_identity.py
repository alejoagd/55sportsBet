# src/ingest/team_identity.py
"""
Resolución de identidad de equipos compartida entre todas las fuentes de ingesta
(API-Football, ESPN, y a futuro cualquier otra).

Reemplaza el patrón usado por el pipeline del Mundial de un diccionario de
normalización de nombres copy-pasteado por script (EXT_TO_DB/CSV_TO_DB en
seed_wc2026_r32_schedule.py, update_wc2026_r32_matches.py, etc.) por una única
tabla `team_external_ids(team_id, source, external_id)`: cada fuente resuelve
por su propio id numérico estable, y el primer cruce entre fuentes distintas
(p. ej. un club visto primero en API-Football y luego en ESPN) se hace una sola
vez por nombre normalizado, no en cada corrida.
"""
from __future__ import annotations
import unicodedata
from sqlalchemy import text
from sqlalchemy.engine import Connection


def normalize_name(name: str) -> str:
    """minúsculas, sin acentos/diacríticos, espacios colapsados — solo para comparar, nunca se guarda."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.lower().split())


class TeamResolver:
    """Resuelve/crea equipos dentro de una única conexión/transacción."""

    def __init__(self, conn: Connection):
        self.conn = conn
        self._by_source_id: dict[tuple[str, int], int] = {}
        self._by_name: dict[str, int] = {}
        for row in conn.execute(text("SELECT id, name FROM teams")).fetchall():
            self._by_name[normalize_name(row.name)] = row.id

    def resolve(self, name: str, league_id: int, source: str, external_id: int) -> int:
        key = (source, external_id)
        if key in self._by_source_id:
            return self._by_source_id[key]

        row = self.conn.execute(
            text("SELECT team_id FROM team_external_ids WHERE source = :source AND external_id = :eid"),
            {"source": source, "eid": external_id},
        ).fetchone()
        if row:
            self._by_source_id[key] = row.team_id
            return row.team_id

        norm = normalize_name(name)
        team_id = self._by_name.get(norm)
        if team_id is None:
            team_id = self.conn.execute(
                text("""
                    INSERT INTO teams (name, league_id, status)
                    VALUES (:name, :lid, 'active')
                    RETURNING id
                """),
                {"name": name.strip(), "lid": league_id},
            ).scalar_one()
            self._by_name[norm] = team_id

        self.conn.execute(
            text("""
                INSERT INTO team_external_ids (team_id, source, external_id)
                VALUES (:tid, :source, :eid)
                ON CONFLICT (source, external_id) DO NOTHING
            """),
            {"tid": team_id, "source": source, "eid": external_id},
        )
        self._by_source_id[key] = team_id
        return team_id
