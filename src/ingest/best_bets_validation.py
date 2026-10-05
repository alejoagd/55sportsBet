"""
Validación de best bets para las competencias que NO pasan por el flujo
"finish" de run_update_automated.py (Liga Argentina, Liga Betplay, Copa
Libertadores, Copa Sudamericana y Brasileirao).

Ese flujo solo recorre las ligas de LeagueManager.LEAGUE_CSV_MAPPING
(europeas), así que las best bets de estas 5 competencias quedaban con
validated_at = NULL para siempre y seguían apareciendo como pendientes en
/best-bets aunque el partido ya tuviera resultado. Los scripts de sync
(update_competitions_espn_sync.py, sync_brasileirao_football_data.py)
llaman a esto justo después de cargar resultados.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def validate_pending_best_bets(conn: Connection, season_id: int) -> tuple[int, int, int]:
    """Valida las best bets pendientes de la temporada que ya tienen resultado.

    Usa la función SQL validate_best_bets() (la misma que /api/best-bets/validate).
    Retorna (validadas, aciertos, fallos).
    """
    row = conn.execute(
        text("SELECT * FROM validate_best_bets(:season_id)"),
        {"season_id": season_id},
    ).fetchone()
    if row is None:
        return 0, 0, 0
    return row[0] or 0, row[1] or 0, row[2] or 0
