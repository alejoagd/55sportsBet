// ============================================================================
// BestBetsSection.tsx - VERSIÓN CORREGIDA
// ============================================================================
//
// PROBLEMA IDENTIFICADO:
// - Llamaba a /history sin season_id (error 422)
// - No mostraba info de liga
//
// SOLUCIÓN:
// - Llamar sin season_id (multiliga automático)
// - Mostrar info de liga cuando esté disponible
// - Fallback si no hay datos de liga
//
// ============================================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminOnly } from './AdminButton';
import ScoreRangeEffectiveness from './Scorerangeeffectiveness';

interface BestBet {
  id: number;
  match_id: number;
  season_id: number;
  date: string;
  home_team: string;
  away_team: string;
  league?: string;           // Opcional (puede no venir del backend)
  league_emoji?: string;     // Opcional
  country?: string;          // Opcional
  model: string;
  bet_type: string;
  prediction: string;
  confidence: number;
  historical_accuracy: number;
  combined_score: number;
  rank: number;
  odds?: number | null;
  hit?: boolean | null;
  profit_loss?: number | null;
}

export default function BestBetsSection() {
  const navigate = useNavigate();
  const [topBets, setTopBets] = useState<BestBet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchBestBets();
  }, []);

  const fetchBestBets = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // Sin season_id para obtener MULTILIGA
      const response = await fetch(
        `${API_URL}/api/best-bets/history?limit=4&validated=false`
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Error ${response.status}: ${errorText}`);
      }
      
      const data: BestBet[] = await response.json();
      
      console.log('✅ Best bets recibidas:', data);
      
      // Ordenar por rank
      const sorted = data.sort((a, b) => a.rank - b.rank);
      setTopBets(sorted);
      
    } catch (error) {
      console.error('❌ Error fetching best bets:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // Función para refrescar análisis (solo admin)
  const refreshAnalysis = async () => {
    setRefreshing(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const today = new Date();
      const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
      
      const dateFrom = today.toISOString().split('T')[0];
      const dateTo = nextWeek.toISOString().split('T')[0];
      
      const response = await fetch(
        `${API_URL}/api/best-bets/analysis-multiliga?date_from=${dateFrom}&date_to=${dateTo}&top_n=4`
      );
      
      if (response.ok) {
        setTimeout(() => {
          fetchBestBets();
          setRefreshing(false);
        }, 1000);
      } else {
        throw new Error('Error al actualizar');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('❌ Error al actualizar análisis. Asegúrate de que el endpoint /analysis-multiliga esté disponible.');
      setRefreshing(false);
    }
  };

  const formatMatchDate = (dateString: string): string => {
    if (!dateString) return '';
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('es-ES', {
      weekday: 'short',
      day: '2-digit',
      month: 'short'
    });
  };

  const getScoreColor = (score: number): string => {
    if (score >= 50) return 'text-green-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getScoreBgColor = (score: number): string => {
    if (score >= 50) return 'bg-green-500/20 border-green-500/30';
    if (score >= 40) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-orange-500/20 border-orange-500/30';
  };

  const formatBetType = (betType: string): string => {
    const types: Record<string, string> = {
      '1X2': '1X2',
      'OVER_25': 'Over/Under 2.5',
      'Over/Under': 'Over/Under 2.5',
      'BTTS': 'BTTS',
      'CORNERS': 'Corners',
      'SHOTS': 'Tiros',
      'SHOTS_ON_TARGET': 'Tiros a puerta',
      'CARDS': 'Tarjetas',
      'FOULS': 'Faltas'
    };
    return types[betType] || betType;
  };

  const getLeagueStats = () => {
    const leagueCount: Record<string, number> = {};
    topBets.forEach(bet => {
      if (bet.league) {
        leagueCount[bet.league] = (leagueCount[bet.league] || 0) + 1;
      }
    });
    return leagueCount;
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="text-center text-slate-400">⏳ Cargando mejores apuestas...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-red-500/30">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ {error}</div>
          <button
            onClick={fetchBestBets}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            🔄 Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (topBets.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="text-center text-slate-400">
          <div className="text-6xl mb-4">🎯</div>
          <div className="text-xl font-bold text-white mb-2">No hay apuestas recomendadas aún</div>
        </div>
      </div>
    );
  }

  const leagueStats = getLeagueStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg p-6 border border-green-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-4xl">🎯</span>
            <div>
              <h2 className="text-2xl font-bold text-white">
                Top 4 Apuestas Recomendadas
                {Object.keys(leagueStats).length > 1 && (
                  <span className="ml-2 text-sm font-normal text-green-400">✨ Multiliga</span>
                )}
              </h2>
              <p className="text-slate-400 text-sm">
                {Object.keys(leagueStats).length > 1 
                  ? 'Análisis de todas las ligas disponibles' 
                  : 'Mejores apuestas de la semana'}
              </p>
            </div>
          </div>
          
          <AdminOnly hideCompletely={true}>
            <button
              onClick={refreshAnalysis}
              disabled={refreshing}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded-lg transition-colors text-sm font-semibold"
            >
              {refreshing ? '⏳ Actualizando...' : '🔄 Actualizar'}
            </button>
          </AdminOnly>
        </div>

        {/* Estadísticas de ligas */}
        {Object.keys(leagueStats).length > 0 && (
          <div className="flex gap-3 flex-wrap">
            <div className="text-slate-400 text-sm font-semibold">Ligas:</div>
            {Object.entries(leagueStats).map(([league, count]) => (
              <div key={league} className="bg-slate-800/50 rounded-full px-3 py-1 text-sm">
                <span className="text-white font-semibold">{league || 'Liga'}</span>
                <span className="text-slate-400 ml-1">({count})</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ScoreRangeEffectiveness */}
      <ScoreRangeEffectiveness seasonId={topBets[0]?.season_id || 2} />

      {/* Top 4 Apuestas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {topBets.map((bet) => (
          <div
            key={bet.id}
            onClick={() => navigate(`/match/${bet.match_id}`)}
            className={`relative bg-slate-800 rounded-lg p-6 border-2 cursor-pointer hover:scale-[1.02] transition-transform ${getScoreBgColor(bet.combined_score)}`}
          >
            {/* Badge de ranking */}
            <div className="absolute -top-3 -left-3 w-12 h-12 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center shadow-lg">
              <span className="text-slate-900 font-bold text-xl">#{bet.rank}</span>
            </div>

            {/* Info de liga (si existe) */}
            {bet.league && (
              <div className="absolute -top-2 -right-2 bg-slate-900 border border-slate-700 rounded-full px-3 py-1 text-xs font-bold shadow-lg flex items-center gap-1">
                {bet.league_emoji && <span>{bet.league_emoji}</span>}
                <span className="text-white">{bet.league}</span>
              </div>
            )}

            {/* Fecha */}
            <div className="text-right text-slate-400 text-sm mb-3 mt-2">
              {formatMatchDate(bet.date)}
            </div>

            {/* Equipos */}
            <div className="text-center mb-4">
              <div className="text-2xl font-bold text-white mb-1">
                {bet.home_team} <span className="text-slate-500">vs</span> {bet.away_team}
              </div>
            </div>

            {/* Predicción */}
            <div className="bg-slate-900/50 rounded-lg p-4 mb-4">
              <div className="text-center">
                <div className="text-slate-400 text-sm mb-1">Apuesta Recomendada</div>
                <div className="text-2xl font-bold text-green-400 mb-2">
                  {bet.prediction}
                </div>
                <div className="text-slate-400 text-xs">
                  {formatBetType(bet.bet_type)}
                </div>
              </div>
            </div>

            {/* Métricas */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Score</div>
                <div className={`text-xl font-bold ${getScoreColor(bet.combined_score)}`}>
                  {bet.combined_score.toFixed(1)}
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Confianza</div>
                <div className="text-xl font-bold text-blue-400">
                  {bet.confidence.toFixed(0)}%
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Histórico</div>
                <div className="text-xl font-bold text-purple-400">
                  {bet.historical_accuracy.toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Modelo */}
            <div className="mt-4 pt-4 border-t border-slate-700 text-center">
              <span className={`text-sm font-semibold capitalize ${
                bet.model === 'poisson' ? 'text-blue-400' : 'text-orange-400'
              }`}>
                Modelo: {bet.model}
              </span>
            </div>

            {/* Indicadores */}
            {bet.combined_score >= 50 && (
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg whitespace-nowrap">
                ⭐ ALTA CONFIANZA
              </div>
            )}

            {bet.hit !== null && (
              <div className={`absolute top-2 left-2 px-2 py-1 rounded text-xs font-bold ${
                bet.hit ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 
                'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {bet.hit ? '✅ Acertó' : '❌ Falló'}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Explicación */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="text-slate-300 text-sm space-y-2">
          <div className="font-semibold text-white mb-2">📖 ¿Cómo funciona?</div>
          
          <div className="mb-3">
            <span className="text-green-400 font-mono">Score</span> = 
            <span className="text-blue-400 font-mono"> Confianza</span> × 
            <span className="text-purple-400 font-mono"> Histórico</span>
          </div>
          
          <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
            <li>
              <strong className="text-blue-400">Confianza:</strong> Probabilidad que asigna el modelo
            </li>
            <li>
              <strong className="text-purple-400">Histórico:</strong> % de aciertos del modelo
            </li>
            <li>
              <strong className="text-green-400">Score:</strong> Mayor score = Mayor probabilidad
            </li>
            {Object.keys(leagueStats).length > 1 && (
              <li>
                <strong className="text-yellow-400">Multiliga:</strong> Se analizan todas las ligas simultáneamente
              </li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}