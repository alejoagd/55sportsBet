# src/ingest/match_upsert.py
"""
Upsert genérico de partidos, compartido por el backfill histórico (API-Football,
clave api_football_fixture_id) y el sync diario (ESPN, clave espn_event_id).

Prioriza la clave externa de la fuente que llama; si no hay match por esa
clave, cae a (season_id, home_id, away_id, date) para evitar duplicar si el
mismo partido ya existe por otra vía.
"""
from __future__ import annotations
from datetime import date as DateType, datetime
from sqlalchemy import text
from sqlalchemy.engine import Connection


def fulltime_result(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "H"
    if away_goals > home_goals:
        return "A"
    return "D"


def upsert_match(
    conn: Connection,
    *,
    season_id: int,
    match_date: DateType,
    home_id: int,
    away_id: int,
    home_goals: int | None,
    away_goals: int | None,
    stage: str | None = None,
    round_label: str | None = None,
    group_name: str | None = None,
    api_football_fixture_id: int | None = None,
    espn_event_id: int | None = None,
    kickoff_at: datetime | None = None,
) -> tuple[int, str]:
    """Retorna (match_id, accion) con accion en {"inserted", "updated", "skipped"}."""
    existing = None
    if api_football_fixture_id is not None:
        existing = conn.execute(
            text("SELECT id, home_goals FROM matches WHERE api_football_fixture_id = :x"),
            {"x": api_football_fixture_id},
        ).fetchone()
    if existing is None and espn_event_id is not None:
        existing = conn.execute(
            text("SELECT id, home_goals FROM matches WHERE espn_event_id = :x"),
            {"x": espn_event_id},
        ).fetchone()
    if existing is None:
        existing = conn.execute(
            text("""
                SELECT id, home_goals FROM matches
                WHERE season_id = :sid AND home_team_id = :hid AND away_team_id = :aid AND date = :d
            """),
            {"sid": season_id, "hid": home_id, "aid": away_id, "d": match_date},
        ).fetchone()

    ft = fulltime_result(home_goals, away_goals)
    params = {
        "id": existing.id if existing else None,
        "sid": season_id,
        "d": match_date,
        "hid": home_id,
        "aid": away_id,
        "hg": home_goals,
        "ag": away_goals,
        "ft": ft,
        "stage": stage,
        "rl": round_label,
        "gn": group_name,
        "afid": api_football_fixture_id,
        "eeid": espn_event_id,
        "kat": kickoff_at,
    }

    if existing:
        had_result_before = existing.home_goals is not None
        conn.execute(
            text("""
                UPDATE matches SET
                    home_goals = COALESCE(:hg, home_goals),
                    away_goals = COALESCE(:ag, away_goals),
                    fulltime_result = COALESCE(:ft, fulltime_result),
                    stage = COALESCE(:stage, stage),
                    round_label = COALESCE(:rl, round_label),
                    group_name = :gn,
                    api_football_fixture_id = COALESCE(:afid, api_football_fixture_id),
                    espn_event_id = COALESCE(:eeid, espn_event_id),
                    kickoff_at = COALESCE(:kat, kickoff_at)
                WHERE id = :id
            """),
            params,
        )
        action = "updated" if (not had_result_before and home_goals is not None) else "skipped"
        return existing.id, action

    new_id = conn.execute(
        text("""
            INSERT INTO matches (
                season_id, date, home_team_id, away_team_id, home_goals, away_goals,
                fulltime_result, stage, round_label, group_name,
                api_football_fixture_id, espn_event_id, kickoff_at
            ) VALUES (
                :sid, :d, :hid, :aid, :hg, :ag,
                :ft, :stage, :rl, :gn,
                :afid, :eeid, :kat
            ) RETURNING id
        """),
        params,
    ).scalar_one()
    return new_id, "inserted"
