# src/ingest/stage_mapping.py
"""
Vocabulario único de `stage` para partidos de copa (grupos + eliminatorias),
compartido por todas las fuentes de ingesta (API-Football, ESPN).

Reemplaza la inferencia por rango de fechas que usaba el pipeline del Mundial
(WorldCupDashboard.tsx `getMatchRound()`) — aquí el stage se deriva directo del
string de ronda que ya entrega la fuente (`league.round` en API-Football,
`series.title`/`season.slug` en ESPN).
"""
from __future__ import annotations

# Orden importa: "Quarter-finals"/"Semi-finals" contienen la subcadena "final",
# así que quarter/semi deben revisarse antes que "final".
_ORDERED_KEYWORDS: list[tuple[str, str]] = [
    ("quarter", "quarterfinal"),
    ("semi", "semifinal"),
    ("third place", "third_place"),
    ("final", "final"),
    ("round of 16", "round_of_16"),
    ("round of 32", "round_of_32"),
    ("group", "group"),
    ("regular season", "regular"),
]


def map_stage(round_label: str | None) -> str:
    """Mapea un string de ronda crudo (de cualquier fuente) al vocabulario fijo de `stage`."""
    if not round_label:
        return "regular"
    lower = round_label.lower()
    for keyword, stage in _ORDERED_KEYWORDS:
        if keyword in lower:
            return stage
    if "round" in lower or "play" in lower:
        return "preliminary"
    return "regular"
