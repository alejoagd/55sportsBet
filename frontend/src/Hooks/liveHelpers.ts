import { useTranslation } from 'react-i18next';
import type { LiveMatch, LivePlay } from './useLiveMatches';

// Funciones del "en vivo" sin JSX (van aparte de LiveParts.tsx para que ese archivo solo
// exporte componentes, como exige la recarga rápida de React).

/** Solo goles y tarjetas; el resto de jugadas no se muestran. */
export function relevant(p: LivePlay): boolean {
  return p.scoring || p.red || p.yellow;
}

/** Texto de estado: minuto, Descanso, Penales o Final. */
export function useLiveLabel(live: LiveMatch): string {
  const { t } = useTranslation();
  if (live.state === 'post') return t('live.final');
  if (live.status_name === 'STATUS_SHOOTOUT' || live.detail === 'Penalties') return t('live.penalties');
  if (live.detail === 'HT') return t('live.halftime');
  return live.clock ?? live.detail ?? '';
}

/** Jugadas de un equipo (o las sin lado conocido si side === null), en orden cronológico. */
export function playsFor(live: LiveMatch | undefined, side: 'home' | 'away' | null): LivePlay[] {
  if (!live) return [];
  return live.plays
    .filter(p => relevant(p) && (p.side ?? null) === side)
    .sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
}

/** "2 - 1" con la tanda de penales entre paréntesis si la hubo; null si ESPN no dio marcador. */
export function liveScoreText(live: LiveMatch | undefined): string | null {
  if (!live || (live.state !== 'in' && live.state !== 'post')) return null;
  if (live.home_score == null || live.away_score == null) return null;
  const pen = live.home_shootout != null && live.away_shootout != null ? ` (${live.home_shootout}-${live.away_shootout})` : '';
  return `${live.home_score} - ${live.away_score}${pen}`;
}
