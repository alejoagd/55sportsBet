import { Fragment, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import i18n, { localeTag } from './i18n';
import { useIsMobile } from './Hooks/useIsMobile';
import ProbabilityBar from './ProbabilityBar';
import { useLiveMatches } from './Hooks/useLiveMatches';
import type { LiveMatch } from './Hooks/useLiveMatches';
import { CombinedPlays, LiveBadge } from './LiveParts';
import { liveScoreText } from './Hooks/liveHelpers';

// Fila compacta de partidos, agrupada por fecha (no por jornada — no hay
// número de jornada real disponible para ninguna liga todavía). Muestra
// predicciones de Weinston únicamente (Poisson se sigue calculando y
// guardando, solo no se muestra en esta vista compacta).
//
// Desktop: tabla real con encabezados de columna (Probabilidad 1/X/2,
// Pred., Marcador Pred., Prom. Goles). Mobile: tarjeta por partido con las
// mismas columnas pero etiquetadas explícitamente, en vez de todo en una
// sola línea sin contexto.

export interface CompactMatch {
  match_id: number;
  date: string;
  kickoff_at?: string | null;
  home_team: string;
  home_team_logo?: string | null;
  away_team: string;
  away_team_logo?: string | null;
  actual_home_goals?: number | null;
  actual_away_goals?: number | null;
  weinston_home_goals?: number | null;
  weinston_away_goals?: number | null;
  weinston_prob_home?: number | null;
  weinston_prob_draw?: number | null;
  weinston_prob_away?: number | null;
  weinston_result?: string | null;
  weinston_hit_1x2?: boolean;
}

function TeamLogo({ url, alt, size = 'sm' }: { url?: string | null; alt: string; size?: 'sm' | 'lg' }) {
  const [failed, setFailed] = useState(false);
  const dim = size === 'lg' ? 'w-9 h-9 sm:w-10 sm:h-10' : 'w-5 h-5';
  if (!url || failed) {
    return (
      <span className={`${dim} rounded-full bg-slate-700/60 flex items-center justify-center shrink-0 ${size === 'lg' ? 'text-base' : 'text-xs'}`}>
        ⚽
      </span>
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      className={`${dim} object-contain shrink-0`}
      onError={() => setFailed(true)}
    />
  );
}

// Colores de acento por resultado (1/X/2), reusados en el badge de
// predicción para que combinen con ProbabilityBar en vez de ser siempre
// naranja sin importar el pronóstico.
const OUTCOME_STYLE: Record<string, string> = {
  '1': 'bg-blue-500/20 text-blue-400',
  'X': 'bg-slate-500/20 text-slate-300',
  '2': 'bg-orange-500/20 text-orange-400',
};

function matchDate(m: CompactMatch): Date | null {
  // kickoff_at es un instante real (con offset) -> new Date() lo parsea bien.
  // m.date es solo "YYYY-MM-DD" (sin hora): new Date(str) lo interpreta como
  // medianoche UTC, y al formatear en una zona horaria detrás de UTC (ej.
  // Colombia, UTC-5) el partido se corre un día hacia atrás. Por eso acá se
  // arma la fecha con los componentes locales, igual que en MatchDetail.tsx.
  if (m.kickoff_at) {
    const d = new Date(m.kickoff_at);
    return isNaN(d.getTime()) ? null : d;
  }
  const [year, month, day] = m.date.split('T')[0].split('-').map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

function formatDateHeader(m: CompactMatch): string {
  const d = matchDate(m);
  return d
    ? d.toLocaleDateString(localeTag(), { weekday: 'long', day: '2-digit', month: 'long' })
    : i18n.t('common.dateTbd');
}

function formatTime(m: CompactMatch): string {
  if (!m.kickoff_at) return i18n.t('common.timeTbd');
  const d = new Date(m.kickoff_at);
  return isNaN(d.getTime())
    ? i18n.t('common.timeTbd')
    : d.toLocaleTimeString(localeTag(), { hour: '2-digit', minute: '2-digit' });
}

function resultLabel(r?: string | null): string {
  if (r === 'H') return '1';
  if (r === 'A') return '2';
  return 'X';
}

interface RowData {
  m: CompactMatch;
  hasPrediction: boolean;
  predictedScore: string;
  avgGoals: string;
  actualScore: string | null;
}

function buildRow(m: CompactMatch, mode: 'upcoming' | 'results'): RowData {
  const hasPrediction = m.weinston_home_goals !== undefined && m.weinston_home_goals !== null;
  const predictedScore = hasPrediction
    ? `${Math.round(m.weinston_home_goals!)} - ${Math.round(m.weinston_away_goals!)}`
    : '—';
  const avgGoals = hasPrediction ? (m.weinston_home_goals! + m.weinston_away_goals!).toFixed(1) : '—';
  const actualScore = mode === 'results' && m.actual_home_goals != null && m.actual_away_goals != null
    ? `${m.actual_home_goals} - ${m.actual_away_goals}`
    : null;
  return { m, hasPrediction, predictedScore, avgGoals, actualScore };
}

function ResultBadge({ row, mode }: { row: RowData; mode: 'upcoming' | 'results' }) {
  const label = resultLabel(row.m.weinston_result);
  const hitColored = mode === 'results' && row.m.weinston_hit_1x2 !== undefined;
  const style = hitColored
    ? row.m.weinston_hit_1x2
      ? 'bg-green-500/20 text-green-400'
      : 'bg-red-500/20 text-red-400'
    : OUTCOME_STYLE[label];
  return (
    <span className={`inline-flex items-center justify-center min-w-[1.5rem] px-1.5 py-0.5 rounded-md font-bold text-xs ${style}`}>
      {label}
    </span>
  );
}

// ── Desktop: tabla con encabezados ─────────────────────────────────────────
function DesktopTable({
  groups,
  mode,
  onMatchClick,
  live,
}: {
  groups: CompactMatch[][];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
  live: Map<number, LiveMatch>;
}) {
  const { t } = useTranslation();
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700/70 shadow-lg shadow-black/10 overflow-hidden">
      <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm border-collapse">
        <thead>
          <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-700 bg-slate-900/50">
            <th className="text-left font-semibold px-4 py-3">{t('matchList.match')}</th>
            <th className="font-semibold px-3 py-3 w-44">{t('matchList.prob1x2')}</th>
            <th className="font-semibold px-2 py-3">{t('matchList.pred')}</th>
            <th className="font-semibold px-2 py-3">{t('matchList.score')}</th>
            <th className="font-semibold px-2 py-3">{t('matchList.goals')}</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((groupMatches) => (
            <Fragment key={groupMatches[0].match_id}>
              <tr>
                <td colSpan={5} className="bg-gradient-to-r from-slate-900/70 to-slate-900/30 text-slate-300 font-bold text-xs uppercase tracking-wide px-4 py-2 capitalize border-b border-slate-700/50">
                  {formatDateHeader(groupMatches[0])}
                </td>
              </tr>
              {groupMatches.map((m) => {
                const row = buildRow(m, mode);
                const lv = live.get(m.match_id);
                const enJuego = lv?.state === 'in';
                const marcadorVivo = liveScoreText(lv);
                return (
                  <tr
                    key={m.match_id}
                    onClick={() => onMatchClick(m.match_id)}
                    className={`group border-b border-slate-700/40 hover:bg-slate-700/30 cursor-pointer transition-colors ${enJuego ? 'bg-red-500/[0.04]' : ''}`}
                  >
                    <td className={`px-4 py-3 ${enJuego ? 'border-l-2 border-red-500/70' : ''}`}>
                      <div className="flex items-center gap-2.5 whitespace-nowrap">
                        {enJuego ? (
                          <span className="w-24 shrink-0"><LiveBadge live={lv!} compact /></span>
                        ) : (
                          <span className="text-slate-500 text-xs w-24 shrink-0 truncate" title={formatTime(m)}>{formatTime(m)}</span>
                        )}
                        <TeamLogo url={m.home_team_logo} alt={m.home_team} />
                        <span className="text-white font-semibold truncate max-w-[130px] group-hover:text-yellow-400 transition-colors">{m.home_team}</span>
                        <span className={`font-mono text-xs px-1 shrink-0 ${marcadorVivo ? 'text-white font-bold text-sm' : 'text-slate-500'}`}>{marcadorVivo ?? row.actualScore ?? 'vs'}</span>
                        <TeamLogo url={m.away_team_logo} alt={m.away_team} />
                        <span className="text-white font-semibold truncate max-w-[130px] group-hover:text-yellow-400 transition-colors">{m.away_team}</span>
                      </div>
                      {lv && <div className="pl-[6.5rem]"><CombinedPlays live={lv} /></div>}
                    </td>
                    {row.hasPrediction ? (
                      <>
                        <td className="px-3 py-3">
                          <div className="max-w-[150px]">
                            <ProbabilityBar home={m.weinston_prob_home} draw={m.weinston_prob_draw} away={m.weinston_prob_away} />
                          </div>
                        </td>
                        <td className="text-center px-2"><ResultBadge row={row} mode={mode} /></td>
                        <td className="text-center px-2">
                          <span className="inline-block bg-slate-900/60 text-white font-mono font-bold px-2.5 py-1 rounded-md">{row.predictedScore}</span>
                        </td>
                        <td className="text-center px-2">
                          <span className="text-slate-300 font-medium">⚽ {row.avgGoals}</span>
                        </td>
                      </>
                    ) : (
                      <td colSpan={4} className="text-center text-slate-500 text-xs px-2">{t('matchList.noPrediction')}</td>
                    )}
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

// ── Mobile: tarjeta por partido, con etiquetas explícitas ──────────────────
function MobileCards({
  groups,
  mode,
  onMatchClick,
  live,
}: {
  groups: CompactMatch[][];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
  live: Map<number, LiveMatch>;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-5">
      {groups.map((groupMatches) => (
        <div key={groupMatches[0].match_id} className="space-y-2.5">
          <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wide capitalize flex items-center gap-2">
            <span className="w-1 h-4 bg-yellow-400/70 rounded-full" />
            {formatDateHeader(groupMatches[0])}
          </h3>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))' }}>
            {groupMatches.map((m) => {
              const row = buildRow(m, mode);
              const lv = live.get(m.match_id);
              const enJuego = lv?.state === 'in';
              const marcadorVivo = liveScoreText(lv);
              return (
                <div
                  key={m.match_id}
                  onClick={() => onMatchClick(m.match_id)}
                  className={`bg-gradient-to-br from-slate-800 to-slate-800/80 rounded-xl border p-4 shadow-md shadow-black/10 active:scale-[0.99] hover:border-slate-600 transition-all cursor-pointer ${enJuego ? 'border-red-500/50' : 'border-slate-700/70'}`}
                >
                  <div className="flex items-center justify-between mb-3">
                    {enJuego ? (
                      <LiveBadge live={lv!} />
                    ) : (
                      <span className="inline-flex items-center gap-1 text-slate-400 text-[11px] font-medium bg-slate-900/50 px-2 py-0.5 rounded-full">
                        🕐 {formatTime(m)}
                      </span>
                    )}
                    {(row.actualScore || lv?.state === 'post') && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded-full font-bold">{t('matchList.fullTime')}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mb-4">
                    <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
                      <TeamLogo url={m.home_team_logo} alt={m.home_team} size="lg" />
                      <span className="text-white font-semibold text-xs sm:text-sm text-center line-clamp-2 break-words leading-tight w-full">{m.home_team}</span>
                    </div>
                    <div className="flex flex-col items-center shrink-0 px-1">
                      {marcadorVivo || row.actualScore ? (
                        <span className="text-white font-mono font-bold text-lg">{marcadorVivo ?? row.actualScore}</span>
                      ) : (
                        <span className="text-slate-400 font-bold text-[10px] bg-slate-900/60 rounded-full w-7 h-7 flex items-center justify-center">VS</span>
                      )}
                    </div>
                    <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
                      <TeamLogo url={m.away_team_logo} alt={m.away_team} size="lg" />
                      <span className="text-white font-semibold text-xs sm:text-sm text-center line-clamp-2 break-words leading-tight w-full">{m.away_team}</span>
                    </div>
                  </div>

                  {lv && <div className="-mt-2 mb-3 flex justify-center text-center"><CombinedPlays live={lv} /></div>}

                  {row.hasPrediction ? (
                    <>
                      <ProbabilityBar home={m.weinston_prob_home} draw={m.weinston_prob_draw} away={m.weinston_prob_away} size="lg" />
                      <div className="grid grid-cols-2 gap-2 mt-3">
                        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-2.5 py-1.5">
                          <ResultBadge row={row} mode={mode} />
                          <div className="min-w-0">
                            <div className="text-[9px] text-slate-500 uppercase tracking-wide leading-none">{t('matchList.prediction')}</div>
                            <div className="text-white font-mono font-bold text-sm leading-tight">{row.predictedScore}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-2.5 py-1.5">
                          <span className="text-base leading-none">⚽</span>
                          <div className="min-w-0">
                            <div className="text-[9px] text-slate-500 uppercase tracking-wide leading-none">{t('matchList.avgGoals')}</div>
                            <div className="text-white font-bold text-sm leading-tight">{row.avgGoals}</div>
                          </div>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-slate-500 text-xs text-center py-1.5 bg-slate-900/30 rounded-lg">{t('matchList.noPredictionAvailable')}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CompactMatchList({
  matches,
  mode,
  onMatchClick,
}: {
  matches: CompactMatch[];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
}) {
  const isMobileViewport = useIsMobile();
  const live = useLiveMatches();

  // La tabla necesita ~720px. Se decide por el ancho REAL del contenedor (no de
  // la pantalla): en tablet con el menú de ligas abierto la pantalla es ancha
  // pero el contenido no, y la tabla quedaba cortada a la derecha.
  const [wrapEl, setWrapEl] = useState<HTMLDivElement | null>(null);
  const [containerNarrow, setContainerNarrow] = useState<boolean | null>(null);
  useEffect(() => {
    if (!wrapEl) return;
    const ro = new ResizeObserver(([entry]) => setContainerNarrow(entry.contentRect.width < 720));
    ro.observe(wrapEl);
    return () => ro.disconnect();
  }, [wrapEl]);
  const isMobile = containerNarrow ?? isMobileViewport;

  const groups = useMemo(() => {
    const map = new Map<string, CompactMatch[]>();
    for (const m of matches) {
      const d = matchDate(m);
      const key = d ? d.toDateString() : 'unknown';
      (map.get(key) ?? map.set(key, []).get(key)!).push(m);
    }
    // Los partidos llegan de la API sin garantía de orden cronológico entre
    // fechas — hay que ordenar los grupos explícitamente. "upcoming" va de
    // la fecha más próxima hacia el futuro; "results" muestra lo más
    // reciente primero.
    const entries = Array.from(map.values()).map((group) =>
      [...group].sort((a, b) => (matchDate(a)?.getTime() ?? 0) - (matchDate(b)?.getTime() ?? 0))
    );
    entries.sort((a, b) => {
      const da = matchDate(a[0])?.getTime() ?? 0;
      const db = matchDate(b[0])?.getTime() ?? 0;
      return mode === 'results' ? db - da : da - db;
    });
    return entries;
  }, [matches, mode]);

  if (groups.length === 0) return null;

  return (
    <div ref={setWrapEl}>
      {isMobile
        ? <MobileCards groups={groups} mode={mode} onMatchClick={onMatchClick} live={live} />
        : <DesktopTable groups={groups} mode={mode} onMatchClick={onMatchClick} live={live} />}
    </div>
  );
}
