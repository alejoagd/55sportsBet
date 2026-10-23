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

/** Jugadas de un equipo (o las sin lado conocido si side === null), en orden cronológico.
 *  Por defecto solo goles (lo que va en las tarjetas de afuera); con `conTarjetas`, también
 *  amarillas y rojas (el detalle del partido). */
export function playsFor(live: LiveMatch | undefined, side: 'home' | 'away' | null, conTarjetas = false): LivePlay[] {
  if (!live) return [];
  return live.plays
    .filter(p => (conTarjetas ? relevant(p) : p.scoring) && (p.side ?? null) === side)
    .sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
}

/** "2 - 1" con la tanda de penales entre paréntesis si la hubo; null si ESPN no dio marcador. */
export function liveScoreText(live: LiveMatch | undefined): string | null {
  if (!live || (live.state !== 'in' && live.state !== 'post')) return null;
  if (live.home_score == null || live.away_score == null) return null;
  const pen = live.home_shootout != null && live.away_shootout != null ? ` (${live.home_shootout}-${live.away_shootout})` : '';
  return `${live.home_score} - ${live.away_score}${pen}`;
}


export type EstadoLinea = { estado: 'cumplida' | 'perdida' | 'pendiente'; n: number };

/** Estado en vivo de una línea de apuesta, con el MISMO criterio que el acierto en la base de
 *  datos (cli.py): OVER acierta si total > línea y UNDER si total < línea, ambos estrictos. Con una
 *  línea entera (4.0) y total = 4 no acierta ninguno de los dos.
 *  Las estadísticas solo crecen durante el partido, así que algunas conclusiones ya son
 *  definitivas: un OVER que supera la línea queda cumplido y un UNDER que ya no puede quedar por
 *  debajo queda perdido, pase lo que pase después.
 *  `n`: cuántas faltan para cumplir un OVER, o cuánto margen queda a un UNDER. */
export function estadoLinea(prediccion: string | undefined, linea: number | undefined, total: number | null): EstadoLinea | null {
  if (total == null || linea == null || !prediccion) return null;
  if (prediccion.toLowerCase() === 'over') {
    const minimo = Math.floor(linea) + 1;                       // línea 9.5 -> 10; línea 26 -> 27
    return total >= minimo ? { estado: 'cumplida', n: 0 } : { estado: 'pendiente', n: minimo - total };
  }
  const maximo = Number.isInteger(linea) ? linea - 1 : Math.floor(linea);   // línea 9.5 -> 9; línea 4 -> 3
  return total > maximo ? { estado: 'perdida', n: 0 } : { estado: 'pendiente', n: maximo - total };
}
