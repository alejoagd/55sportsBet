import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminMode } from './Hooks/useAdminMode';
import LeagueSwitcher from './Leagueswitcher';


interface Match {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
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
  weinston_result: string;
  weinston_over_25: number;
  weinston_btts: number;

  weinston_prob_over_25?: number;  // Valor correcto de BD
  weinston_prob_btts?: number;     // Valor correcto de BD
  
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
  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([]);
  const [recentMatches, setRecentMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentLeagueId, setCurrentLeagueId] = useState(1);
  const [seasonId, setSeasonId] = useState(2);
  const { isAdmin } = useAdminMode();

  // Actualizar season_id cuando cambia la liga
  useEffect(() => {
    const updateSeasonForLeague = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${API_URL}/api/leagues/${currentLeagueId}`);

        if (response.ok) {
          const leagueData = await response.json();
          setSeasonId(leagueData.seasonId);
        }
      } catch (error) {
        console.error('Error obteniendo season_id:', error);
      }
    };

    updateSeasonForLeague();
  }, [currentLeagueId]);

  useEffect(() => {
    if (seasonId) {
      fetchData();
    }
  }, [seasonId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const upcomingResponse = await fetch(
        `${API_URL}/api/matches/upcoming?season_id=${seasonId}&limit=10`
      );
      
      if (!upcomingResponse.ok) {
        throw new Error(`Error ${upcomingResponse.status}`);
      }
      
      const upcomingData = await upcomingResponse.json();
      console.log('Upcoming matches:', upcomingData);
      setUpcomingMatches(upcomingData);

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

  const safeNumber = (value: any, defaultValue: number = 0): number => {
    if (value === null || value === undefined || isNaN(value)) {
      return defaultValue;
    }
    return Number(value);
  };

  const formatPercentage = (value: any): string => {
    const num = safeNumber(value);
    return (num * 100).toFixed(0);
  };

  // Función para formatear fecha sin problemas de zona horaria
  const formatMatchDate = (dateString: string): string => {
    if (!dateString) return '';
    
    // Parsear manualmente la fecha (YYYY-MM-DD) sin conversión de timezone
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
    const date = new Date(year, month - 1, day); // month - 1 porque JavaScript usa 0-11
    
    return date.toLocaleDateString('es-ES', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getPredictedResult = (probHome: number, probDraw: number, probAway: number) => {
    if (probHome > probDraw && probHome > probAway) return 'H';
    if (probAway > probDraw && probAway > probHome) return 'A';
    return 'D';
  };

  const getResultLabel = (result: string) => {
    if (result === 'H') return '1';
    if (result === 'A') return '2';
    return 'X';
  };

  const renderMatchCard = (match: Match, showResult: boolean = false) => {
    const poissonPredictedResult = getPredictedResult(
      safeNumber(match.poisson_prob_home),
      safeNumber(match.poisson_prob_draw),
      safeNumber(match.poisson_prob_away)
    );

    return (
      <div
        key={match.match_id}
        onClick={() => navigate(`/match/${match.match_id}`)}
        className="bg-slate-800 rounded-lg p-4 hover:bg-slate-700/50 transition-colors border border-slate-700 cursor-pointer"
      >
        {/* Fecha */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-slate-400 text-sm">
            {formatMatchDate(match.date)}
          </span>
          {showResult && (
            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded font-bold">
              FT
            </span>
          )}
        </div>

        {/* Equipos y Resultado */}
        <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center mb-4">
          <div className="text-right">
            <div className="text-white font-bold text-lg">{match.home_team}</div>
          </div>

          <div className="flex flex-col items-center gap-1 min-w-[80px]">
            {showResult && match.actual_home_goals !== undefined ? (
              <div className="text-3xl font-bold text-white">
                {match.actual_home_goals} - {match.actual_away_goals}
              </div>
            ) : (
              <div className="text-slate-400 text-sm font-semibold">vs</div>
            )}
          </div>

          <div className="text-left">
            <div className="text-white font-bold text-lg">{match.away_team}</div>
          </div>
        </div>

        {/* Predicciones */}
        <div className="grid grid-cols-2 gap-3">
          {/* Poisson */}
          <div className="bg-slate-900/50 rounded p-3 border border-blue-500/20">
            <div className="flex items-center justify-between mb-2">
              <span className="text-blue-400 font-semibold text-sm">Poisson</span>
              {showResult && (
                <div className="flex gap-1">
                  {match.poisson_hit_1x2 !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.poisson_hit_1x2 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="Resultado 1X2"
                    >
                      {match.poisson_hit_1x2 ? '✓' : '✗'}
                    </span>
                  )}
                  {match.poisson_hit_over25 !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.poisson_hit_over25 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="Over/Under 2.5"
                    >
                      {match.poisson_hit_over25 ? '✓' : '✗'}
                    </span>
                  )}
                  {match.poisson_hit_btts !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.poisson_hit_btts 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="BTTS"
                    >
                      {match.poisson_hit_btts ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Marcador:</span>
                <span className="text-white font-mono">
                  {safeNumber(match.poisson_home_goals).toFixed(1)} - {safeNumber(match.poisson_away_goals).toFixed(1)}
                </span>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">Resultado:</span>
                <div className="flex items-center gap-2">
                  <span className="text-blue-300 font-mono font-bold">
                    {getResultLabel(poissonPredictedResult)} ({(
                      (poissonPredictedResult === 'H' ? safeNumber(match.poisson_prob_home) :
                       poissonPredictedResult === 'A' ? safeNumber(match.poisson_prob_away) :
                       safeNumber(match.poisson_prob_draw)) * 100
                    ).toFixed(0)}%)
                  </span>
                  {showResult && match.poisson_hit_1x2 !== undefined && (
                    <span className={`text-xs font-bold ${match.poisson_hit_1x2 ? 'text-green-400' : 'text-red-400'}`}>
                      {match.poisson_hit_1x2 ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">O/U 2.5:</span>
                <div className="flex items-center gap-2">
                  {(() => {
                    const overProb = safeNumber(match.poisson_over_25);
                    const underProb = 1 - overProb;
                    const isOver = overProb >= 0.5;
                    const displayProb = isOver ? overProb : underProb;
                    
                    return (
                      <span className={`font-mono text-xs ${isOver ? 'text-green-400' : 'text-orange-400'}`}>
                        {isOver ? 'Over' : 'Under'} {formatPercentage(displayProb)}%
                      </span>
                    );
                  })()}
                  {showResult && match.poisson_hit_over25 !== undefined && (
                    <span className={`text-xs font-bold ${match.poisson_hit_over25 ? 'text-green-400' : 'text-red-400'}`}>
                      {match.poisson_hit_over25 ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">BTTS:</span>
                <div className="flex items-center gap-2">
                  {(() => {
                    const bttsProb = safeNumber(match.poisson_btts);
                    const noBttsProb = 1 - bttsProb;
                    const isBtts = bttsProb >= 0.5;
                    const displayProb = isBtts ? bttsProb : noBttsProb;
                    
                    return (
                      <span className={`font-mono text-xs ${isBtts ? 'text-green-400' : 'text-orange-400'}`}>
                        {isBtts ? 'Sí' : 'No'} {formatPercentage(displayProb)}%
                      </span>
                    );
                  })()}
                  {showResult && match.poisson_hit_btts !== undefined && (
                    <span className={`text-xs font-bold ${match.poisson_hit_btts ? 'text-green-400' : 'text-red-400'}`}>
                      {match.poisson_hit_btts ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Weinston */}
          <div className="bg-slate-900/50 rounded p-3 border border-orange-500/20">
            <div className="flex items-center justify-between mb-2">
              <span className="text-orange-400 font-semibold text-sm">Weinston</span>
              {showResult && (
                <div className="flex gap-1">
                  {match.weinston_hit_1x2 !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.weinston_hit_1x2 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="Resultado 1X2"
                    >
                      {match.weinston_hit_1x2 ? '✓' : '✗'}
                    </span>
                  )}
                  {match.weinston_hit_over25 !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.weinston_hit_over25 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="Over/Under 2.5"
                    >
                      {match.weinston_hit_over25 ? '✓' : '✗'}
                    </span>
                  )}
                  {match.weinston_hit_btts !== undefined && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                        match.weinston_hit_btts 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}
                      title="BTTS"
                    >
                      {match.weinston_hit_btts ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Marcador:</span>
                <span className="text-white font-mono">
                  {safeNumber(match.weinston_home_goals).toFixed(1)} - {safeNumber(match.weinston_away_goals).toFixed(1)}
                </span>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">Resultado:</span>
                <div className="flex items-center gap-2">
                  <span className="text-orange-300 font-mono font-bold">
                    {getResultLabel(match.weinston_result || 'D')}
                  </span>
                  {showResult && match.weinston_hit_1x2 !== undefined && (
                    <span className={`text-xs font-bold ${match.weinston_hit_1x2 ? 'text-green-400' : 'text-red-400'}`}>
                      {match.weinston_hit_1x2 ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">O/U 2.5:</span>
                <div className="flex items-center gap-2">
                  {(() => {
                    // ✅ CAMBIO: Usar ?? para fallback a weinston_over_25 si prob no existe
                    const overProb = safeNumber(match.weinston_prob_over_25 ?? match.weinston_over_25);
                    const underProb = 1 - overProb;
                    const isOver = overProb >= 0.5;  // ✅ CAMBIO: >= en lugar de >
                    const displayProb = isOver ? overProb : underProb;

                    return (
                      <span className={`font-mono text-xs ${isOver ? 'text-green-400' : 'text-orange-400'}`}>
                        {isOver ? 'Over' : 'Under'} {(displayProb * 100).toFixed(1)}%  {/* ✅ CAMBIO: toFixed(1) */}
                      </span>
                    );
                  })()}
                  {showResult && match.weinston_hit_over25 !== undefined && (
                    <span className={`text-xs font-bold ${match.weinston_hit_over25 ? 'text-green-400' : 'text-red-400'}`}>
                      {match.weinston_hit_over25 ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-slate-400">BTTS:</span>
                <div className="flex items-center gap-2">
                  {(() => {
                    // ✅ CAMBIO: Usar ?? para fallback
                    const bttsProb = safeNumber(match.weinston_prob_btts ?? match.weinston_btts);
                    const noBttsProb = 1 - bttsProb;
                    const isBtts = bttsProb >= 0.5;  // ✅ CAMBIO: >= en lugar de >
                    const displayProb = isBtts ? bttsProb : noBttsProb;

                    return (
                      <span className={`font-mono text-xs ${isBtts ? 'text-green-400' : 'text-orange-400'}`}>
                        {isBtts ? 'Sí' : 'No'} {(displayProb * 100).toFixed(1)}%  {/* ✅ CAMBIO: toFixed(1) */}
                      </span>
                    );
                  })()}
                  {showResult && match.weinston_hit_btts !== undefined && (
                    <span className={`text-xs font-bold ${match.weinston_hit_btts ? 'text-green-400' : 'text-red-400'}`}>
                      {match.weinston_hit_btts ? '✓' : '✗'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Árbitro */}
        {match.referee && (
          <div className="mt-3 pt-3 border-t border-slate-700 text-center text-slate-400 text-xs">
            👨‍⚖️ {match.referee}
          </div>
        )}
      </div>
    );
  };

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

  return (
    <>
      {/* ✨ SELECTOR DE LIGAS - DEBE IR AQUÍ ARRIBA */}
      <LeagueSwitcher 
        currentLeagueId={currentLeagueId}
        onLeagueChange={(leagueId) => {
          setCurrentLeagueId(leagueId);
          setLoading(true);
        }}
      />

      {/* CONTENIDO DEL DASHBOARD */}
      <div className="min-h-screen bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto space-y-8">

          {/* Header */}
          <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-lg p-6 shadow-xl border border-slate-600">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-white mb-2">
                  📊 Dashboard de Predicciones
                </h1>
                <p className="text-slate-300">
                  Temporada 2025/2026
                </p>
              </div>
              {/* ✅ SOLO MOSTRAR SI ES ADMIN */}
              {isAdmin && (
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
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  🔄 Recalcular Aciertos
                </button>
              )}
            </div>
          </div>

          {/* Próximos Partidos */}
          {upcomingMatches.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-white">
                  🔮 Próximos Partidos
                </h2>
                <span className="text-slate-400 text-sm bg-slate-800 px-3 py-1 rounded-full">
                  {upcomingMatches.length} partidos
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {upcomingMatches.map((match) => renderMatchCard(match, false))}
              </div>
            </section>
          )}

          {/* Resultados Recientes */}
          {recentMatches.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-white">
                  📋 Resultados Recientes
                </h2>
                <span className="text-slate-400 text-sm bg-slate-800 px-3 py-1 rounded-full">
                  {recentMatches.length} partidos
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recentMatches.map((match) => renderMatchCard(match, true))}
              </div>
            </section>
          )}

          {/* Sin datos */}
          {upcomingMatches.length === 0 && recentMatches.length === 0 && (
            <div className="text-center py-12">
              <div className="text-slate-400 text-lg">
                No hay partidos disponibles
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}