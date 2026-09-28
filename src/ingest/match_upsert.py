# src/ingest/match_upsert.py
"""
Upsert genérico de partidos, compartido por el backfill histórico (API-Football,
clave api_football_fixture_id) y el sync diario (ESPN, clave espn_event_id).

Prioriza la clave externa de la fuente que llama; si no hay match por esa
clave, cae a (season_id, home_id, away_id, date) para evitar duplicar si el
mismo partido ya existe por otra vía.
"""
from __future__ import annotations
from datetime import date as DateType, datetime, timedelta
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
    if existing is None:
        # Fallback final: sin api_football_fixture_id/espn_event_id (ej.
        # fuente football-data.org) y sin coincidencia de fecha exacta, el
        # mismo partido puede ya existir bajo una fecha "por confirmar" que
        # no coincide con la fecha real una vez se confirma el calendario —
        # sin esto, cada confirmación insertaba un duplicado en vez de
        # actualizar el que ya estaba (visto en Brasileirao). Se busca entre
        # partidos NO jugados del mismo local/visitante en una ventana de
        # fechas acotada, no más amplia porque el mismo par puede repetirse
        # (ida/vuelta) meses después.
        existing = conn.execute(
            text("""
                SELECT id, home_goals FROM matches
                WHERE season_id = :sid AND home_team_id = :hid AND away_team_id = :aid
                  AND home_goals IS NULL
                  AND date BETWEEN :start AND :end
                ORDER BY date
                LIMIT 1
            """),
            {
                "sid": season_id, "hid": home_id, "aid": away_id,
                "start": match_date - timedelta(days=21),
                "end": match_date + timedelta(days=21),
            },
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
                    date = :d,
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

    _retire_stale_bracket_placeholder(conn, season_id=season_id, stage=stage,
                                       match_date=match_date, home_id=home_id, away_id=away_id,
                                       new_match_id=new_id)

    return new_id, "inserted"


# Equipos "por definir" que ESPN usa para sembrar de antemano los cupos de
# cuartos/semis/final antes de que se conozca quién avanza (ver teams.id 757
# "TBD Home" / 758 "TBD Away"). Cuando el cruce real se confirma, ESPN lo
# publica como un evento NUEVO (espn_event_id distinto al del placeholder),
# así que upsert_match nunca lo reconoce como "el mismo partido" y siempre
# termina en un INSERT - dejando el placeholder huérfano en el bracket con
# los nombres "TBD Home"/"TBD Away" para siempre si nadie lo retira.
_TBD_HOME_TEAM_ID = 757
_TBD_AWAY_TEAM_ID = 758


def _retire_stale_bracket_placeholder(
    conn: Connection, *, season_id: int, stage: str | None, match_date: DateType,
    home_id: int, away_id: int, new_match_id: int,
) -> None:
    if stage in (None, "regular", "group"):
        return
    if home_id == _TBD_HOME_TEAM_ID or away_id == _TBD_AWAY_TEAM_ID:
        return  # el que se acaba de insertar es él mismo un placeholder

    stale = conn.execute(
        text("""
            SELECT id, date FROM matches
            WHERE season_id = :sid AND stage = :stage
              AND id != :new_id
              AND home_goals IS NULL
              AND (
                    (home_team_id = :tbd_h OR away_team_id = :tbd_a)
                 OR (home_team_id IN (:hid, :aid) AND away_team_id IN (:hid, :aid))
              )
            ORDER BY ABS(date - :d)
            LIMIT 1
        """),
        {"sid": season_id, "stage": stage, "d": match_date, "new_id": new_match_id,
         "tbd_h": _TBD_HOME_TEAM_ID, "tbd_a": _TBD_AWAY_TEAM_ID,
         "hid": home_id, "aid": away_id},
    ).fetchone()
    if stale is None:
        return
    # Ventana angosta a propósito: en una ronda a ida y vuelta puede haber más
    # de un placeholder/duplicado pendiente (una pierna sí confirmada, la otra
    # no) - solo se retira el más cercano en fecha, no todos los de esa
    # stage/temporada. La segunda condición del WHERE de arriba (mismo par de
    # equipos, no jugado) cubre además el caso de una fila que alguien ya
    # corrigió a mano con los equipos reales antes de que ESPN publicara el
    # evento oficial - si no, ese arreglo manual también quedaría huérfano en
    # cuanto llegue el fixture real.
    if abs((stale.date - match_date).days) > 14:
        return

    # matches.id tiene FKs con delete_rule NO ACTION desde varias tablas de
    # predicciones (el placeholder, al ser un partido "próximo" más, ya suele
    # tener su fila de Poisson/Weinston/betting-lines generada) - hay que
    # limpiarlas antes o el DELETE de abajo revienta por violación de FK.
    # h2h_scoring / h2h_recommended_picks sí son ON DELETE CASCADE, no hace
    # falta tocarlas a mano.
    for dependent_table in (
        "betting_lines_predictions", "match_stats", "poisson_predictions",
        "weinston_predictions", "wc_scoring_events",
    ):
        conn.execute(text(f"DELETE FROM {dependent_table} WHERE match_id = :id"), {"id": stale.id})
    conn.execute(text("DELETE FROM matches WHERE id = :id"), {"id": stale.id})
