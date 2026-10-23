import { useTranslation } from 'react-i18next';
import type { LiveMatch, LivePlay } from './Hooks/useLiveMatches';
import { relevant, useLiveLabel } from './Hooks/liveHelpers';

// Piezas visuales del "en vivo", compartidas por Hoy, la lista de la liga y el detalle.

/** Punto rojo que parpadea + EN VIVO + minuto. Solo para partidos en juego.
 *  `stacked`: EN VIVO arriba y el minuto abajo, para columnas angostas (la hora de las tarjetas). */
export function LiveBadge({ live, compact = false, stacked = false }: { live: LiveMatch; compact?: boolean; stacked?: boolean }) {
  const { t } = useTranslation();
  const label = useLiveLabel(live);
  const dot = (
    <span className="relative flex h-1.5 w-1.5 shrink-0">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-red-500" />
    </span>
  );
  if (stacked) {
    return (
      <span className="inline-flex max-w-full flex-col items-center gap-0.5 rounded-lg bg-red-500/15 px-2 py-1 text-red-400">
        <span className="flex items-center gap-1 text-[10px] font-bold uppercase leading-none tracking-wide">{dot}{t('live.live')}</span>
        <span className="text-xs font-bold leading-tight tabular-nums">{label}</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-bold text-red-400">
      {dot}
      {!compact && <span className="uppercase tracking-wide">{t('live.live')}</span>}
      <span className="tabular-nums">{label}</span>
    </span>
  );
}

function icon(p: LivePlay): string {
  return p.red ? '🟥' : p.yellow ? '🟨' : '⚽';
}

function describe(p: LivePlay, ownGoalLabel: string): string {
  const who = p.player ? ` ${p.player}` : '';
  return `${p.clock ?? ''}${who}${p.own_goal ? ` (${ownGoalLabel})` : ''}`.trim();
}

/** Línea pequeña de jugadas bajo el nombre del equipo: "⚽ 5' Demirovic · 🟨 44' Sauer". */
export function PlayLine({ plays }: { plays: LivePlay[] }) {
  const { t } = useTranslation();
  if (plays.length === 0) return null;
  return (
    <div className="mt-0.5 flex flex-wrap gap-x-2.5 gap-y-0.5 pl-[34px] text-[11px] leading-tight text-slate-400">
      {plays.map((p, i) => (
        <span key={i} className="whitespace-nowrap" title={t(p.red ? 'live.redCard' : p.yellow ? 'live.yellowCard' : 'live.goal')}>
          {icon(p)} {describe(p, t('live.ownGoal'))}
        </span>
      ))}
    </div>
  );
}

/** Todas las jugadas en una sola línea, coloreadas por equipo (azul local, naranja visitante,
 *  igual que el 1/X/2 de las predicciones). Para vistas donde no hay una fila por equipo. */
export function CombinedPlays({ live }: { live: LiveMatch | undefined }) {
  const { t } = useTranslation();
  if (!live) return null;
  const plays = live.plays.filter(relevant).sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
  if (plays.length === 0) return null;
  const color = (p: LivePlay) => (p.side === 'home' ? 'text-blue-300' : p.side === 'away' ? 'text-orange-300' : 'text-slate-400');
  return (
    <div className="mt-1 flex flex-wrap gap-x-2.5 gap-y-0.5 text-[11px] leading-tight">
      {plays.map((p, i) => (
        <span key={i} className={`whitespace-nowrap ${color(p)}`}>
          {icon(p)} {describe(p, t('live.ownGoal'))}
        </span>
      ))}
    </div>
  );
}


/** Columna vertical de jugadas de un equipo, para el detalle del partido. */
export function PlayColumn({ plays, align }: { plays: LivePlay[]; align: 'left' | 'right' }) {
  const { t } = useTranslation();
  if (plays.length === 0) return <div />;
  return (
    <div className={`space-y-0.5 text-xs text-slate-300 ${align === 'right' ? 'text-right' : 'text-left'}`}>
      {plays.map((p, i) => (
        <div key={i}>{icon(p)} {describe(p, t('live.ownGoal'))}</div>
      ))}
    </div>
  );
}
