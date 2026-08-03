import { Fragment, useMemo, useState } from 'react';
import { useIsMobile } from './Hooks/useIsMobile';

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

function TeamLogo({ url, alt }: { url?: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return <span className="text-base leading-none shrink-0">⚽</span>;
  }
  return (
    <img
      src={url}
      alt={alt}
      className="w-5 h-5 object-contain shrink-0"
      onError={() => setFailed(true)}
    />
  );
}

function matchDate(m: CompactMatch): Date | null {
  const iso = m.kickoff_at || m.date;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

function formatDateHeader(m: CompactMatch): string {
  const d = matchDate(m);
  return d ? d.toLocaleDateString('es-CO', { weekday: 'long', day: '2-digit', month: 'long' }) : 'Fecha por confirmar';
}

function formatTime(m: CompactMatch): string {
  if (!m.kickoff_at) return 'Hora por confirmar';
  const d = new Date(m.kickoff_at);
  return isNaN(d.getTime()) ? 'Hora por confirmar' : d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
}

function resultLabel(r?: string | null): string {
  if (r === 'H') return '1';
  if (r === 'A') return '2';
  return 'X';
}

function pct(v?: number | null): string {
  return v !== undefined && v !== null ? `${(v * 100).toFixed(0)}%` : '—';
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
  const colored = mode === 'results' && row.m.weinston_hit_1x2 !== undefined;
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded font-bold text-xs ${
        colored
          ? row.m.weinston_hit_1x2
            ? 'bg-green-500/20 text-green-400'
            : 'bg-red-500/20 text-red-400'
          : 'bg-orange-500/20 text-orange-400'
      }`}
    >
      {resultLabel(row.m.weinston_result)}
    </span>
  );
}

// ── Desktop: tabla con encabezados ─────────────────────────────────────────
function DesktopTable({
  groups,
  mode,
  onMatchClick,
}: {
  groups: CompactMatch[][];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
}) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-700 bg-slate-900/40">
            <th className="text-left font-semibold px-3 py-2">Partido</th>
            <th className="font-semibold px-2 py-2" colSpan={3}>Probabilidad %</th>
            <th className="font-semibold px-2 py-2">Pred.</th>
            <th className="font-semibold px-2 py-2">Marcador Pred.</th>
            <th className="font-semibold px-2 py-2">Prom. Goles</th>
          </tr>
          <tr className="text-slate-500 text-[11px] border-b border-slate-700">
            <th></th>
            <th className="font-normal px-1 py-1">1</th>
            <th className="font-normal px-1 py-1">X</th>
            <th className="font-normal px-1 py-1">2</th>
            <th colSpan={3}></th>
          </tr>
        </thead>
        <tbody>
          {groups.map((groupMatches) => (
            <Fragment key={groupMatches[0].match_id}>
              <tr>
                <td colSpan={7} className="bg-slate-900/60 text-slate-300 font-bold text-xs uppercase tracking-wide px-3 py-1.5 capitalize">
                  {formatDateHeader(groupMatches[0])}
                </td>
              </tr>
              {groupMatches.map((m) => {
                const row = buildRow(m, mode);
                return (
                  <tr
                    key={m.match_id}
                    onClick={() => onMatchClick(m.match_id)}
                    className="border-b border-slate-700/50 hover:bg-slate-700/40 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2 whitespace-nowrap">
                        <span className="text-slate-500 text-xs w-14 shrink-0">{formatTime(m)}</span>
                        <TeamLogo url={m.home_team_logo} alt={m.home_team} />
                        <span className="text-white font-medium truncate max-w-[120px]">{m.home_team}</span>
                        <span className="text-slate-400 font-mono text-xs px-1 shrink-0">{row.actualScore ?? 'vs'}</span>
                        <TeamLogo url={m.away_team_logo} alt={m.away_team} />
                        <span className="text-white font-medium truncate max-w-[120px]">{m.away_team}</span>
                      </div>
                    </td>
                    {row.hasPrediction ? (
                      <>
                        <td className="text-center text-white px-1">{pct(m.weinston_prob_home)}</td>
                        <td className="text-center text-white px-1">{pct(m.weinston_prob_draw)}</td>
                        <td className="text-center text-white px-1">{pct(m.weinston_prob_away)}</td>
                        <td className="text-center px-2"><ResultBadge row={row} mode={mode} /></td>
                        <td className="text-center text-white font-mono px-2">{row.predictedScore}</td>
                        <td className="text-center text-slate-300 px-2">{row.avgGoals}</td>
                      </>
                    ) : (
                      <td colSpan={6} className="text-center text-slate-500 text-xs px-2">Sin predicción</td>
                    )}
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Mobile: tarjeta por partido, con etiquetas explícitas ──────────────────
function MobileCards({
  groups,
  mode,
  onMatchClick,
}: {
  groups: CompactMatch[][];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
}) {
  return (
    <div className="space-y-5">
      {groups.map((groupMatches) => (
        <div key={groupMatches[0].match_id} className="space-y-2">
          <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wide capitalize">
            {formatDateHeader(groupMatches[0])}
          </h3>
          <div className="space-y-2">
            {groupMatches.map((m) => {
              const row = buildRow(m, mode);
              return (
                <div
                  key={m.match_id}
                  onClick={() => onMatchClick(m.match_id)}
                  className="bg-slate-800 rounded-lg border border-slate-700 p-3 active:bg-slate-700/40 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-500 text-xs">{formatTime(m)}</span>
                    {row.actualScore && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded font-bold">FT</span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex items-center gap-1.5 flex-1 min-w-0">
                      <TeamLogo url={m.home_team_logo} alt={m.home_team} />
                      <span className="text-white font-medium text-sm truncate">{m.home_team}</span>
                    </div>
                    <span className="text-white font-mono text-sm px-2 shrink-0">{row.actualScore ?? 'vs'}</span>
                    <div className="flex items-center gap-1.5 flex-1 min-w-0 justify-end text-right">
                      <span className="text-white font-medium text-sm truncate">{m.away_team}</span>
                      <TeamLogo url={m.away_team_logo} alt={m.away_team} />
                    </div>
                  </div>

                  {row.hasPrediction ? (
                    <>
                      <div className="grid grid-cols-3 gap-1 bg-slate-900/50 rounded p-1.5 mb-2 text-center">
                        <div>
                          <div className="text-slate-500 text-[10px]">1</div>
                          <div className="text-white text-xs font-semibold">{pct(m.weinston_prob_home)}</div>
                        </div>
                        <div className="border-x border-slate-700">
                          <div className="text-slate-500 text-[10px]">X</div>
                          <div className="text-white text-xs font-semibold">{pct(m.weinston_prob_draw)}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 text-[10px]">2</div>
                          <div className="text-white text-xs font-semibold">{pct(m.weinston_prob_away)}</div>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-500">Predicción</span>
                          <ResultBadge row={row} mode={mode} />
                          <span className="text-white font-mono">{row.predictedScore}</span>
                        </div>
                        <div className="text-slate-500">
                          Prom. goles <span className="text-slate-300">{row.avgGoals}</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-slate-500 text-xs text-center py-1">Sin predicción disponible</div>
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
  const isMobile = useIsMobile();

  const groups = useMemo(() => {
    const map = new Map<string, CompactMatch[]>();
    for (const m of matches) {
      const d = matchDate(m);
      const key = d ? d.toDateString() : 'unknown';
      (map.get(key) ?? map.set(key, []).get(key)!).push(m);
    }
    return Array.from(map.values());
  }, [matches]);

  if (groups.length === 0) return null;

  return isMobile
    ? <MobileCards groups={groups} mode={mode} onMatchClick={onMatchClick} />
    : <DesktopTable groups={groups} mode={mode} onMatchClick={onMatchClick} />;
}
