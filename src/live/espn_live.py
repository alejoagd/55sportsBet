"""
Lectura en vivo de ESPN (endpoint compacto `site.api`): una sola llamada por liga trae,
para cada partido, estado, reloj, marcador, penales y las jugadas (goles y tarjetas).

Por qué este endpoint y no la API core del sync diario: la core necesita ~4 llamadas por
partido; esta una por liga. Medido en un partido real (Libertadores, 2026-10-22): el CDN de
ESPN cachea 0-10 s, las respuestas tardan 0.15-0.4 s y el endpoint core va unos 12 s por
delante en los cambios de estado. Sondear cada 30 s es suficiente.

Ojo con los estados (aprendido en ese mismo partido):
- La Libertadores ya no juega prórroga: tras el 90' va directo a penales. ESPN lo expone
  como state='in', name='STATUS_SHOOTOUT' y, al terminar, 'FT-Pens'. El marcador del juego
  queda 0-0 y los penales viajan aparte (shootoutScore).
- El `winner` del endpoint core vino en False para los dos equipos; el compacto sí lo marcó.
- Hay jugadas que ESPN carga tarde y fuera de orden (una amarilla del 65' apareció después
  de la del 66', ~4 min tarde). El marcador final se toma del estado del partido, nunca de
  contar jugadas.
"""
from __future__ import annotations
import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime

from src.ingest.competitions_config import COMPETITIONS

SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"

# competición (nombre en la BD) -> slug de ESPN
SLUGS: dict[str, str] = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Serie A": "ita.1",
    "Bundesliga": "ger.1",
    **{c["name"]: c["espn_slug"] for c in COMPETITIONS},
}

# Estados terminales que NO son un resultado (el partido no se jugó o no terminó)
NO_RESULTADO = ("POSTPONED", "CANCELED", "CANCELLED", "SUSPENDED", "ABANDONED", "DELAYED")


@dataclass
class LiveEvent:
    espn_event_id: int
    league: str
    kickoff: datetime | None
    home_name: str
    away_name: str
    state: str                 # pre | in | post
    status_name: str           # STATUS_FIRST_HALF, STATUS_SHOOTOUT, STATUS_FULL_TIME...
    detail: str                # "HT", "73'", "Penalties", "FT-Pens"
    clock: str | None
    period: int | None
    completed: bool
    home_score: int | None
    away_score: int | None
    home_shootout: int | None = None
    away_shootout: int | None = None
    winner: str | None = None  # 'home' | 'away' | None (solo cuando ESPN lo marca)
    plays: list[dict] = field(default_factory=list)

    @property
    def tiene_resultado(self) -> bool:
        """Terminado de verdad: no pospuesto/cancelado/suspendido y con marcador."""
        return (self.state == "post" and self.completed and self.home_score is not None
                and self.away_score is not None
                and not any(x in self.status_name.upper() for x in NO_RESULTADO))

    @property
    def en_juego(self) -> bool:
        return self.state == "in"


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_event(raw: dict, league: str) -> LiveEvent | None:
    """Convierte un evento del scoreboard; None si no tiene la forma esperada."""
    try:
        comp = raw["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        st = raw["status"]
        tipo = st["type"]
        kickoff = None
        if raw.get("date"):
            kickoff = datetime.fromisoformat(raw["date"].replace("Z", "+00:00"))
        winner = "home" if home.get("winner") else ("away" if away.get("winner") else None)
        pre = tipo["state"] == "pre"   # antes de empezar ESPN manda "0": no es un marcador
        plays = []
        for p in comp.get("details", []) or []:
            plays.append({
                "type": (p.get("type") or {}).get("text"),
                "clock": (p.get("clock") or {}).get("displayValue"),
                "clock_s": (p.get("clock") or {}).get("value"),
                "team_id": (p.get("team") or {}).get("id"),
                "scoring": bool(p.get("scoringPlay")),
                "red": bool(p.get("redCard")),
                "yellow": bool(p.get("yellowCard")),
                "own_goal": bool(p.get("ownGoal")),
                "penalty": bool(p.get("penaltyKick")),
            })
        return LiveEvent(
            espn_event_id=int(raw["id"]), league=league, kickoff=kickoff,
            home_name=home["team"]["displayName"], away_name=away["team"]["displayName"],
            state=tipo["state"], status_name=tipo.get("name", ""), detail=tipo.get("detail", ""),
            clock=st.get("displayClock"), period=st.get("period"), completed=bool(tipo.get("completed")),
            home_score=None if pre else _int(home.get("score")), away_score=None if pre else _int(away.get("score")),
            home_shootout=_int(home.get("shootoutScore")), away_shootout=_int(away.get("shootoutScore")),
            winner=winner, plays=plays,
        )
    except (KeyError, StopIteration, TypeError, ValueError):
        return None


def fetch_events(league: str, fechas: list[str | None] | None = None, timeout: int = 20) -> list[LiveEvent]:
    """Partidos de una liga. Lanza si ESPN no responde.

    `fechas`: lista de 'YYYYMMDD' o None (= el día actual de ESPN, que incluye los partidos
    en juego). Este endpoint NO acepta rangos (devuelve 400): una llamada por fecha.
    """
    vistos: dict[int, LiveEvent] = {}
    for f in (fechas or [None]):
        url = SITE.format(slug=SLUGS[league]) + (f"?dates={f}&limit=100" if f else "?limit=100")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        for raw in data.get("events", []):
            ev = parse_event(raw, league)
            if ev is not None:
                vistos[ev.espn_event_id] = ev
    return list(vistos.values())
