import type { Highlight, HighlightStat, TeamHighlightsData } from './useTeamHighlights';

export interface StatChip extends Highlight {
  side: 'home' | 'away';
  team: string;
  venue: 'home' | 'away';
}

/** Equipos del partido que se destacan en UNA estadística (para mostrar en su línea de apuesta). */
export function chipsDeStat(data: TeamHighlightsData | null, stat: HighlightStat): StatChip[] {
  if (!data) return [];
  const out: StatChip[] = [];
  for (const side of ['home', 'away'] as const) {
    const t = data[side];
    const h = t.indicators.find(i => i.stat === stat);
    if (h) out.push({ ...h, side, team: t.team, venue: t.venue });
  }
  return out;
}

/** ¿Hay algún indicador destacado en cualquiera de los dos equipos? */
export function hayDestacados(data: TeamHighlightsData | null): boolean {
  return !!data && (data.home.indicators.length > 0 || data.away.indicators.length > 0);
}
