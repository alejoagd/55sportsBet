import { useState, useEffect } from 'react';

interface BetTypeStats {
  hit: number;
  miss: number;
  total: number;
  accuracy: number;
}

interface LeagueStats {
  league_name: string;
  league_code: string;
  league_emoji: string;
  total_matches: number;
  overall_accuracy: number;
  stats: {
    TIROS: BetTypeStats;
    'TIROS AL ARCO': BetTypeStats;
    CORNERS: BetTypeStats;
    TARJETAS: BetTypeStats;
    FALTAS: BetTypeStats;
  };
}

interface BettingLinesStatsResponse {
  stats_by_league: LeagueStats[];
  total_leagues: number;
  date_from: string | null;
  date_to: string | null;
}

export default function BettingLinesStats() {
  const [data, setData] = useState<BettingLinesStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // Fetch stats for all leagues without date filter (all historical data)
      const response = await fetch(`${API_URL}/api/betting-lines/stats-by-league`);

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${await response.text()}`);
      }

      const result: BettingLinesStatsResponse = await response.json();
      setData(result);

    } catch (error) {
      console.error('Error fetching betting lines stats:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const getAccuracyColor = (accuracy: number): string => {
    if (accuracy >= 70) return 'text-green-400';
    if (accuracy >= 60) return 'text-yellow-400';
    if (accuracy >= 50) return 'text-orange-400';
    return 'text-red-400';
  };

  const getAccuracyBgColor = (accuracy: number): string => {
    if (accuracy >= 70) return 'bg-green-500/20';
    if (accuracy >= 60) return 'bg-yellow-500/20';
    if (accuracy >= 50) return 'bg-orange-500/20';
    return 'bg-red-500/20';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-slate-400">⏳ Cargando estadísticas...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 text-center">
        <div className="text-red-400 mb-4">❌ {error}</div>
        <button
          onClick={fetchStats}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          🔄 Reintentar
        </button>
      </div>
    );
  }

  if (!data || data.stats_by_league.length === 0) {
    return (
      <div className="text-center text-slate-400 py-12">
        <div className="text-6xl mb-4">📊</div>
        <div className="text-xl">No hay estadísticas disponibles</div>
      </div>
    );
  }

  const betTypes = ['TIROS', 'TIROS AL ARCO', 'CORNERS', 'TARJETAS', 'FALTAS'] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-lg p-6 border border-blue-500/30">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">📊</span>
          <div>
            <h3 className="text-2xl font-bold text-white">Estadísticas de Betting Lines</h3>
            <p className="text-slate-400 text-sm">
              Rendimiento por liga y tipo de apuesta
            </p>
          </div>
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <div className="bg-slate-800/50 rounded-lg px-4 py-2">
            <span className="text-slate-400">Total Ligas: </span>
            <span className="text-white font-bold">{data.total_leagues}</span>
          </div>
        </div>
      </div>

      {/* Stats by League */}
      {data.stats_by_league.map((league) => (
        <div
          key={league.league_code}
          className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
        >
          {/* League Header */}
          <div className="bg-gradient-to-r from-slate-700 to-slate-800 p-4 border-b border-slate-600">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{league.league_emoji}</span>
                <div>
                  <h4 className="text-xl font-bold text-white">{league.league_name}</h4>
                  <p className="text-slate-400 text-sm">
                    {league.total_matches} partidos analizados
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-slate-400 text-sm mb-1">Precisión General</div>
                <div className={`text-3xl font-bold ${getAccuracyColor(league.overall_accuracy)}`}>
                  {league.overall_accuracy.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Stats Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-900/50">
                  <th className="px-4 py-3 text-left text-slate-400 font-semibold text-sm">
                    Tipo de Apuesta
                  </th>
                  <th className="px-4 py-3 text-center text-slate-400 font-semibold text-sm">
                    ✅ Aciertos
                  </th>
                  <th className="px-4 py-3 text-center text-slate-400 font-semibold text-sm">
                    ❌ Fallos
                  </th>
                  <th className="px-4 py-3 text-center text-slate-400 font-semibold text-sm">
                    Total
                  </th>
                  <th className="px-4 py-3 text-center text-slate-400 font-semibold text-sm">
                    Precisión
                  </th>
                </tr>
              </thead>
              <tbody>
                {betTypes.map((betType, index) => {
                  const stats = league.stats[betType];
                  return (
                    <tr
                      key={betType}
                      className={`border-t border-slate-700/50 hover:bg-slate-700/30 transition-colors ${
                        index % 2 === 0 ? 'bg-slate-800/30' : ''
                      }`}
                    >
                      <td className="px-4 py-3 text-white font-medium">{betType}</td>
                      <td className="px-4 py-3 text-center text-green-400 font-semibold">
                        {stats.hit}
                      </td>
                      <td className="px-4 py-3 text-center text-red-400 font-semibold">
                        {stats.miss}
                      </td>
                      <td className="px-4 py-3 text-center text-slate-300 font-semibold">
                        {stats.total}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className={`${getAccuracyBgColor(stats.accuracy)} rounded-full px-3 py-1`}>
                            <span className={`font-bold ${getAccuracyColor(stats.accuracy)}`}>
                              {stats.accuracy.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="text-slate-300 text-sm space-y-2">
          <div className="font-semibold text-white mb-2">📖 Interpretación de colores</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-slate-400">≥ 70% - Excelente</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span className="text-slate-400">60-69% - Bueno</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span className="text-slate-400">50-59% - Regular</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-slate-400">&lt; 50% - Bajo</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
