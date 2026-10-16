import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18n, { localeTag } from './i18n';
import ProbabilityBar from './ProbabilityBar';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Vista por defecto del Dashboard: partidos de HOY en todas las ligas,
// en vez de auto-seleccionar una liga (antes siempre caía en el Mundial).
// Liviana a propósito — es un marcador cruzado de ligas, no la vista de
// predicciones de una liga (esa sigue siendo ImprovedDashboard normal,
// accesible eligiendo una liga en el sidebar/panel de ligas).

interface TodayMatch {
  match_id: number;
  date: string;
  kickoff_at: string | null;
  league_id: number;
  league_name: string;
  league_emoji: string;
  home_team: string;
  home_team_logo: string | null;
  away_team: string;
  away_team_logo: string | null;
  home_goals: number | null;
  away_goals: number | null;
  // Predicción Weinston (null si el partido aún no tiene)
  weinston_home_goals: number | null;
  weinston_away_goals: number | null;
  weinston_prob_home: number | null;
  weinston_prob_draw: number | null;
  weinston_prob_away: number | null;
  weinston_result: 'H' | 'D' | 'A' | null;
}

function formatTime(kickoffAt: string | null): string {
  if (!kickoffAt) return i18n.t('common.timeTbd');
  try {
    return new Date(kickoffAt).toLocaleTimeString(localeTag(), { hour: '2-digit', minute: '2-digit' });
  } catch {
    return i18n.t('common.timeTbd');
  }
}

function isToday(m: { date: string; kickoff_at: string | null }): boolean {
  // Igual que en CompactMatchList/ImprovedDashboard: si no hay kickoff_at,
  // m.date es "YYYY-MM-DD" sin hora y hay que armarlo con componentes
  // locales — parsearlo directo con new Date() lo corre un día hacia atrás
  // en zonas detrás de UTC. Antes esta función simplemente descartaba
  // cualquier partido sin kickoff_at ("Hora por confirmar"), sacándolo de
  // "Hoy" aunque su fecha SÍ fuera hoy.
  let d: Date;
  if (m.kickoff_at) {
    d = new Date(m.kickoff_at);
  } else {
    const [year, month, day] = m.date.split('T')[0].split('-').map(Number);
    if (!year || !month || !day) return false;
    d = new Date(year, month - 1, day);
  }
  return !isNaN(d.getTime()) && d.toDateString() === new Date().toDateString();
}

