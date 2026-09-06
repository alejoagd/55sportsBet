import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';

interface TeamStats {
  team_id: number;
  team_name: string;
  home_matches: number;
  away_matches: number;
  total_matches: number;
  home_avg_goals_scored: number;
  away_avg_goals_scored: number;
  home_total_goals_scored: number;
  away_total_goals_scored: number;
  home_avg_goals_conceded: number;
  away_avg_goals_conceded: number;
  home_total_goals_conceded: number;
  away_total_goals_conceded: number;
  home_avg_corners: number;
  away_avg_corners: number;
  home_total_corners: number;
  away_total_corners: number;
  home_avg_shots: number;
  away_avg_shots: number;
  home_total_shots: number;
  away_total_shots: number;
  home_avg_shots_target: number;
  away_avg_shots_target: number;
  home_total_shots_target: number;
  away_total_shots_target: number;
  home_avg_fouls: number;
  away_avg_fouls: number;
  home_total_fouls: number;
  away_total_fouls: number;
  home_avg_cards: number;
  away_avg_cards: number;
  home_total_cards: number;
  away_total_cards: number;
}

interface RefereeStats {
  referee: string;
  matches_officiated: number;
  avg_fouls_per_match: number;
  total_fouls: number;
  avg_cards_per_match: number;
  total_cards: number;
}

interface StatsResponse {
  season_id: number;
  date_from: string | null;
  date_to: string | null;
  teams: TeamStats[];
  referees: RefereeStats[];
}

