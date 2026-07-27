# src/ingest/competitions_config.py
"""
Definición única de las 5 competencias nuevas (Brasileirao, Liga Argentina,
Liga Betplay, Copa Libertadores, Copa Sudamericana) y helpers get_or_create
de liga/temporada compartidos por el backfill histórico (API-Football) y el
sync diario (ESPN).
"""
from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.engine import Connection

COMPETITIONS: list[dict] = [
    {
        "key": "brasileirao",
        "name": "Brasileirao",
        "country": "Brazil",
        "kind": "league",
        "api_football_league_id": 71,
        "espn_slug": "bra.1",
    },
    {
        "key": "liga_argentina",
        "name": "Liga Argentina",
        "country": "Argentina",
        "kind": "league",
        "api_football_league_id": 128,
        "espn_slug": "arg.1",
    },
    {
        "key": "liga_betplay",
        "name": "Liga Betplay",
        "country": "Colombia",
        "kind": "league",
        "api_football_league_id": 239,
        "espn_slug": "col.1",
    },
    {
        "key": "copa_libertadores",
        "name": "Copa Libertadores",
        "country": "South America",
        "kind": "cup",
        "api_football_league_id": 13,
        "espn_slug": "conmebol.libertadores",
    },
    {
        "key": "copa_sudamericana",
        "name": "Copa Sudamericana",
        "country": "South America",
        "kind": "cup",
        "api_football_league_id": 11,
        "espn_slug": "conmebol.sudamericana",
    },
]


def get_competition(key: str) -> dict:
    for c in COMPETITIONS:
        if c["key"] == key:
            return c
    raise KeyError(f"Competencia desconocida: {key}")


def get_or_create_league(conn: Connection, name: str, country: str) -> int:
    row = conn.execute(text("SELECT id FROM leagues WHERE name = :name"), {"name": name}).fetchone()
    if row:
        return row.id
    return conn.execute(
        text("INSERT INTO leagues (name, country) VALUES (:name, :country) RETURNING id"),
        {"name": name, "country": country},
    ).scalar_one()


def get_or_create_season(conn: Connection, league_id: int, year: int) -> int:
    row = conn.execute(
        text("SELECT id FROM seasons WHERE league_id = :lid AND year_start = :ys"),
        {"lid": league_id, "ys": year},
    ).fetchone()
    if row:
        return row.id
    return conn.execute(
        text("""
            INSERT INTO seasons (league_id, year_start, year_end)
            VALUES (:lid, :ys, :ye)
            RETURNING id
        """),
        {"lid": league_id, "ys": year, "ye": year},
    ).scalar_one()
