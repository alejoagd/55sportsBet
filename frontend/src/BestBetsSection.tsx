import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminOnly } from './AdminButton';

interface BestBet {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
  model: string;
  bet_type: string;
  prediction: string;
  confidence: number;
  historical_accuracy: number;
  combined_score: number;
}

interface HistoricalAccuracy {
  poisson?: {
    total_predictions: number;
    accuracy_1x2: number;
    accuracy_over25: number;
    accuracy_btts: number;
  };
  weinston?: {
    total_predictions: number;
    accuracy_1x2: number;
    accuracy_over25: number;
    accuracy_btts: number;
  };
}

interface BestBetsData {
  historical_accuracy: HistoricalAccuracy;
  top_bets: BestBet[];
  all_recommendations: BestBet[];
}

export default function BestBetsSection() {
  const navigate = useNavigate();
  const [data, setData] = useState<BestBetsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seasonId] = useState(2);

  useEffect(() => {
    fetchBestBets();
  }, []);

  const fetchBestBets = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/best-bets/analysis?season_id=${seasonId}`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar análisis');
      }
      
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="text-center text-slate-400">⏳ Analizando partidos...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-red-500/30">
        <div className="text-center text-red-400">❌ {error || 'Sin datos'}</div>
      </div>
    );
  }

  const { top_bets, historical_accuracy } = data;

  return (
    <div className="space-y-6">
      {/* Header con título y accuracy general */}
      <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg p-6 border border-green-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-4xl">🎯</span>
            <div>
              <h2 className="text-2xl font-bold text-white">Top 4 Apuestas Recomendadas del fin de semana</h2>
              <p className="text-slate-400 text-sm">Basado en análisis de rendimiento histórico</p>
            </div>
          </div>
          <AdminOnly hideCompletely={true}>
          <button
            onClick={fetchBestBets}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-semibold"
          >
            🔄 Actualizar
          </button>
          </AdminOnly>
        </div>

        {/* Accuracy histórica */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          {historical_accuracy.poisson && (
            <div className="bg-slate-800/50 rounded-lg p-4 border border-blue-500/20">
              <div className="text-blue-400 font-bold mb-2">📊 Poisson</div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">1X2:</span>
                  <span className="text-white font-mono">{historical_accuracy.poisson.accuracy_1x2.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Over/Under:</span>
                  <span className="text-white font-mono">{historical_accuracy.poisson.accuracy_over25.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">BTTS:</span>
                  <span className="text-white font-mono">{historical_accuracy.poisson.accuracy_btts.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          )}
          {historical_accuracy.weinston && (
            <div className="bg-slate-800/50 rounded-lg p-4 border border-orange-500/20">
              <div className="text-orange-400 font-bold mb-2">📊 Weinston</div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">1X2:</span>
                  <span className="text-white font-mono">{historical_accuracy.weinston.accuracy_1x2.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Over/Under:</span>
                  <span className="text-white font-mono">{historical_accuracy.weinston.accuracy_over25.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">BTTS:</span>
                  <span className="text-white font-mono">{historical_accuracy.weinston.accuracy_btts.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Top 4 Apuestas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {top_bets.map((bet, index) => (
          <div
            key={`${bet.match_id}-${bet.model}-${bet.bet_type}`}
            onClick={() => navigate(`/match/${bet.match_id}`)}
            className={`relative bg-slate-800 rounded-lg p-6 border-2 cursor-pointer hover:scale-[1.02] transition-transform ${getScoreBgColor(bet.combined_score)}`}
          >
            {/* Badge de ranking */}
            <div className="absolute -top-3 -left-3 w-12 h-12 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center shadow-lg">
              <span className="text-slate-900 font-bold text-xl">#{index + 1}</span>
            </div>

            {/* Fecha */}
            <div className="text-right text-slate-400 text-sm mb-3">
              {formatMatchDate(bet.date)}
            </div>

            {/* Equipos */}
            <div className="text-center mb-4">
              <div className="text-2xl font-bold text-white mb-1">
                {bet.home_team} <span className="text-slate-500">vs</span> {bet.away_team}
              </div>
            </div>

            {/* Predicción principal */}
            <div className="bg-slate-900/50 rounded-lg p-4 mb-4">
              <div className="text-center">
                <div className="text-slate-400 text-sm mb-1">Apuesta Recomendada</div>
                <div className="text-2xl font-bold text-green-400 mb-2">
                  {bet.prediction}
                </div>
                <div className="text-slate-400 text-xs">
                  {bet.bet_type}
                </div>
              </div>
            </div>

            {/* Métricas */}
            <div className="grid grid-cols-3 gap-3">
              {/* Score combinado */}
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Score</div>
                <div className={`text-xl font-bold ${getScoreColor(bet.combined_score)}`}>
                  {bet.combined_score.toFixed(1)}
                </div>
              </div>

              {/* Confianza */}
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Confianza</div>
                <div className="text-xl font-bold text-blue-400">
                  {bet.confidence.toFixed(0)}%
                </div>
              </div>

              {/* Histórico */}
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Histórico</div>
                <div className="text-xl font-bold text-purple-400">
                  {bet.historical_accuracy.toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Modelo */}
            <div className="mt-4 pt-4 border-t border-slate-700 text-center">
              <span className={`text-sm font-semibold ${
                bet.model === 'Poisson' ? 'text-blue-400' : 'text-orange-400'
              }`}>
                Modelo: {bet.model}
              </span>
            </div>

            {/* Indicador de calidad */}
            {bet.combined_score >= 50 && (
              <div className="absolute -top-2 -right-2 bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg">
                ⭐ ALTA CONFIANZA
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Explicación */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="text-slate-300 text-sm space-y-2">
          <div className="font-semibold text-white mb-2">📖 ¿Cómo se calcula el Score?</div>
          <div>
            <span className="text-green-400 font-mono">Score</span> = 
            <span className="text-blue-400 font-mono"> Confianza</span> × 
            <span className="text-purple-400 font-mono"> Histórico</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
            <li><strong className="text-blue-400">Confianza:</strong> Probabilidad que asigna el modelo a esta predicción</li>
            <li><strong className="text-purple-400">Histórico:</strong> % de aciertos del modelo en este tipo de apuesta</li>
            <li><strong className="text-green-400">Score combinado:</strong> Mayor score = Mayor probabilidad de acierto</li>
          </ul>
        </div>
      </div>
    </div>
  );
}