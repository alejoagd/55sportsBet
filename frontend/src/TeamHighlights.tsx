import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowDown, ArrowUp, Crosshair, Flag, Goal, Hand, Square, Target } from 'lucide-react';
import { hayDestacados } from './Hooks/highlightHelpers';
import type { Highlight, HighlightStat, TeamHighlightsData, TeamSide } from './Hooks/useTeamHighlights';

// Tarjeta "Lo más destacado de cada equipo": en qué estadística cada equipo sale entre los 5 de arriba o
// los 5 de abajo de las tablas del módulo de Estadísticas (como local o visitante, según su condición en
// este partido). No es un ranking general de la liga: es una posición por cada estadística.
//
// Es un dato valioso, así que se muestra para llamar la atención y leerse de un vistazo: icono de la
// estadística, medalla con el puesto (oro/plata/bronce) y una barra contra el promedio de la liga. Las
// flechas van en verde (más) y azul (menos), nunca en rojo: "menos" no es "malo", es una característica.

const MAX_POR_EQUIPO = 3;

type Icono = ComponentType<{ className?: string }>;
const ICONO: Record<HighlightStat, { Icon: Icono; clase: string }> = {
  goals: { Icon: Goal, clase: 'text-emerald-300' },
  shots: { Icon: Crosshair, clase: 'text-sky-300' },
  shots_on_target: { Icon: Target, clase: 'text-violet-300' },
  corners: { Icon: Flag, clase: 'text-amber-300' },
  fouls: { Icon: Hand, clase: 'text-orange-300' },
  cards: { Icon: Square, clase: 'fill-yellow-400 text-yellow-400' },
};

// Medalla del puesto: el #1 en oro, #2 plata, #3 bronce y el resto neutro
function medalla(rank: number): string {
  if (rank === 1) return 'bg-gradient-to-br from-amber-300 to-yellow-500 text-slate-900 shadow-lg shadow-amber-500/30';
  if (rank === 2) return 'bg-gradient-to-br from-slate-100 to-slate-300 text-slate-900';
  if (rank === 3) return 'bg-gradient-to-br from-orange-300 to-amber-600 text-slate-900';
  return 'bg-slate-700 text-white';
}

