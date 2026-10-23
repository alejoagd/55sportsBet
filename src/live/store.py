"""
Persistencia del sondeo en vivo.

Regla de oro: mientras el partido está en juego el marcador parcial vive SOLO en match_live.
matches.home_goals/away_goals se escriben una única vez, al terminar (y se corrigen si ESPN
los cambia después). Si no, evaluate() y las posiciones tratarían un 1-0 al minuto 20 como
resultado final.
"""
from __future__ import annotations
import contextlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.ingest.best_bets_validation import validate_pending_best_bets
from src.live.espn_live import LiveEvent

DDL = (Path(__file__).resolve().parents[2] / "migrations" / "add_match_live.sql").read_text(encoding="utf-8")


def asegurar_tabla(conn: Connection) -> None:
    conn.execute(text(DDL))


def vincular_evento(conn: Connection, match_id: int, espn_event_id: int) -> None:
    """Guarda el id de ESPN en el partido para no volver a mapear por nombre. No pisa uno existente."""
    conn.execute(text("UPDATE matches SET espn_event_id = :e WHERE id = :m AND espn_event_id IS NULL"),
                 {"e": espn_event_id, "m": match_id})


def guardar_en_vivo(conn: Connection, match_id: int, ev: LiveEvent) -> dict | None:
    """Upsert del estado en vivo. Devuelve la fila anterior (o None) para detectar cambios."""
    anterior = conn.execute(text("SELECT state, detail, home_score, away_score, plays FROM match_live WHERE match_id = :m"),
                            {"m": match_id}).mappings().first()
    conn.execute(text("""
        INSERT INTO match_live (match_id, espn_event_id, state, status_name, detail, clock, period,
                                home_score, away_score, home_shootout, away_shootout, plays,
                                first_live_at, finished_at, updated_at)
        VALUES (:m, :e, :st, :sn, :d, :c, :p, :hs, :as_, :hso, :aso, CAST(:pl AS jsonb),
                CASE WHEN :st = 'in' THEN now() END, CASE WHEN :done THEN now() END, now())
        ON CONFLICT (match_id) DO UPDATE SET
            state = EXCLUDED.state, status_name = EXCLUDED.status_name, detail = EXCLUDED.detail,
            clock = EXCLUDED.clock, period = EXCLUDED.period,
            home_score = EXCLUDED.home_score, away_score = EXCLUDED.away_score,
            home_shootout = EXCLUDED.home_shootout, away_shootout = EXCLUDED.away_shootout,
            plays = EXCLUDED.plays,
            first_live_at = COALESCE(match_live.first_live_at, EXCLUDED.first_live_at),
            finished_at = COALESCE(match_live.finished_at, EXCLUDED.finished_at),
            updated_at = now()
    """), {"m": match_id, "e": ev.espn_event_id, "st": ev.state, "sn": ev.status_name, "d": ev.detail,
           "c": ev.clock, "p": ev.period, "hs": ev.home_score, "as_": ev.away_score,
           "hso": ev.home_shootout, "aso": ev.away_shootout, "pl": json.dumps(ev.plays),
           "done": ev.tiene_resultado})
    return dict(anterior) if anterior else None


def guardar_estadisticas(conn: Connection, match_id: int, stats: dict) -> None:
    """Guarda las estadísticas de equipo en vivo en match_live (la fila ya debe existir)."""
    conn.execute(text("UPDATE match_live SET stats = CAST(:s AS jsonb) WHERE match_id = :m"),
                 {"s": json.dumps({**stats, "updated_at": datetime.now(timezone.utc).isoformat()}), "m": match_id})


def ganador_penales(ev: LiveEvent, home: str, away: str) -> str | None:
    """Nombre (de la BD) del equipo que ganó la tanda; None si no hubo o está empatada/sin dato."""
    if ev.home_shootout is None or ev.away_shootout is None or ev.home_shootout == ev.away_shootout:
        return None
    return home if ev.home_shootout > ev.away_shootout else away


def resultado_regular(h: int, a: int) -> str:
    return "H" if h > a else ("A" if a > h else "D")


def finalizar(conn: Connection, match: dict, ev: LiveEvent) -> str:
    """Pasa el resultado a matches. Devuelve 'nuevo', 'corregido' o 'igual'.

    El marcador es el del tiempo reglamentario (en un 0-0 definido por penales queda 0-0, 'D');
    el ganador de la tanda va en penalty_winner. Si cambió algo, valida las best bets de la
    temporada, igual que el resto de caminos de ingesta.
    """
    h, a = ev.home_score, ev.away_score
    antes = (match["home_goals"], match["away_goals"])
    if antes == (h, a):
        return "igual"
    conn.execute(text("""
        UPDATE matches SET home_goals = :h, away_goals = :a, fulltime_result = :ft,
               penalty_winner = COALESCE(:pw, penalty_winner)
        WHERE id = :m"""), {"h": h, "a": a, "ft": resultado_regular(h, a),
                            "pw": ganador_penales(ev, match["home"], match["away"]), "m": match["id"]})
    validate_pending_best_bets(conn, match["season_id"])
    return "nuevo" if antes == (None, None) else "corregido"


def regenerar_aciertos(match_id: int, season_id: int) -> dict:
    """prediction_outcomes de ESE partido. evaluate() abre su propia transacción, así que va
    después de confirmar la de finalizar(). Imprime cada partido; se silencia."""
    from src.predictions.evaluate import evaluate
    with contextlib.redirect_stdout(io.StringIO()):
        return evaluate(season_id=season_id, only_matches=[match_id])