export default function TeamStatistics({ embedded = false }: { embedded?: boolean } = {}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const leagueParam = searchParams.get('league');
  const [currentLeagueId, setCurrentLeagueId] = useState<number | null>(
    leagueParam ? parseInt(leagueParam, 10) : null
  );

  const [seasonId, setSeasonId] = useState<number | null>(null);
  const [leagueName, setLeagueName] = useState<string>('');
  const [leagueEmoji, setLeagueEmoji] = useState<string>('⚽');

  const [data, setData] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Sin ?league= en la URL: tomar la primera liga activa (igual que ImprovedDashboard)
  useEffect(() => {
    if (currentLeagueId !== null) return;
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/leagues/active`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((leagues: { id: number }[]) => {
        if (leagues.length > 0) {
          setCurrentLeagueId(leagues[0].id);
          setSearchParams(prev => {
            const next = new URLSearchParams(prev);
            next.set('league', String(leagues[0].id));
            return next;
          }, { replace: true });
        }
      })
      .catch(() => setCurrentLeagueId(1));
  }, []);

  // ?league= cambió (via LeagueSidebar/LeagueMobilePanel) → sincronizar
  useEffect(() => {
    const param = searchParams.get('league');
    if (!param) return;
    const leagueFromUrl = parseInt(param, 10);
    if (leagueFromUrl !== currentLeagueId) {
      setCurrentLeagueId(leagueFromUrl);
    }
  }, [searchParams]);

  // Resolver season_id/nombre/emoji reales desde el backend
  useEffect(() => {
    if (currentLeagueId === null) return;
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/leagues/${currentLeagueId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((leagueData: { seasonId: number; name: string; emoji: string }) => {
        setSeasonId(leagueData.seasonId);
        setLeagueName(leagueData.name || '');
        setLeagueEmoji(leagueData.emoji || '⚽');
      })
      .catch((error) => console.error('❌ Error obteniendo season_id:', error));
  }, [currentLeagueId]);

  // Función de fetch con useCallback
  const fetchStatistics = useCallback(async (seasonId: number) => {
    setLoading(true);
    setData(null); // Limpiar datos anteriores IMPORTANTE

    try {
      const today = new Date().toISOString().split('T')[0];

      const params = new URLSearchParams({
        season_id: seasonId.toString(),
        date_from: '2024-08-01',
        date_to: today
      });

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${API_URL}/api/team-statistics?${params}`;
      
      console.log('🔗 URL:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      console.log('✅ Data loaded:');
      console.log('   Teams:', result.teams?.length || 0);
      console.log('   Referees:', result.referees?.length || 0);
      console.log('   Season ID in response:', result.season_id);
      
      // Verificar que el season_id de la respuesta coincide
      if (result.season_id !== seasonId) {
        console.warn('⚠️  MISMATCH: Expected season_id', seasonId, 'but got', result.season_id);
      }
      
      setData(result);
      
    } catch (error) {
      console.error('❌ Error fetching statistics:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch cuando cambia seasonId
  useEffect(() => {
    if (seasonId && seasonId > 0) {
      fetchStatistics(seasonId);
    }
  }, [seasonId, fetchStatistics]);

  // Funciones para obtener rankings
  const getTopTeams = (key: keyof TeamStats, limit: number = 5, ascending: boolean = false) => {
    if (!data || !data.teams) return [];
    return [...data.teams]
      .sort((a, b) => ascending ? (a[key] as number) - (b[key] as number) : (b[key] as number) - (a[key] as number))
      .slice(0, limit);
  };

  const renderRankingTable = (
    title: string,
    teams: TeamStats[],
    valueKey: keyof TeamStats,
    label: string,
    color: string
  ) => (
    <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
      <h3 className={`text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight ${color}`}>{title}</h3>
      {teams.length === 0 ? (
        <div className="text-slate-500 text-center py-4 text-xs sm:text-base">No hay datos</div>
      ) : (
        <div className="space-y-1.5 sm:space-y-2">
          {teams.map((team, idx) => (
            <div
              key={team.team_id}
              className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0"
            >
              <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                <span className="text-white font-medium text-xs sm:text-base truncate">{team.team_name}</span>
              </div>
              <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0">
                <span className={`font-bold text-xs sm:text-base ${color}`}>
                  {typeof team[valueKey] === 'number' ? team[valueKey].toFixed(2) : team[valueKey]}
                </span>
                <span className="text-slate-400 text-[10px] sm:text-sm">{label}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  if (loading) {
    const inner = (
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-slate-400">Cargando estadísticas{leagueName ? ` de ${leagueName}` : ''}...</p>
      </div>
    );
    return embedded
      ? <div className="flex items-center justify-center py-16">{inner}</div>
      : <div className="min-h-screen bg-slate-950 flex items-center justify-center h-96">{inner}</div>;
  }

  if (!data || !data.teams || data.teams.length === 0) {
    const inner = (
      <>
        <div className="text-6xl mb-4">{leagueEmoji}</div>
        <div className="text-slate-400 text-xl">No hay datos disponibles para {leagueName}</div>
        <button
          onClick={() => seasonId && fetchStatistics(seasonId)}
          className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          🔄 Reintentar
        </button>
      </>
    );
    return embedded
      ? <div className="text-center py-16">{inner}</div>
      : <div className="min-h-screen bg-slate-950 p-6 text-center">{inner}</div>;
  }

  const topHomeOffense = getTopTeams('home_avg_goals_scored', 5);
  const bottomHomeOffense = getTopTeams('home_avg_goals_scored', 5, true);
  const topAwayOffense = getTopTeams('away_avg_goals_scored', 5);
  const bottomAwayOffense = getTopTeams('away_avg_goals_scored', 5, true);

  const topHomeDefense = getTopTeams('home_avg_goals_conceded', 5, true);
  const bottomHomeDefense = getTopTeams('home_avg_goals_conceded', 5);
  const topAwayDefense = getTopTeams('away_avg_goals_conceded', 5, true);
  const bottomAwayDefense = getTopTeams('away_avg_goals_conceded', 5);

  const topHomeCorners = getTopTeams('home_avg_corners', 5);
  const bottomHomeCorners = getTopTeams('home_avg_corners', 5, true);
  const topAwayCorners = getTopTeams('away_avg_corners', 5);
  const bottomAwayCorners = getTopTeams('away_avg_corners', 5, true);

  const topHomeShots = getTopTeams('home_avg_shots', 5);
  const bottomHomeShots = getTopTeams('home_avg_shots', 5, true);
  const topAwayShots = getTopTeams('away_avg_shots', 5);
  const bottomAwayShots = getTopTeams('away_avg_shots', 5, true);

  const topHomeShotsTarget = getTopTeams('home_avg_shots_target', 5);
  const bottomHomeShotsTarget = getTopTeams('home_avg_shots_target', 5, true);
  const topAwayShotsTarget = getTopTeams('away_avg_shots_target', 5);
  const bottomAwayShotsTarget = getTopTeams('away_avg_shots_target', 5, true);

  const topHomeFouls = getTopTeams('home_avg_fouls', 5);
  const bottomHomeFouls = getTopTeams('home_avg_fouls', 5, true);
  const topAwayFouls = getTopTeams('away_avg_fouls', 5);
  const bottomAwayFouls = getTopTeams('away_avg_fouls', 5, true);

  const topHomeCards = getTopTeams('home_avg_cards', 5);
  const bottomHomeCards = getTopTeams('home_avg_cards', 5, true);
  const topAwayCards = getTopTeams('away_avg_cards', 5);
  const bottomAwayCards = getTopTeams('away_avg_cards', 5, true);

  const topRefereesFouls = data.referees
    ? [...data.referees].sort((a, b) => b.avg_fouls_per_match - a.avg_fouls_per_match).slice(0, 5)
    : [];

  const topRefereesCards = data.referees
    ? [...data.referees].sort((a, b) => b.avg_cards_per_match - a.avg_cards_per_match).slice(0, 5)
    : [];

  const Wrapper = embedded
    ? ({ children }: { children: ReactNode }) => <div className="space-y-6">{children}</div>
    : ({ children }: { children: ReactNode }) => (
        <div className="min-h-screen bg-slate-950">
          <div className="w-full max-w-[1600px] mx-auto p-6 space-y-6">{children}</div>
        </div>
      );

  return (
    <Wrapper>
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-4xl">{leagueEmoji}</span>
            <h1 className="text-3xl font-bold text-white">
              📊 Análisis Estadístico por Equipos
            </h1>
          </div>
          <p className="text-slate-300">
            Rankings y comparativas de rendimiento - {leagueName} Temporada {seasonId}
          </p>
          <p className="text-slate-500 text-sm mt-1">
            {data.teams.length} equipos • {data.referees?.length || 0} árbitros
          </p>
        </div>

        {/* 1. OFENSIVA */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">⚽ Ofensiva (Goles Anotados)</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Mejor Ofensiva Local', topHomeOffense, 'home_avg_goals_scored', 'goles/partido', 'text-green-400')}
            {renderRankingTable('🏠 Peor Ofensiva Local', bottomHomeOffense, 'home_avg_goals_scored', 'goles/partido', 'text-red-400')}
            {renderRankingTable('✈️ Mejor Ofensiva Visitante', topAwayOffense, 'away_avg_goals_scored', 'goles/partido', 'text-green-400')}
            {renderRankingTable('✈️ Peor Ofensiva Visitante', bottomAwayOffense, 'away_avg_goals_scored', 'goles/partido', 'text-red-400')}
          </div>
        </div>

        {/* 2. DEFENSA */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">🛡️ Defensa (Goles Recibidos)</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Mejor Defensa Local', topHomeDefense, 'home_avg_goals_conceded', 'goles/partido', 'text-green-400')}
            {renderRankingTable('🏠 Peor Defensa Local', bottomHomeDefense, 'home_avg_goals_conceded', 'goles/partido', 'text-red-400')}
            {renderRankingTable('✈️ Mejor Defensa Visitante', topAwayDefense, 'away_avg_goals_conceded', 'goles/partido', 'text-green-400')}
            {renderRankingTable('✈️ Peor Defensa Visitante', bottomAwayDefense, 'away_avg_goals_conceded', 'goles/partido', 'text-red-400')}
          </div>
        </div>

        {/* 3. CORNERS */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">🚩 Corners</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Más Corners Local', topHomeCorners, 'home_avg_corners', 'corners/partido', 'text-yellow-400')}
            {renderRankingTable('🏠 Menos Corners Local', bottomHomeCorners, 'home_avg_corners', 'corners/partido', 'text-slate-400')}
            {renderRankingTable('✈️ Más Corners Visitante', topAwayCorners, 'away_avg_corners', 'corners/partido', 'text-yellow-400')}
            {renderRankingTable('✈️ Menos Corners Visitante', bottomAwayCorners, 'away_avg_corners', 'corners/partido', 'text-slate-400')}
          </div>
        </div>

        {/* 4. TIROS */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">🎯 Tiros</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Más Tiros Local', topHomeShots, 'home_avg_shots', 'tiros/partido', 'text-blue-400')}
            {renderRankingTable('🏠 Menos Tiros Local', bottomHomeShots, 'home_avg_shots', 'tiros/partido', 'text-slate-400')}
            {renderRankingTable('✈️ Más Tiros Visitante', topAwayShots, 'away_avg_shots', 'tiros/partido', 'text-blue-400')}
            {renderRankingTable('✈️ Menos Tiros Visitante', bottomAwayShots, 'away_avg_shots', 'tiros/partido', 'text-slate-400')}
          </div>
        </div>

        {/* 5. TIROS A PUERTA */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">🎯 Tiros a Puerta</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Más Tiros a Puerta Local', topHomeShotsTarget, 'home_avg_shots_target', 'tiros/partido', 'text-purple-400')}
            {renderRankingTable('🏠 Menos Tiros a Puerta Local', bottomHomeShotsTarget, 'home_avg_shots_target', 'tiros/partido', 'text-slate-400')}
            {renderRankingTable('✈️ Más Tiros a Puerta Visitante', topAwayShotsTarget, 'away_avg_shots_target', 'tiros/partido', 'text-purple-400')}
            {renderRankingTable('✈️ Menos Tiros a Puerta Visitante', bottomAwayShotsTarget, 'away_avg_shots_target', 'tiros/partido', 'text-slate-400')}
          </div>
        </div>

        {/* 6. FALTAS */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">⚠️ Faltas</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Más Faltas Local', topHomeFouls, 'home_avg_fouls', 'faltas/partido', 'text-orange-400')}
            {renderRankingTable('🏠 Menos Faltas Local', bottomHomeFouls, 'home_avg_fouls', 'faltas/partido', 'text-slate-400')}
            {renderRankingTable('✈️ Más Faltas Visitante', topAwayFouls, 'away_avg_fouls', 'faltas/partido', 'text-orange-400')}
            {renderRankingTable('✈️ Menos Faltas Visitante', bottomAwayFouls, 'away_avg_fouls', 'faltas/partido', 'text-slate-400')}
          </div>
        </div>

        {/* 7. TARJETAS */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">🟨 Tarjetas</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable('🏠 Más Tarjetas Local', topHomeCards, 'home_avg_cards', 'tarjetas/partido', 'text-yellow-400')}
            {renderRankingTable('🏠 Menos Tarjetas Local', bottomHomeCards, 'home_avg_cards', 'tarjetas/partido', 'text-slate-400')}
            {renderRankingTable('✈️ Más Tarjetas Visitante', topAwayCards, 'away_avg_cards', 'tarjetas/partido', 'text-yellow-400')}
            {renderRankingTable('✈️ Menos Tarjetas Visitante', bottomAwayCards, 'away_avg_cards', 'tarjetas/partido', 'text-slate-400')}
          </div>
        </div>

        {/* 8. ÁRBITROS */}
        {data.referees && data.referees.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-white">👨‍⚖️ Árbitros</h2>
            <div className="grid grid-cols-2 gap-2 sm:gap-4">

              {/* Árbitros con más faltas */}
              <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
                <h3 className="text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight text-orange-400">⚠️ Más Faltas por Partido</h3>
                <div className="space-y-1.5 sm:space-y-2">
                  {topRefereesFouls.map((ref, idx) => (
                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0">
                      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                        <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                        <span className="text-white font-medium text-xs sm:text-base truncate">{ref.referee}</span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0">
                        <span className="font-bold text-xs sm:text-base text-orange-400">{ref.avg_fouls_per_match.toFixed(2)}</span>
                        <span className="text-slate-400 text-[10px] sm:text-sm">faltas/partido</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Árbitros con más tarjetas */}
              <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
                <h3 className="text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight text-yellow-400">🟨 Más Tarjetas por Partido</h3>
                <div className="space-y-1.5 sm:space-y-2">
                  {topRefereesCards.map((ref, idx) => (
                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0">
                      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                        <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                        <span className="text-white font-medium text-xs sm:text-base truncate">{ref.referee}</span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0">
                        <span className="font-bold text-xs sm:text-base text-yellow-400">{ref.avg_cards_per_match.toFixed(2)}</span>
                        <span className="text-slate-400 text-[10px] sm:text-sm">tarjetas/partido</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
    </Wrapper>
  );
}