/** Barra del valor del equipo contra el promedio de la liga (marca vertical). */
function BarraVsLiga({ valor, promedio, color }: { valor: number; promedio: number; color: string }) {
  const tope = Math.max(valor, promedio) * 1.2 || 1;
  return (
    <div className="relative mt-1.5 h-1.5 rounded-full bg-slate-700/80">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, (valor / tope) * 100)}%` }} />
      <div className="absolute -top-[3px] h-[12px] w-0.5 rounded bg-white/80" style={{ left: `${Math.min(100, (promedio / tope) * 100)}%` }} />
    </div>
  );
}

function Indicador({ h, principal, color }: { h: Highlight; principal: boolean; color: 'blue' | 'orange' }) {
  const { t } = useTranslation();
  const mas = h.direction === 'most';
  const { Icon, clase } = ICONO[h.stat];
  // Los goles usan los nombres del módulo de Estadísticas (Mejor/Peor ofensiva); el resto, "Más/Menos ..."
  const titulo = h.stat === 'goals'
    ? t(mas ? 'highlights.bestOffense' : 'highlights.worstOffense')
    : t(mas ? 'highlights.most' : 'highlights.least', { stat: t(`highlights.stat_${h.stat}`) });
  return (
    <div className={`rounded-xl p-3 ring-1 ${principal
      ? 'bg-gradient-to-br from-amber-400/15 via-slate-800 to-slate-800 ring-amber-400/40'
      : 'bg-slate-800/70 ring-slate-700/60'}`}>
      {/* Fila 1: icono + qué estadística + medalla con el puesto */}
      <div className="flex items-center gap-3">
        <div className="relative shrink-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-700/70">
            <Icon className={`h-5 w-5 ${clase}`} />
          </div>
          {/* Más = flecha verde hacia arriba; menos = flecha azul hacia abajo */}
          <span className={`absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full ring-2 ring-slate-800 ${mas ? 'bg-emerald-500' : 'bg-sky-500'}`}>
            {mas ? <ArrowUp className="h-2.5 w-2.5 text-white" strokeWidth={3} /> : <ArrowDown className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
          </span>
        </div>
        <div className={`min-w-0 flex-1 font-bold leading-tight text-white ${principal ? 'text-base' : 'text-sm'}`}>{titulo}</div>
        <div className={`flex h-12 w-[4.5rem] shrink-0 flex-col items-center justify-center rounded-xl ${medalla(h.rank)}`}>
          <span className="text-lg font-black leading-none">#{h.rank}</span>
          <span className="mt-0.5 whitespace-nowrap text-[9px] font-semibold leading-none opacity-80">{t('highlights.ofTeams', { of: h.of })}</span>
        </div>
      </div>
      {/* Fila 2: el valor del equipo contra el promedio de la liga, a todo el ancho */}
      <BarraVsLiga valor={h.value} promedio={h.league_avg} color={color === 'blue' ? 'bg-blue-400' : 'bg-orange-400'} />
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 text-[11px] leading-tight text-slate-400">
        <span>
          <span className="font-bold text-white">{t('highlights.perMatch', { v: h.value })}</span>
          <span className="text-slate-500"> · {t('highlights.leagueAvg', { v: h.league_avg })}</span>
        </span>
        <span className="text-slate-500">{t('highlights.matches', { n: h.pj })}</span>
      </div>
    </div>
  );
}

function Columna({ side, color }: { side: TeamSide; color: 'blue' | 'orange' }) {
  const { t } = useTranslation();
  const lista = side.indicators.slice(0, MAX_POR_EQUIPO);
  const local = side.venue === 'home';
  return (
    <div className="min-w-0">
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className={`text-sm font-bold uppercase tracking-wide ${color === 'blue' ? 'text-blue-300' : 'text-orange-300'}`}>{side.team}</span>
        <span className="shrink-0 rounded-full bg-slate-700/60 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
          {local ? '🏠' : '✈️'} {t(local ? 'highlights.venueHome' : 'highlights.venueAway')}
        </span>
      </div>
      <div className="space-y-2">
        {lista.length === 0 && <div className="rounded-xl bg-slate-800/40 px-3 py-3 text-xs text-slate-500">{t('highlights.none')}</div>}
        {lista.map((h, i) => <Indicador key={h.stat} h={h} principal={i === 0} color={color} />)}
      </div>
    </div>
  );
}

export default function TeamHighlights({ data }: { data: TeamHighlightsData | null }) {
  const { t } = useTranslation();
  if (!data || !hayDestacados(data)) return null;
  return (
    <div className="rounded-lg border border-slate-700/70 bg-slate-800 p-4 shadow-xl sm:p-5">
      <h2 className="text-base font-bold text-white sm:text-lg">⭐ {t('highlights.title')}</h2>
      <p className="mt-0.5 text-[11px] text-slate-400">{t('highlights.subtitleShort')}</p>
      {/* La explicación completa, a un toque: no hace falta verla siempre */}
      {/* Leyenda: qué es la barra y qué es la marca blanca */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-1.5 w-5 rounded-full bg-gradient-to-r from-blue-400 to-orange-400" />{t('highlights.legendTeam')}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-0.5 rounded bg-white/80" />{t('highlights.legendAvg')}
        </span>
      </div>
      <details className="mb-3 mt-2">
        <summary className="inline-block cursor-pointer select-none text-[11px] font-semibold text-sky-300 hover:text-sky-200">{t('highlights.howTitle')}</summary>
        <p className="mt-1 text-[11px] leading-snug text-slate-400">{t('highlights.subtitle', { top: data.top_n })}</p>
      </details>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Columna side={data.home} color="blue" />
        <Columna side={data.away} color="orange" />
      </div>
    </div>
  );
}
