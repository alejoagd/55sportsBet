import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

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
}

function formatTime(kickoffAt: string | null): string {
  if (!kickoffAt) return 'Hora por confirmar';
  try {
    return new Date(kickoffAt).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Hora por confirmar';
  }
}

function isToday(kickoffAt: string | null): boolean {
  if (!kickoffAt) return false;
  const d = new Date(kickoffAt);
  return d.toDateString() === new Date().toDateString();
}

function TeamLogo({ url, alt }: { url: string | null; alt: string }) {
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

export default function TodayAllLeaguesView() {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<TodayMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/matches/today`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: TodayMatch[]) => setMatches(data))
      .catch(() => setError('No se pudieron cargar los partidos de hoy'))
      .finally(() => setLoading(false));
  }, []);

  const todayMatches = matches.filter(m => isToday(m.kickoff_at));

  const byLeague = todayMatches.reduce<Record<string, TodayMatch[]>>((acc, m) => {
    (acc[m.league_name] ||= []).push(m);
    return acc;
  }, {});

  const today = new Date().toLocaleDateString('es-CO', { weekday: 'long', day: '2-digit', month: 'long' });

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-lg p-6 shadow-xl border border-slate-600">
          <h1 className="text-2xl font-bold text-white mb-1">📅 Partidos de hoy</h1>
          <p className="text-slate-300 capitalize">{today}</p>
        </div>

        {loading && (
          <div className="text-center py-16 text-slate-400">Cargando partidos de hoy...</div>
        )}

        {!loading && error && (
          <div className="text-center py-16 text-red-400">{error}</div>
        )}

        {!loading && !error && todayMatches.length === 0 && (
          <div className="text-center py-16 text-slate-500">No hay partidos programados para hoy en ninguna liga</div>
        )}

        {!loading && !error && Object.entries(byLeague).map(([leagueName, leagueMatches]) => (
          <section key={leagueName} className="space-y-3">
            <h2 className="flex items-center gap-2 text-lg font-bold text-white">
              <span>{leagueMatches[0].league_emoji}</span>
              {leagueName}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {leagueMatches.map((m) => (
                <div
                  key={m.match_id}
                  onClick={() => navigate(`/match/${m.match_id}`)}
                  className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:bg-slate-700/50 transition-colors cursor-pointer"
                >
                  <div className="text-slate-400 text-xs mb-2">{formatTime(m.kickoff_at)}</div>
                  <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
                    <div className="flex items-center justify-end gap-2 text-right text-white font-semibold text-sm min-w-0">
                      <span className="truncate">{m.home_team}</span>
                      <TeamLogo url={m.home_team_logo} alt={m.home_team} />
                    </div>
                    <div className="text-center min-w-[48px]">
                      {m.home_goals !== null && m.away_goals !== null ? (
                        <span className="text-lg font-bold text-white">{m.home_goals} - {m.away_goals}</span>
                      ) : (
                        <span className="text-slate-500 text-sm">vs</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-left text-white font-semibold text-sm min-w-0">
                      <TeamLogo url={m.away_team_logo} alt={m.away_team} />
                      <span className="truncate">{m.away_team}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
