import { useTranslation } from 'react-i18next';
import { hayDestacados } from './Hooks/highlightHelpers';
import type { Highlight, TeamHighlightsData, TeamSide } from './Hooks/useTeamHighlights';

// Tarjeta "Lo más destacado de cada equipo": en qué estadística cada equipo sale entre los 5 de arriba o
// los 5 de abajo de las tablas del módulo de Estadísticas (como local o visitante, según su condición
// en este partido). No es un ranking general de la liga: es una posición por cada estadística.
// El más marcado va destacado; el resto, más discretos. Si un equipo no se destaca en nada, se
// dice (no se inventa un indicador).

const MAX_POR_EQUIPO = 3;

function Indicador({ h, venue, principal, color }: { h: Highlight; venue: 'home' | 'away'; principal: boolean; color: 'blue' | 'orange' }) {
  const { t } = useTranslation();
  const mas = h.direction === 'most';
  const stat = t(`highlights.stat_${h.stat}`);
  // Los goles usan los nombres del módulo de Estadísticas (Mejor/Peor ofensiva); el resto, "Más/Menos ..."
  const titulo = h.stat === 'goals'
    ? t(mas ? 'highlights.bestOffense' : 'highlights.worstOffense')
    : t(mas ? 'highlights.most' : 'highlights.least', { stat });
  const ring = color === 'blue' ? 'ring-blue-500/40 bg-blue-500/10' : 'ring-orange-500/40 bg-orange-500/10';
  return (
    <div className={`rounded-lg px-3 py-2 ${principal ? `ring-1 ${ring}` : 'bg-slate-800/60'}`}>
      <div className="flex items-start gap-2">
        <span className={`mt-0.5 shrink-0 ${mas ? 'text-green-400' : 'text-sky-400'}`} aria-hidden>{mas ? '🔺' : '🔻'}</span>
        <div className="min-w-0 flex-1">
          <div className={`font-semibold leading-tight text-white ${principal ? 'text-sm' : 'text-xs'}`}>{titulo}</div>
          <div className="mt-0.5 text-[11px] font-semibold leading-tight text-slate-200">
            {t('highlights.position', {
              rank: h.rank, of: h.of,
              venue: t(venue === 'home' ? 'highlights.venueHome' : 'highlights.venueAway'),
            })}
          </div>
          <div className="mt-0.5 text-[11px] leading-tight text-slate-400">
            {t('highlights.detail', { v: h.value, pj: h.pj, avg: h.league_avg })}
          </div>
        </div>
        {h.rank === 1 && (
          <span className="shrink-0 rounded bg-yellow-400/20 px-1.5 py-0.5 text-[10px] font-bold text-yellow-300">#1</span>
        )}
      </div>
    </div>
  );
}

function Columna({ side, color }: { side: TeamSide; color: 'blue' | 'orange' }) {
  const { t } = useTranslation();
  const lista = side.indicators.slice(0, MAX_POR_EQUIPO);
  return (
    <div className="min-w-0">
      <div className={`mb-2 truncate text-xs font-bold uppercase tracking-wide ${color === 'blue' ? 'text-blue-300' : 'text-orange-300'}`}>
        {side.team}
      </div>
      <div className="space-y-1.5">
        {lista.length === 0 && <div className="rounded-lg bg-slate-800/40 px-3 py-2 text-xs text-slate-500">{t('highlights.none')}</div>}
        {lista.map((h, i) => <Indicador key={h.stat} h={h} venue={side.venue} principal={i === 0} color={color} />)}
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
      <p className="mb-3 mt-0.5 text-[11px] text-slate-400">{t('highlights.subtitle', { top: data.top_n })}</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Columna side={data.home} color="blue" />
        <Columna side={data.away} color="orange" />
      </div>
    </div>
  );
}
