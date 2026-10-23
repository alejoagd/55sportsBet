"""
Mapeo de un partido de ESPN a un partido de nuestra BD.

Por qué por nombre y fecha: los partidos de las ligas europeas y del Brasileirao no tienen
`espn_event_id` y esos equipos no tienen id externo de ESPN (vienen de los CSV de
football-data.co.uk, con nombres como "Man United", "Nott'm Forest" o "M'gladbach", mientras
ESPN dice "Manchester United", "Nottingham Forest", "Borussia Mönchengladbach").

Por qué es seguro: no se compara contra todos los equipos de la liga, solo contra los
partidos de esa liga programados en una ventana de ±1 día (a lo sumo unas decenas), con el
mismo local y visitante que ESPN. Aun así se exige un mínimo de parecido en AMBOS nombres y
que el mejor candidato le gane al segundo; si hay duda no se mapea (se registra y se omite).
Al mapear se guarda el espn_event_id, así los siguientes ciclos no repiten el cálculo.
"""
from __future__ import annotations
import difflib
import re
import unicodedata
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.live.espn_live import LiveEvent

MIN_PARECIDO = 0.65      # mínimo por equipo
MIN_VENTAJA = 0.15       # el mejor candidato debe superar al segundo por esto
_RUIDO = {"fc", "cf", "sc", "ac", "as", "cd", "ca", "club", "de", "del", "la", "el", "los", "las",
          "afc", "ssc", "us", "sv", "fk", "sd", "ud", "rc", "the", "1", "04", "05"}


def _normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 ]", "", s.replace("'", "").replace(".", " "))


# Apodos de los CSV de football-data.co.uk que no se parecen a la forma completa de ESPN
_ALIAS = {
    "wolves": "wolverhampton wanderers", "spurs": "tottenham hotspur",
    "cologne": "koln", "fc cologne": "koln", "1 fc cologne": "koln",   # ESPN en inglés vs "FC Koln"
    "la coruna": "deportivo", "deportivo la coruna": "deportivo",       # "La Coruna" vs "Deportivo"
}


def _tokens(s: str) -> list[str]:
    norm = _normalizar(s).strip()
    t = [x for x in _ALIAS.get(norm, norm).split() if x not in _RUIDO]
    return t or _normalizar(s).split()


def _es_abreviatura(corto: str, largo: str) -> bool:
    """'nottm' en 'nottingham', 'mgladbach' en 'monchengladbach': mismas primeras letras y
    las demás aparecen en orden dentro de la palabra larga."""
    if len(corto) < 3 or corto[0] != largo[0] or len(corto) > len(largo):
        return False
    it = iter(largo)
    return all(c in it for c in corto)


def _parecido_token(a: str, b: str) -> float:
    if a == b:
        return 1.0
    c, l = (a, b) if len(a) <= len(b) else (b, a)
    if l.startswith(c) and len(c) >= 3:
        return 0.9
    if _es_abreviatura(c, l):
        return 0.85
    return difflib.SequenceMatcher(None, a, b).ratio() * 0.8


def parecido(a: str, b: str) -> float:
    """0..1 entre dos nombres de equipo. Simétrico."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    corto, largo = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    por_token = sum(max(_parecido_token(x, y) for y in largo) for x in corto) / len(corto)
    # Si el nombre largo tiene tokens de más ("Real" + "Madrid" vs "Madrid") se penaliza poco,
    # pero un equipo distinto con solo la ciudad en común no debe pasar el umbral.
    exceso = (len(largo) - len(corto)) * 0.12
    plano = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return max(por_token - exceso, plano)


def _candidatos(conn: Connection, ev: LiveEvent) -> list[dict]:
    if ev.kickoff is None:
        return []
    d = ev.kickoff.date()
    rows = conn.execute(text("""
        SELECT m.id, m.home_goals, m.away_goals, m.season_id, m.espn_event_id, th.name AS home, ta.name AS away
        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN leagues l ON l.id = s.league_id
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        WHERE l.name = :liga AND m.date BETWEEN :d1 AND :d2
    """), {"liga": ev.league, "d1": d - timedelta(days=1), "d2": d + timedelta(days=1)}).mappings().all()
    return [dict(r) for r in rows]


def encontrar_partido(conn: Connection, ev: LiveEvent) -> tuple[dict | None, str]:
    """(partido, motivo). El partido trae id, season_id, resultado actual y nombres de la BD.
    Si no se puede mapear con seguridad devuelve (None, motivo)."""
    por_id = conn.execute(text("""
        SELECT m.id, m.home_goals, m.away_goals, m.season_id, m.espn_event_id, th.name AS home, ta.name AS away
        FROM matches m JOIN teams th ON th.id = m.home_team_id JOIN teams ta ON ta.id = m.away_team_id
        WHERE m.espn_event_id = :e"""), {"e": ev.espn_event_id}).mappings().all()
    if len(por_id) == 1:
        return dict(por_id[0]), "espn_event_id"
    if len(por_id) > 1:
        return None, f"espn_event_id repetido en {len(por_id)} partidos"

    puntuados = []
    for c in _candidatos(conn, ev):
        if c["espn_event_id"] not in (None, ev.espn_event_id):
            continue  # ya está ligado a otro evento de ESPN
        ph, pa = parecido(ev.home_name, c["home"]), parecido(ev.away_name, c["away"])
        if ph >= MIN_PARECIDO and pa >= MIN_PARECIDO:
            puntuados.append((ph + pa, c))
    if not puntuados:
        return None, "sin candidato parecido en la BD"
    puntuados.sort(key=lambda x: -x[0])
    if len(puntuados) > 1 and puntuados[0][0] - puntuados[1][0] < MIN_VENTAJA:
        return None, "ambiguo: dos candidatos igual de parecidos"
    return puntuados[0][1], "nombre+fecha"
