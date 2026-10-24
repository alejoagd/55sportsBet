import { useEffect, useState } from 'react';

// Indicador en el que un equipo se destaca dentro de su liga (ver src/analysis/team_highlights.py)
export type HighlightStat = 'goals' | 'shots' | 'shots_on_target' | 'corners' | 'fouls' | 'cards';

export interface Highlight {
  stat: HighlightStat;
  direction: 'most' | 'least';
  rank: number;
  of: number;
  value: number;
  league_avg: number;
  pj: number;            // partidos jugados por el equipo en esa condición (local o visitante)
}

export interface TeamSide {
  team_id: number;
  team: string;
  venue: 'home' | 'away';
  indicators: Highlight[];
}

export interface TeamHighlightsData {
  match_id: number;
  league: string;
  season_id: number;
  has_match_stats: boolean;
  top_n: number;
  home: TeamSide;
  away: TeamSide;
}

/** Indicadores destacados de los dos equipos del partido; null mientras carga o si no hay. */
export function useTeamHighlights(matchId: string | undefined): TeamHighlightsData | null {
  const [data, setData] = useState<TeamHighlightsData | null>(null);
  useEffect(() => {
    if (!matchId) return;
    const apiUrl: string = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    setData(null);
    fetch(`${apiUrl}/api/matches/${matchId}/team-highlights`)
      .then(r => (r.ok ? r.json() : null))
      .then((d: TeamHighlightsData | null) => setData(d))
      .catch(() => { /* sin indicadores: la tarjeta simplemente no se muestra */ });
  }, [matchId]);
  return data;
}