function TeamLogo({ url, alt }: { url: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return (
      <span className="w-6 h-6 rounded-full bg-slate-700/60 flex items-center justify-center shrink-0 text-xs">⚽</span>
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      className="w-6 h-6 object-contain shrink-0"
      onError={() => setFailed(true)}
    />
  );
}

// Mismo código de colores que las tarjetas de la liga: 1 local, X empate, 2 visitante.
const OUTCOME_STYLE: Record<string, string> = {
  '1': 'bg-blue-500/20 text-blue-400',
  'X': 'bg-slate-500/20 text-slate-300',
  '2': 'bg-orange-500/20 text-orange-400',
};

// Predicción compacta del partido, a la derecha de los equipos: arriba el
// pronóstico (1/X/2) y el marcador esperado (+ goles promedio desde sm), abajo
// una mini barra 1X2. Ancho fijo: no se estira en pantallas grandes ni se
// aprieta en móvil. Si el partido ya terminó, el pronóstico se pinta
// verde/rojo según acertó.
function PredictionStrip({ m, finished }: { m: TodayMatch; finished: boolean }) {
  const { t } = useTranslation();
  if (m.weinston_home_goals == null || m.weinston_away_goals == null || m.weinston_prob_home == null) {
    return <div className="text-right text-[11px] leading-tight text-slate-500">{t('matchList.noPrediction')}</div>;
  }
  const probs = { H: m.weinston_prob_home, D: m.weinston_prob_draw ?? 0, A: m.weinston_prob_away ?? 0 };
  const predicted = m.weinston_result ?? (Object.keys(probs) as ('H' | 'D' | 'A')[]).sort((a, b) => probs[b] - probs[a])[0];
  const label = predicted === 'H' ? '1' : predicted === 'A' ? '2' : 'X';
  const actual = finished ? (m.home_goals! > m.away_goals! ? 'H' : m.home_goals! < m.away_goals! ? 'A' : 'D') : null;
  const badgeStyle = finished
    ? (actual === predicted ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')
    : OUTCOME_STYLE[label];

  return (
    <div className="flex flex-col gap-1.5" title={t('matchList.prediction')}>
      <div className="flex items-center justify-end gap-1.5">
        {finished && (
          <span className="mr-auto text-[9px] font-semibold uppercase tracking-wide text-slate-500">{t('matchList.pred')}</span>
        )}
        <span className={`inline-flex min-w-[1.25rem] items-center justify-center rounded px-1 py-0.5 text-[11px] font-bold ${badgeStyle}`}>
          {label}
        </span>
        <span className="rounded bg-slate-900/60 px-1.5 py-0.5 font-mono text-xs font-bold text-white">
          {Math.round(m.weinston_home_goals)} - {Math.round(m.weinston_away_goals)}
        </span>
        <span className="hidden text-[11px] font-medium text-slate-300 sm:inline" title={t('matchList.avgGoals')}>
          ⚽ {(m.weinston_home_goals + m.weinston_away_goals).toFixed(1)}
        </span>
      </div>
      <ProbabilityBar home={m.weinston_prob_home} draw={m.weinston_prob_draw} away={m.weinston_prob_away} />
    </div>
  );
}

// Una fila por equipo (escudo + nombre + goles), como en Sofascore/Flashscore:
// el nombre ocupa todo el ancho disponible y se recorta con "…" en vez de
// partirse letra por letra, sin importar qué tan angosta quede la tarjeta
// (tablet con el menú de ligas abierto, por ejemplo).
function TeamLine({ name, logo, goals, winner }: { name: string; logo: string | null; goals: number | null; winner: boolean }) {
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <TeamLogo url={logo} alt={name} />
      <span
        className={`flex-1 min-w-0 truncate text-sm ${winner ? 'font-bold text-white' : 'font-medium text-slate-200'}`}
        title={name}
      >
        {name}
      </span>
      {goals !== null && (
        <span className={`w-5 text-right text-base tabular-nums ${winner ? 'font-bold text-white' : 'font-semibold text-slate-300'}`}>
          {goals}
        </span>
      )}
    </div>
  );
}

export default function TodayAllLeaguesView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [matches, setMatches] = useState<TodayMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/matches/today`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: TodayMatch[]) => setMatches(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  // Orden cronológico dentro de cada liga
  const todayMatches = matches.filter(m => isToday(m)).sort((a, b) => (a.kickoff_at ?? '').localeCompare(b.kickoff_at ?? ''));

  const byLeague = todayMatches.reduce<Record<string, TodayMatch[]>>((acc, m) => {
    (acc[m.league_name] ||= []).push(m);
    return acc;
  }, {});

  const today = new Date().toLocaleDateString(localeTag(), { weekday: 'long', day: '2-digit', month: 'long' });

  return (
    <div className="min-h-screen bg-slate-900 p-4 sm:p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-800 via-slate-800 to-slate-700/80 rounded-xl p-5 sm:p-6 shadow-xl border border-slate-700">
          <div className="absolute -right-6 -top-6 h-28 w-28 rounded-full bg-yellow-400/10 blur-2xl" />
          <h1 className="relative text-xl sm:text-2xl font-bold text-white mb-1">📅 {t('today.title')}</h1>
          <p className="relative text-slate-300 text-sm capitalize">{today}</p>
        </div>

        {loading && (
          <div className="text-center py-16 text-slate-400">{t('today.loading')}</div>
        )}

        {!loading && error && (
          <div className="text-center py-16 text-red-400">{t('today.error')}</div>
        )}

        {!loading && !error && todayMatches.length === 0 && (
          <div className="text-center py-16 text-slate-500">{t('today.empty')}</div>
        )}

        {!loading && !error && Object.entries(byLeague).map(([leagueName, leagueMatches]) => (
          // Una tarjeta por liga con una fila por partido (patrón Flashscore/
          // Sofascore): usa todo el ancho disponible, con el menú de ligas
          // abierto o colapsado, y deja a los nombres todo el espacio posible.
          <section key={leagueName} className="overflow-hidden rounded-xl border border-slate-700/70 bg-slate-800/60 shadow-lg shadow-black/10">
            <div className="flex items-center gap-2.5 border-b border-slate-700/70 bg-slate-800 px-4 py-2.5">
              <span className="text-xl leading-none">{leagueMatches[0].league_emoji}</span>
              {/* El nombre de la liga lleva a la liga (pestaña Partidos) */}
              <Link
                to={`/?league=${leagueMatches[0].league_id}`}
                className="group/league flex min-w-0 items-center gap-1.5 text-sm sm:text-base font-bold text-white transition-colors hover:text-yellow-400"
                title={leagueName}
              >
                <h2 className="truncate">{leagueName}</h2>
                <span className="text-slate-500 transition-colors group-hover/league:text-yellow-400" aria-hidden>›</span>
              </Link>
              <span className="ml-auto rounded-full bg-slate-900/60 px-2.5 py-0.5 text-xs font-medium text-slate-400">
                {t('common.matchesCount', { count: leagueMatches.length })}
              </span>
            </div>
            <div className="divide-y divide-slate-700/50">
              {leagueMatches.map((m) => {
                const finished = m.home_goals !== null && m.away_goals !== null;
                return (
                  <div
                    key={m.match_id}
                    onClick={() => navigate(`/match/${m.match_id}`, { state: { returnPath: '/' } })}
                    className="group cursor-pointer px-3 sm:px-4 py-3 transition-colors hover:bg-slate-700/40 active:bg-slate-700/60"
                  >
                    <div className="flex items-center gap-2.5 sm:gap-3">
                      <div className="hidden w-20 shrink-0 flex-col items-center justify-center gap-1 text-center sm:flex">
                        <span className="whitespace-nowrap text-[13px] font-semibold leading-tight text-slate-300 tabular-nums">
                          {formatTime(m.kickoff_at)}
                        </span>
                        {finished && (
                          <span className="rounded-full bg-green-500/20 px-1.5 py-0.5 text-[10px] font-bold text-green-400">
                            {t('matchList.fullTime')}
                          </span>
                        )}
                      </div>
                      <div className="flex min-w-0 flex-1 flex-col justify-center gap-2 sm:border-l sm:border-slate-700/60 sm:pl-3">
                        {/* Móvil: la hora va aquí (en vez de una columna lateral) para dar el
                            ancho a los nombres de los equipos. */}
                        <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400 tabular-nums sm:hidden">
                          <span>{formatTime(m.kickoff_at)}</span>
                          {finished && (
                            <span className="rounded-full bg-green-500/20 px-1.5 text-[10px] font-bold text-green-400">{t('matchList.fullTime')}</span>
                          )}
                        </div>
                        <TeamLine
                          name={m.home_team} logo={m.home_team_logo} goals={m.home_goals}
                          winner={finished && m.home_goals! > m.away_goals!}
                        />
                        <TeamLine
                          name={m.away_team} logo={m.away_team_logo} goals={m.away_goals}
                          winner={finished && m.away_goals! > m.home_goals!}
                        />
                      </div>
                      <div className="w-[6rem] shrink-0 border-l border-slate-700/60 pl-2 sm:w-[9.5rem] sm:pl-3">
                        <PredictionStrip m={m} finished={finished} />
                      </div>
                      <span className="shrink-0 text-slate-600 transition-colors group-hover:text-yellow-400">›</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
