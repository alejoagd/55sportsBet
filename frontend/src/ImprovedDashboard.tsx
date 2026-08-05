import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAdminMode } from './Hooks/useAdminMode';
import WorldCupDashboard from './WorldCupDashboard';
import CompetitionDashboard from './CompetitionDashboard';
import TodayAllLeaguesView from './TodayAllLeaguesView';
import CompactMatchList from './CompactMatchList';
import LeagueTabNav, { useLeagueTab } from './LeagueTabNav';
import LeagueStandingsTable from './LeagueStandingsTable';
import LeagueNewsView from './LeagueNewsView';
import TeamStatistics from './Teamstatistics';

function isMatchToday(m: { date: string; kickoff_at?: string | null }): boolean {
  const iso = m.kickoff_at || m.date;
  const d = new Date(iso);
  return !isNaN(d.getTime()) && d.toDateString() === new Date().toDateString();
}



interface Match {
  match_id: number;
  date: string;
  kickoff_at?: string | null;
  home_team: string;
  home_team_logo?: string | null;
  away_team: string;
  away_team_logo?: string | null;
  referee: string | null;

  // Resultados reales (solo para partidos jugados)
  actual_home_goals?: number;
  actual_away_goals?: number;
  actual_result?: 'H' | 'D' | 'A';
  
  // Predicciones Poisson
  poisson_home_goals: number;
  poisson_away_goals: number;
  poisson_prob_home: number;
  poisson_prob_draw: number;
  poisson_prob_away: number;
  poisson_over_25: number;
  poisson_btts: number;
  
  // Predicciones Weinston
  weinston_home_goals: number;
  weinston_away_goals: number;
  weinston_prob_home: number;
  weinston_prob_draw: number;
  weinston_prob_away: number;
  weinston_result: string;
  weinston_over_25: number;
  weinston_btts: number;

  weinston_prob_over_25?: number;
  weinston_prob_btts?: number;
  
  // Aciertos
  poisson_hit_1x2?: boolean;
  poisson_hit_over25?: boolean;
  poisson_hit_btts?: boolean;
  weinston_hit_1x2?: boolean;
  weinston_hit_over25?: boolean;
  weinston_hit_btts?: boolean;
}

