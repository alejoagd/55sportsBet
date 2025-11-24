import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

/**
 * ScoreRangeEffectiveness - Análisis de efectividad por rangos de Score
 * 
 * Muestra qué rangos de score son más confiables para apostar
 */

interface ScoreRange {
  range_label: string;
  min_score: number;
  max_score: number;
  total_bets: number;
  hits: number;
  accuracy: number;
  roi: number;
  avg_odds: number;
  confidence_level: string;
  recommendation: string;
}

interface ScoreRangesData {
  ranges: ScoreRange[];
  best_range: ScoreRange | null;
  total_analyzed: number;
  overall_accuracy: number;
  recommendation_text: string;
}

interface Props {
  seasonId?: number;
  leagueId?: number;
}

const ScoreRangeEffectiveness: React.FC<Props> = ({ seasonId, leagueId }) => {
  const [data, setData] = useState<ScoreRangesData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [seasonId, leagueId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (seasonId) params.append('season_id', seasonId.toString());
      if (leagueId) params.append('league_id', leagueId.toString());
      
      const response = await fetch(
        `http://localhost:8000/api/best-bets/score-ranges?${params}`
      );
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error loading score ranges:', error);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'MUY ALTA': return 'text-green-400 bg-green-500/20';
      case 'ALTA': return 'text-blue-400 bg-blue-500/20';
      case 'MEDIA': return 'text-yellow-400 bg-yellow-500/20';
      case 'BAJA': return 'text-orange-400 bg-orange-500/20';
      case 'MUY BAJA': return 'text-red-400 bg-red-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getConfidenceIcon = (level: string) => {
    switch (level) {
      case 'MUY ALTA': return <CheckCircle className="w-5 h-5" />;
      case 'ALTA': return <CheckCircle className="w-5 h-5" />;
      case 'MEDIA': return <AlertTriangle className="w-5 h-5" />;
      case 'BAJA': return <AlertTriangle className="w-5 h-5" />;
      case 'MUY BAJA': return <XCircle className="w-5 h-5" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 bg-slate-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!data || data.ranges.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          📊 Efectividad por Rango de Score
        </h3>
        <p className="text-slate-400">
          No hay suficientes datos para analizar. Se necesitan más apuestas finalizadas.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          📊 Efectividad por Rango de Score
        </h3>
        <p className="text-slate-400 text-sm">
          Análisis de {data.total_analyzed} apuestas finalizadas
          <span className="ml-2">
            • Accuracy general: <span className="text-blue-400 font-semibold">{data.overall_accuracy.toFixed(1)}%</span>
          </span>
        </p>
      </div>

      {/* Rangos */}
      <div className="space-y-3 mb-6">
        {data.ranges.map((range) => {
          const accuracyPercent = (range.accuracy / 100) * 100; // Para el ancho de la barra
          const isBestRange = data.best_range?.range_label === range.range_label;
          
          return (
            <div 
              key={range.range_label}
              className={`
                p-4 rounded-lg border transition-all duration-200
                ${isBestRange 
                  ? 'border-green-500/50 bg-green-500/5' 
                  : 'border-slate-700 bg-slate-900/50 hover:bg-slate-900'
                }
              `}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-white font-bold text-lg">
                    Score {range.range_label}
                  </span>
                  <span className={`
                    flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold
                    ${getConfidenceColor(range.confidence_level)}
                  `}>
                    {getConfidenceIcon(range.confidence_level)}
                    {range.confidence_level}
                  </span>
                  {isBestRange && (
                    <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-semibold">
                      🔥 MEJOR
                    </span>
                  )}
                </div>
                
                <div className="text-right">
                  <div className="text-white font-bold text-xl">
                    {range.accuracy.toFixed(1)}%
                  </div>
                  <div className="text-slate-400 text-xs">
                    {range.hits}/{range.total_bets} aciertos
                  </div>
                </div>
              </div>

              {/* Barra de progreso */}
              <div className="mb-3">
                <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-500 ${
                      range.accuracy >= 80 ? 'bg-green-500' :
                      range.accuracy >= 70 ? 'bg-blue-500' :
                      range.accuracy >= 60 ? 'bg-yellow-500' :
                      range.accuracy >= 50 ? 'bg-orange-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${accuracyPercent}%` }}
                  />
                </div>
              </div>

              {/* Métricas */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-slate-400 text-xs">ROI</div>
                  <div className={`font-bold ${
                    range.roi > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {range.roi > 0 ? '+' : ''}{range.roi.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-xs">Cuota Prom.</div>
                  <div className="text-white font-semibold">
                    {range.avg_odds.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-xs">Apuestas</div>
                  <div className="text-white font-semibold">
                    {range.total_bets}
                  </div>
                </div>
              </div>

              {/* Recomendación */}
              <div className="mt-2 text-xs text-slate-400">
                {range.recommendation}
              </div>
            </div>
          );
        })}
      </div>

      {/* Recomendación General */}
      {data.best_range && (
        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <h4 className="text-white font-semibold mb-1">
                💡 Recomendación
              </h4>
              <p className="text-slate-300 text-sm">
                {data.recommendation_text}
              </p>
              <p className="text-slate-400 text-xs mt-2">
                Basado en el análisis de {data.total_analyzed} apuestas históricas
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoreRangeEffectiveness;