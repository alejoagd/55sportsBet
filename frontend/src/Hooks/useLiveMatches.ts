import { useEffect, useState } from 'react';

const API_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Jugada (gol/tarjeta) tal como la guarda el sondeo en vivo. `side` dice de qué equipo es
// para pintarla bajo el escudo correcto; puede faltar en filas guardadas antes de que el
// backend lo informara (se rellena solo en la siguiente lectura de ESPN).
export interface LivePlay {
  type: string | null;
  clock: string | null;
  clock_s?: number | null;
  side?: 'home' | 'away' | null;
  player?: string | null;
  scoring: boolean;
  red: boolean;
  yellow: boolean;
  own_goal?: boolean;
}

export interface LiveMatch {
  match_id: number;
  league_name: string;
  state: 'pre' | 'in' | 'post';
  status_name: string | null;
  detail: string | null;
  clock: string | null;
  period: number | null;
  // null = ESPN no dio marcador (nunca se rellena con 0)
  home_score: number | null;
  away_score: number | null;
  home_shootout: number | null;
  away_shootout: number | null;
  plays: LivePlay[];
}

type Listener = (m: Map<number, LiveMatch>) => void;

// Un único sondeo para toda la app: Hoy, la lista de la liga y el detalle comparten la misma
// consulta aunque estén montados a la vez. Cada 20 s si hay algo en juego, cada 60 s si no, y
// pausado mientras la pestaña está oculta (no gasta batería ni llamadas al API).
const FAST_MS = 20_000;
const IDLE_MS = 60_000;

let cache = new Map<number, LiveMatch>();
const listeners = new Set<Listener>();
let timer: ReturnType<typeof setTimeout> | null = null;
let inflight = false;

async function tick() {
  timer = null;
  if (listeners.size === 0) return;
  if (document.hidden) { schedule(IDLE_MS); return; }
  if (!inflight) {
    inflight = true;
    try {
      const r = await fetch(`${API_URL}/api/matches/live`);
      if (r.ok) {
        const rows: LiveMatch[] = await r.json();
        cache = new Map(rows.map(x => [x.match_id, x]));
        listeners.forEach(l => l(cache));
      }
    } catch { /* sin red: se conserva lo último y se reintenta */ }
    finally { inflight = false; }
  }
  schedule([...cache.values()].some(m => m.state === 'in') ? FAST_MS : IDLE_MS);
}

function schedule(ms: number) {
  if (timer) clearTimeout(timer);
  timer = setTimeout(tick, ms);
}

// Al volver a la pestaña se actualiza de inmediato en vez de esperar al próximo ciclo
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && listeners.size > 0) { schedule(0); }
  });
}

/** Partidos en juego (y terminados hace menos de 30 min) indexados por match_id. */
export function useLiveMatches(): Map<number, LiveMatch> {
  const [live, setLive] = useState<Map<number, LiveMatch>>(cache);
  useEffect(() => {
    listeners.add(setLive);
    setLive(cache);
    if (listeners.size === 1) schedule(0);
    return () => {
      listeners.delete(setLive);
      if (listeners.size === 0 && timer) { clearTimeout(timer); timer = null; }
    };
  }, []);
  return live;
}