export default function ImprovedDashboard() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([]);
  const [recentMatches, setRecentMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const leagueParam = searchParams.get('league');
  const [currentLeagueId, setCurrentLeagueId] = useState<number | null>(
    leagueParam ? parseInt(leagueParam, 10) : null
  );

  const [seasonId, setSeasonId] = useState<number | null>(null);
  const [upcomingLimit, setUpcomingLimit] = useState<number>(10);
  const [leagueName, setLeagueName] = useState<string>('');
  const { isAdmin } = useAdminMode();
  const [activeTab, setActiveTab] = useLeagueTab('matches');

  // Sin ?league= en la URL: no se auto-selecciona ninguna liga (antes caía
  // siempre en la primera, que era el Mundial). Se muestra en su lugar
  // <TodayAllLeaguesView /> — ver el return más abajo.

  useEffect(() => {
    const param = searchParams.get('league');
    if (!param) {
      if (currentLeagueId !== null) {
        setCurrentLeagueId(null);
      }
      return;
    }
    const leagueFromUrl = parseInt(param, 10);
    if (leagueFromUrl !== currentLeagueId) {
      setCurrentLeagueId(leagueFromUrl);
    }
  }, [searchParams]);

  // Actualizar season_id cuando cambia la liga
  useEffect(() => {
    if (currentLeagueId === null) return;
    const updateSeasonForLeague = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${API_URL}/api/leagues/${currentLeagueId}`);

        if (response.ok) {
          const leagueData = await response.json();
          setSeasonId(leagueData.seasonId);
          setLeagueName(leagueData.name || '');
          setUpcomingLimit(20);
        } else {
          // League id not found — fall back to first active league
          const activeResp = await fetch(`${API_URL}/api/leagues/active`);
          if (activeResp.ok) {
            const leagues: { id: number }[] = await activeResp.json();
            if (leagues.length > 0) {
              setCurrentLeagueId(leagues[0].id);
              setSearchParams({ league: String(leagues[0].id) }, { replace: true });
            }
          }
        }
      } catch (error) {
        console.error('❌ Error obteniendo season_id:', error);
      }
    };

    updateSeasonForLeague();
  }, [currentLeagueId]);

  useEffect(() => {
    if (seasonId && seasonId > 0) {
      console.log('📊 Fetching data for season_id:', seasonId);
      fetchData();
    }
  }, [seasonId, upcomingLimit]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      console.log('🚀 Fetching upcoming matches with season_id:', seasonId);
      const upcomingResponse = await fetch(
        `${API_URL}/api/matches/upcoming?season_id=${seasonId}&limit=${upcomingLimit}`
      );
      
      if (!upcomingResponse.ok) {
        throw new Error(`Error ${upcomingResponse.status}`);
      }
      
      const upcomingData = await upcomingResponse.json();
      console.log('✅ Upcoming matches loaded:', upcomingData.length);
      setUpcomingMatches(upcomingData);

      console.log('🚀 Fetching recent results with season_id:', seasonId);
      const recentResponse = await fetch(
        `${API_URL}/api/matches/recent-results?season_id=${seasonId}&num_matches=20`
      );
      
      if (!recentResponse.ok) {
        throw new Error(`Error ${recentResponse.status}`);
      }
      
      const recentData = await recentResponse.json();
      console.log('Recent matches:', recentData);
      setRecentMatches(recentData);
    } catch (error) {
      console.error('Error fetching data:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };



  // Sin liga seleccionada (no hay ?league= en la URL): vista por defecto
  // con los partidos de hoy en todas las ligas.
  if (currentLeagueId === null) {
    return <TodayAllLeaguesView />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-slate-400 text-xl">⏳ Cargando predicciones...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-900 p-6">
        <div className="text-red-400 text-xl mb-4">❌ Error al cargar datos</div>
        <div className="text-slate-400 text-sm mb-4">{error}</div>
        <button 
          onClick={fetchData}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

// ═══════════════════════════════════════════════════════════════════
// CORRECCIÓN DEL return EN ImprovedDashboard.tsx
// Reemplaza desde la línea 446 hasta el final (línea 532)
// ═══════════════════════════════════════════════════════════════════

  const isWorldCup = leagueName === 'FIFA World Cup';
  const isCupCompetition = leagueName === 'Copa Libertadores' || leagueName === 'Copa Sudamericana';

  const matchClickHandler = (matchId: number) =>
    navigate(`/match/${matchId}`, { state: { returnPath: `/?${searchParams.toString()}` } });

  const todayUpcoming = upcomingMatches.filter(isMatchToday);
  const todayRecent = recentMatches.filter(isMatchToday);

  return (
    <>
      {/* VISTA ESPECIAL MUNDIAL — sin cambios, tiene su propio menú de pestañas */}
      {isWorldCup && (
        <WorldCupDashboard initialGroup={searchParams.get('group')} />
      )}

      {/* MENÚ DE PESTAÑAS (todas las ligas menos el Mundial) */}
      {!isWorldCup && currentLeagueId && (
        <div className="min-h-screen bg-slate-900 p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <LeagueTabNav
              active={activeTab}
              onChange={setActiveTab}
              leagueId={currentLeagueId}
              showBracket={isCupCompetition}
            />

            {isAdmin && activeTab === 'matches' && (
              <div className="flex justify-end -mt-2">
                <button
                  onClick={async () => {
                    if (confirm('¿Recalcular todos los aciertos?')) {
                      try {
                        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                        const response = await fetch(
                          `${API_URL}/api/recalculate-outcomes?season_id=${seasonId}`,
                          { method: 'POST' }
                        );
                        const data = await response.json();
                        alert(`✅ Recalculados ${data.inserted_count} registros`);
                        fetchData();
                      } catch (error) {
                        alert('❌ Error al recalcular');
                      }
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
                >
                  🔄 Recalcular Aciertos
                </button>
              </div>
            )}

            {activeTab === 'today' && (
              <div className="space-y-8">
                {todayUpcoming.length > 0 && (
                  <section>
                    <h2 className="text-xl font-bold text-white mb-4">🔮 Próximos de hoy</h2>
                    <CompactMatchList matches={todayUpcoming} mode="upcoming" onMatchClick={matchClickHandler} />
                  </section>
                )}
                {todayRecent.length > 0 && (
                  <section>
                    <h2 className="text-xl font-bold text-white mb-4">📋 Jugados hoy</h2>
                    <CompactMatchList matches={todayRecent} mode="results" onMatchClick={matchClickHandler} />
                  </section>
                )}
                {todayUpcoming.length === 0 && todayRecent.length === 0 && (
                  <div className="text-center py-12 text-slate-400">No hay partidos de esta liga hoy</div>
                )}
              </div>
            )}

            {activeTab === 'matches' && (
              <div className="space-y-8">
                {upcomingMatches.length > 0 && (
                  <section>
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-2xl font-bold text-white">🔮 Próximos Partidos</h2>
                      <span className="text-slate-400 text-sm bg-slate-800 px-3 py-1 rounded-full">
                        {upcomingMatches.length} partidos
                      </span>
                    </div>
                    <CompactMatchList matches={upcomingMatches} mode="upcoming" onMatchClick={matchClickHandler} />
                  </section>
                )}
                {recentMatches.length > 0 && (
                  <section>
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-2xl font-bold text-white">📋 Resultados Recientes</h2>
                      <span className="text-slate-400 text-sm bg-slate-800 px-3 py-1 rounded-full">
                        {recentMatches.length} partidos
                      </span>
                    </div>
                    <CompactMatchList matches={recentMatches} mode="results" onMatchClick={matchClickHandler} />
                  </section>
                )}
                {upcomingMatches.length === 0 && recentMatches.length === 0 && (
                  <div className="text-center py-12">
                    <div className="text-slate-400 text-lg">No hay partidos disponibles</div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'standings' && seasonId && (
              isCupCompetition
                ? <CompetitionDashboard seasonId={seasonId} section="groups" />
                : <LeagueStandingsTable seasonId={seasonId} />
            )}

            {activeTab === 'bracket' && isCupCompetition && seasonId && (
              <CompetitionDashboard seasonId={seasonId} section="bracket" />
            )}

            {activeTab === 'news' && (
              <LeagueNewsView leagueId={currentLeagueId} leagueName={leagueName} />
            )}

            {activeTab === 'stats' && <TeamStatistics embedded />}
          </div>
        </div>
      )}
    </>
  );
}