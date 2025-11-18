import { useState, useEffect } from 'react';

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

interface Filters {
  season_id: number;
  date_from: string;
  date_to: string;
}

export default function TeamStatistics() {
  const [data, setData] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
const [filters] = useState<Filters>({
    season_id: 2,
    date_from: '2025-08-15',
    date_to: new Date().toISOString().split('T')[0]  // Fecha actual automática
});

  useEffect(() => {
    fetchStatistics();
  }, [filters]);

  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        season_id: filters.season_id.toString(),
        ...(filters.date_from && { date_from: filters.date_from }),
        ...(filters.date_to && { date_to: filters.date_to })
      });

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/team-statistics?${params}`);
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96 text-gray-400">Cargando estadísticas...</div>;
  }

  if (!data) {
    return <div className="text-gray-400">No hay datos disponibles</div>;
  }

  // Funciones para obtener rankings
  const getTopTeams = (key: keyof TeamStats, limit: number = 5, ascending: boolean = false) => {
    return [...data.teams]
      .sort((a, b) => ascending ? (a[key] as number) - (b[key] as number) : (b[key] as number) - (a[key] as number))
      .slice(0, limit);
  };

  const renderRankingTable = (
    title: string,
    teams: TeamStats[],
    valueKey: keyof TeamStats,
    label: string,
    _isHome: boolean, // eslint-disable-line @typescript-eslint/no-unused-vars
    color: string
  ) => (
    
    <div className="bg-slate-800 rounded-lg p-4" >
      <h3 className={`text-lg font-bold mb-3 ${color}`}>{title}</h3>
      <div className="space-y-2">
        {teams.map((team, idx) => (
          <div key={team.team_id} className="flex items-center justify-between bg-slate-700/50 rounded px-3 py-2">
            <div className="flex items-center gap-3">
              <span className="text-slate-400 font-bold w-6">{idx + 1}</span>
              <span className="text-white font-medium">{team.team_name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`font-bold ${color}`}>
                {typeof team[valueKey] === 'number' ? team[valueKey].toFixed(2) : team[valueKey]}
              </span>
              <span className="text-slate-400 text-sm">{label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const topHomeOffense = getTopTeams('home_avg_goals_scored', 5);
  const bottomHomeOffense = getTopTeams('home_avg_goals_scored', 5, true);
  const topAwayOffense = getTopTeams('away_avg_goals_scored', 5);
  const bottomAwayOffense = getTopTeams('away_avg_goals_scored', 5, true);

  const topHomeDefense = getTopTeams('home_avg_goals_conceded', 5, true); // Menos goles recibidos = mejor defensa
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

  const topRefereesFouls = [...data.referees]
    .sort((a, b) => b.avg_fouls_per_match - a.avg_fouls_per_match)
    .slice(0, 5);

  const topRefereesCards = [...data.referees]
    .sort((a, b) => b.avg_cards_per_match - a.avg_cards_per_match)
    .slice(0, 5);

  return (
    <div className="w-full max-w-[1600px] mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-6 shadow-xl">
        <h1 className="text-3xl font-bold text-white mb-2">
          📊 Análisis Estadístico por Equipos
        </h1>
        <p className="text-slate-300">
          Rankings y comparativas de rendimiento por equipo - Temporada {filters.season_id}
        </p>
      </div>

      {/* 1. OFENSIVA */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">⚽ Ofensiva (Goles Anotados)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Mejor Ofensiva Local', topHomeOffense, 'home_avg_goals_scored', 'goles/partido', true, 'text-green-400')}
          {renderRankingTable('🏠 Peor Ofensiva Local', bottomHomeOffense, 'home_avg_goals_scored', 'goles/partido', true, 'text-red-400')}
          {renderRankingTable('✈️ Mejor Ofensiva Visitante', topAwayOffense, 'away_avg_goals_scored', 'goles/partido', false, 'text-green-400')}
          {renderRankingTable('✈️ Peor Ofensiva Visitante', bottomAwayOffense, 'away_avg_goals_scored', 'goles/partido', false, 'text-red-400')}
        </div>
      </div>

      {/* 2. DEFENSIVA */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">🛡️ Defensiva (Goles Recibidos)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Mejor Defensa Local', topHomeDefense, 'home_avg_goals_conceded', 'goles/partido', true, 'text-green-400')}
          {renderRankingTable('🏠 Peor Defensa Local', bottomHomeDefense, 'home_avg_goals_conceded', 'goles/partido', true, 'text-red-400')}
          {renderRankingTable('✈️ Mejor Defensa Visitante', topAwayDefense, 'away_avg_goals_conceded', 'goles/partido', false, 'text-green-400')}
          {renderRankingTable('✈️ Peor Defensa Visitante', bottomAwayDefense, 'away_avg_goals_conceded', 'goles/partido', false, 'text-red-400')}
        </div>
      </div>

      {/* 3. CORNERS */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">🚩 Corners</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Más Corners Local', topHomeCorners, 'home_avg_corners', 'corners/partido', true, 'text-blue-400')}
          {renderRankingTable('🏠 Menos Corners Local', bottomHomeCorners, 'home_avg_corners', 'corners/partido', true, 'text-orange-400')}
          {renderRankingTable('✈️ Más Corners Visitante', topAwayCorners, 'away_avg_corners', 'corners/partido', false, 'text-blue-400')}
          {renderRankingTable('✈️ Menos Corners Visitante', bottomAwayCorners, 'away_avg_corners', 'corners/partido', false, 'text-orange-400')}
        </div>
      </div>

      {/* 4. TIROS */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">🎯 Tiros</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Más Tiros Local', topHomeShots, 'home_avg_shots', 'tiros/partido', true, 'text-purple-400')}
          {renderRankingTable('🏠 Menos Tiros Local', bottomHomeShots, 'home_avg_shots', 'tiros/partido', true, 'text-gray-400')}
          {renderRankingTable('✈️ Más Tiros Visitante', topAwayShots, 'away_avg_shots', 'tiros/partido', false, 'text-purple-400')}
          {renderRankingTable('✈️ Menos Tiros Visitante', bottomAwayShots, 'away_avg_shots', 'tiros/partido', false, 'text-gray-400')}
        </div>
      </div>

      {/* 5. TIROS AL ARCO */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">🥅 Tiros al Arco</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Más Tiros al Arco Local', topHomeShotsTarget, 'home_avg_shots_target', 'tiros/partido', true, 'text-cyan-400')}
          {renderRankingTable('🏠 Menos Tiros al Arco Local', bottomHomeShotsTarget, 'home_avg_shots_target', 'tiros/partido', true, 'text-slate-400')}
          {renderRankingTable('✈️ Más Tiros al Arco Visitante', topAwayShotsTarget, 'away_avg_shots_target', 'tiros/partido', false, 'text-cyan-400')}
          {renderRankingTable('✈️ Menos Tiros al Arco Visitante', bottomAwayShotsTarget, 'away_avg_shots_target', 'tiros/partido', false, 'text-slate-400')}
        </div>
      </div>

      {/* 6. FALTAS */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">⚠️ Faltas</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Más Faltas Local', topHomeFouls, 'home_avg_fouls', 'faltas/partido', true, 'text-yellow-400')}
          {renderRankingTable('🏠 Menos Faltas Local', bottomHomeFouls, 'home_avg_fouls', 'faltas/partido', true, 'text-green-400')}
          {renderRankingTable('✈️ Más Faltas Visitante', topAwayFouls, 'away_avg_fouls', 'faltas/partido', false, 'text-yellow-400')}
          {renderRankingTable('✈️ Menos Faltas Visitante', bottomAwayFouls, 'away_avg_fouls', 'faltas/partido', false, 'text-green-400')}
        </div>
      </div>

      {/* 7. TARJETAS */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">🟨🟥 Tarjetas</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderRankingTable('🏠 Más Tarjetas Local', topHomeCards, 'home_avg_cards', 'tarjetas/partido', true, 'text-red-400')}
          {renderRankingTable('🏠 Menos Tarjetas Local', bottomHomeCards, 'home_avg_cards', 'tarjetas/partido', true, 'text-green-400')}
          {renderRankingTable('✈️ Más Tarjetas Visitante', topAwayCards, 'away_avg_cards', 'tarjetas/partido', false, 'text-red-400')}
          {renderRankingTable('✈️ Menos Tarjetas Visitante', bottomAwayCards, 'away_avg_cards', 'tarjetas/partido', false, 'text-green-400')}
        </div>
      </div>

      {/* 8 y 9. ÁRBITROS */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">👨‍⚖️ Árbitros</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Top 5 Árbitros con más faltas */}
          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3 text-yellow-400">⚠️ Top 5 Árbitros - Más Faltas</h3>
            <div className="space-y-2">
              {topRefereesFouls.map((ref, idx) => (
                <div key={ref.referee} className="flex items-center justify-between bg-slate-700/50 rounded px-3 py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-bold w-6">{idx + 1}</span>
                    <span className="text-white font-medium">{ref.referee}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-yellow-400">{ref.avg_fouls_per_match.toFixed(2)}</span>
                    <span className="text-slate-400 text-sm">faltas/partido</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top 5 Árbitros con más tarjetas */}
          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3 text-red-400">🟨🟥 Top 5 Árbitros - Más Tarjetas</h3>
            <div className="space-y-2">
              {topRefereesCards.map((ref, idx) => (
                <div key={ref.referee} className="flex items-center justify-between bg-slate-700/50 rounded px-3 py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-bold w-6">{idx + 1}</span>
                    <span className="text-white font-medium">{ref.referee}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-red-400">{ref.avg_cards_per_match.toFixed(2)}</span>
                    <span className="text-slate-400 text-sm">tarjetas/partido</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}