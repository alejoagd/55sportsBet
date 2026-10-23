import { useTranslation } from 'react-i18next';
import type { LiveMatch, LivePlay } from './Hooks/useLiveMatches';
import { golesPorLado, periodoJugada, useLiveLabel } from './Hooks/liveHelpers';
import type { Periodo } from './Hooks/liveHelpers';

// Piezas visuales del "en vivo", compartidas por Hoy, la lista de la liga y el detalle.

/** Punto rojo que parpadea + EN VIVO + minuto. Solo para partidos en juego.
 *  `stacked`: EN VIVO arriba y el minuto abajo, para columnas angostas (la hora de las tarjetas). */
export function LiveBadge({ live, compact = false, stacked = false }: { live: LiveMatch; compact?: boolean; stacked?: boolean }) {
  const { t } = useTranslation();
  const label = useLiveLabel(live);
  if (live.state === 'post') {
    // Terminado: sin punto parpadeante ni "EN VIVO"
    return <span className="inline-flex items-center whitespace-nowrap rounded-full bg-green-500/15 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-green-400">{label}</span>;
  }
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
  if (p.shootout) return p.scoring ? '✅' : '❌';
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

/** Solo los goles, en una sola línea, coloreadas por equipo (azul local, naranja visitante,
 *  igual que el 1/X/2 de las predicciones). Para vistas donde no hay una fila por equipo. */
export function CombinedPlays({ live }: { live: LiveMatch | undefined }) {
  const { t } = useTranslation();
  if (!live) return null;
  const plays = live.plays.filter(p => p.scoring && !p.shootout).sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
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




function StatRow({ label, home, away, suffix = '' }: { label: string; home: number | undefined; away: number | undefined; suffix?: string }) {
  if (home === undefined && away === undefined) return null;
  const h = home ?? 0;
  const a = away ?? 0;
  const total = h + a;
  const pctHome = total > 0 ? (h / total) * 100 : 50;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="w-14 font-mono font-bold text-blue-300">{home ?? '–'}{home !== undefined && suffix}</span>
        <span className="text-xs text-slate-400">{label}</span>
        <span className="w-14 text-right font-mono font-bold text-orange-300">{away ?? '–'}{away !== undefined && suffix}</span>
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-slate-700/60">
        <div className="bg-blue-500/80" style={{ width: `${pctHome}%` }} />
        <div className="bg-orange-500/80" style={{ width: `${100 - pctHome}%` }} />
      </div>
    </div>
  );
}

/** Estadísticas en vivo de ambos equipos (posesión, tiros, córners, faltas, tarjetas).
 *  Solo se muestran las que ESPN informó; las ausentes no se rellenan con 0. */
export function LiveStatsPanel({ live, homeName, awayName }: { live: LiveMatch; homeName: string; awayName: string }) {
  const { t } = useTranslation();
  const h = live.stats?.home;
  const a = live.stats?.away;
  if (!h && !a) return null;
  return (
    <div className="rounded-lg border border-red-500/30 bg-slate-800 p-4 shadow-xl sm:p-6">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-white sm:text-xl">{t('live.statsTitle')}</h2>
        <LiveBadge live={live} />
      </div>
      <div className="mb-3 flex justify-between text-[11px] font-semibold uppercase tracking-wide">
        <span className="max-w-[45%] truncate text-blue-300">{homeName}</span>
        <span className="max-w-[45%] truncate text-orange-300">{awayName}</span>
      </div>
      <div className="space-y-3">
        <StatRow label={t('live.possession')} home={h?.possession} away={a?.possession} suffix="%" />
        <StatRow label={t('matchDetail.shots')} home={h?.shots} away={a?.shots} />
        <StatRow label={t('matchDetail.shotsOt')} home={h?.shots_on_target} away={a?.shots_on_target} />
        <StatRow label={t('matchDetail.corners')} home={h?.corners} away={a?.corners} />
        <StatRow label={t('matchDetail.fouls')} home={h?.fouls} away={a?.fouls} />
        <StatRow label={t('live.yellowCards2')} home={h?.yellow_cards} away={a?.yellow_cards} />
        <StatRow label={t('live.redCards2')} home={h?.red_cards} away={a?.red_cards} />
      </div>
    </div>
  );
}


function TimelineRow({ p, etiqueta }: { p: LivePlay; etiqueta?: string }) {
  const { t } = useTranslation();
  const texto = (
    <span className="leading-tight">
      {p.player ?? t(p.red ? 'live.redCard' : p.yellow ? 'live.yellowCard' : 'live.goal')}
      {p.own_goal && <span className="text-slate-500"> ({t('live.ownGoal')})</span>}
    </span>
  );
  const ico = <span className="shrink-0 leading-tight">{icon(p)}</span>;
  return (
    <div className="grid grid-cols-[1fr_3rem_1fr] items-start gap-1.5 text-sm sm:gap-2">
      <div className={`flex items-start justify-end gap-1 text-right ${p.side === 'home' ? 'text-blue-200' : ''}`}>
        {p.side === 'home' && <>{texto}{ico}</>}
      </div>
      <div className="pt-px text-center text-xs font-bold tabular-nums text-slate-300">{etiqueta ?? p.clock}</div>
      <div className={`flex items-start justify-start gap-1 text-left ${p.side === 'away' ? 'text-orange-200' : ''}`}>
        {p.side === 'away' && <>{ico}{texto}</>}
      </div>
    </div>
  );
}

/** Resumen del partido: línea de tiempo de goles y tarjetas, separada en primer y segundo tiempo
 *  (y prórroga si la hubo). Local a la izquierda, visitante a la derecha, minuto al centro.
 *  `data` null = el sondeo en vivo nunca vio este partido. */
export function MatchTimeline({ data, homeName, awayName }: { data: LiveMatch | null; homeName: string; awayName: string }) {
  const { t } = useTranslation();
  if (!data) return <div className="rounded-lg bg-slate-800 p-6 text-center text-sm text-slate-500">{t('live.noTimeline')}</div>;

  const plays = data.plays
    .filter(p => (p.scoring || p.red || p.yellow) && !p.shootout)
    .sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
  const tanda = data.plays.filter(p => p.shootout).sort((a, b) => (a.clock_s ?? 0) - (b.clock_s ?? 0));
  if (plays.length === 0 && tanda.length === 0) return <div className="rounded-lg bg-slate-800 p-6 text-center text-sm text-slate-500">{t('live.noEventsYet')}</div>;

  const secciones: { id: Periodo; titulo: string }[] = [
    { id: '1T', titulo: t('live.firstHalf') },
    { id: '2T', titulo: t('live.secondHalf') },
    { id: 'ET', titulo: t('live.extraTime') },
  ];
  // El marcador al descanso se deduce de las jugadas; solo se muestra si esas jugadas suman
  // exactamente el marcador actual (si ESPN dejó alguna sin registrar, mejor no mostrar un dato falso).
  const total = golesPorLado(plays);
  const coherente = total.home === data.home_score && total.away === data.away_score;
  const alDescanso = golesPorLado(plays.filter(p => periodoJugada(p.clock) === '1T'));

  return (
    <div className="rounded-lg bg-slate-800 p-4 sm:p-6 shadow-xl">
      <div className="mb-4 flex justify-between text-[11px] font-semibold uppercase tracking-wide">
        <span className="max-w-[45%] truncate text-blue-300">{homeName}</span>
        <span className="max-w-[45%] truncate text-orange-300">{awayName}</span>
      </div>
      <div className="space-y-5">
        {secciones.map(sec => {
          const delTiempo = plays.filter(p => periodoJugada(p.clock) === sec.id);
          if (delTiempo.length === 0) return null;
          return (
            <div key={sec.id}>
              <div className="mb-2 flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-700" />
                <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                  {sec.titulo}{sec.id === '1T' && coherente && ` · ${alDescanso.home}-${alDescanso.away}`}
                </span>
                <div className="h-px flex-1 bg-slate-700" />
              </div>
              <div className="space-y-2">
                {delTiempo.map((p, i) => <TimelineRow key={i} p={p} />)}
              </div>
            </div>
          );
        })}
        {tanda.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-3">
              <div className="h-px flex-1 bg-slate-700" />
              <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                {t('live.penalties')}
                {data.home_shootout != null && data.away_shootout != null && ` · ${data.home_shootout}-${data.away_shootout}`}
              </span>
              <div className="h-px flex-1 bg-slate-700" />
            </div>
            <div className="space-y-2">
              {tanda.map((p, i) => <TimelineRow key={i} p={p} etiqueta={`#${i + 1}`} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
