import { useMemo, useState } from 'react';

// Fila compacta de partidos, agrupada por fecha (no por jornada — no hay
// número de jornada real disponible para ninguna liga todavía). Muestra
// predicciones de Weinston únicamente (Poisson se sigue calculando y
// guardando, solo no se muestra en esta vista compacta).

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

export default function CompactMatchList({
  matches,
  mode,
  onMatchClick,
}: {
  matches: CompactMatch[];
  mode: 'upcoming' | 'results';
  onMatchClick: (matchId: number) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<string, CompactMatch[]>();
    for (const m of matches) {
      const d = matchDate(m);
      const key = d ? d.toDateString() : 'unknown';
      (map.get(key) ?? map.set(key, []).get(key)!).push(m);
    }
    return Array.from(map.values());
  }, [matches]);

  return (
    <div className="space-y-6">
      {groups.map((groupMatches) => (
        <div key={groupMatches[0].match_id} className="space-y-2">
          <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wide capitalize">
            {formatDateHeader(groupMatches[0])}
          </h3>
          <div className="bg-slate-800 rounded-lg border border-slate-700 divide-y divide-slate-700 overflow-hidden">
            {groupMatches.map((m) => {
              const hasPrediction = m.weinston_home_goals !== undefined && m.weinston_home_goals !== null;
              const predictedScore = hasPrediction
                ? `${Math.round(m.weinston_home_goals!)} - ${Math.round(m.weinston_away_goals!)}`
                : '—';
              const avgGoals = hasPrediction ? (m.weinston_home_goals! + m.weinston_away_goals!).toFixed(1) : '—';
              const actualScore = mode === 'results' && m.actual_home_goals != null && m.actual_away_goals != null
                ? `${m.actual_home_goals} - ${m.actual_away_goals}`
                : null;

              return (
                <div
                  key={m.match_id}
                  onClick={() => onMatchClick(m.match_id)}
                  className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 px-3 py-2.5 hover:bg-slate-700/40 transition-colors cursor-pointer text-sm"
                >
                  {/* Hora + equipos + marcador */}
                  <div className="flex items-center gap-2 sm:w-72 shrink-0">
                    <span className="text-slate-500 text-xs w-16 shrink-0">{formatTime(m)}</span>
                    <div className="flex items-center gap-1.5 min-w-0 flex-1 justify-end text-right">
                      <span className="text-white font-medium truncate">{m.home_team}</span>
                      <TeamLogo url={m.home_team_logo} alt={m.home_team} />
                    </div>
                    <span className="text-slate-300 font-mono text-xs px-1 shrink-0">
                      {actualScore ?? 'vs'}
                    </span>
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      <TeamLogo url={m.away_team_logo} alt={m.away_team} />
                      <span className="text-white font-medium truncate">{m.away_team}</span>
                    </div>
                  </div>

                  {/* Predicción Weinston */}
                  {hasPrediction ? (
                    <div className="flex items-center gap-3 sm:gap-4 flex-wrap text-xs pl-[4.5rem] sm:pl-0">
                      <div className="flex items-center gap-1 text-slate-500">
                        1 <span className="text-white">{pct(m.weinston_prob_home)}</span>
                        <span className="ml-1">X</span> <span className="text-white">{pct(m.weinston_prob_draw)}</span>
                        <span className="ml-1">2</span> <span className="text-white">{pct(m.weinston_prob_away)}</span>
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded font-bold ${
                          mode === 'results' && m.weinston_hit_1x2 !== undefined
                            ? m.weinston_hit_1x2
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-red-500/20 text-red-400'
                            : 'bg-orange-500/20 text-orange-400'
                        }`}
                      >
                        {resultLabel(m.weinston_result)}
                      </span>
                      <span className="text-slate-500">
                        Pred: <span className="text-white font-mono">{predictedScore}</span>
                      </span>
                      <span className="text-slate-500">
                        Prom: <span className="text-slate-300">{avgGoals}</span>
                      </span>
                    </div>
                  ) : (
                    <span className="text-slate-500 text-xs pl-[4.5rem] sm:pl-0">Sin predicción</span>
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
