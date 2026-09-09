import { useState, useEffect } from 'react';
import { Target, TrendingUp, BarChart3 } from 'lucide-react';

interface H2HScoringData {
  match_id: number;
  total_h2h_matches: number;
  predictions: {
    [key: string]: {
      prediction: string;
      predicted_total?: number;
      line?: number;
      hit_count: number;
      valid_matches: number;
      score: number | null;
      percentage: number | null;
      hit_sequence?: boolean[];
    };
  };
  h2h_matches: any[];
  overall_confidence: number;
}

interface H2HScoringProps {
  matchId: number;
}

export default function H2HScoring({ matchId }: H2HScoringProps) {
  const [data, setData] = useState<H2HScoringData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchH2HScoring();
  }, [matchId]);

  const fetchH2HScoring = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/matches/${matchId}/h2h-scoring`
      );

      if (!response.ok) {
        throw new Error('Error al cargar H2H Scoring');
      }

      const result = await response.json();
      if (result.error) {
        setError(result.error);
      } else {
        setData(result);
      }
    } catch (error) {
      console.error('Error:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // Color del badge de score/confianza — mismo criterio en toda la tarjeta
  // (borde, número y "Confianza General") para que un vistazo alcance.
  const getScoreColor = (score: number | null): string => {
    if (score === null) return 'bg-slate-600 text-slate-400';
    if (score >= 10) return 'bg-green-500 text-white';
    if (score >= 8) return 'bg-green-400 text-white';
    if (score >= 6) return 'bg-yellow-500 text-black';
    if (score >= 4) return 'bg-orange-500 text-white';
    return 'bg-red-500 text-white';
  };

  const formatStatName = (statKey: string): string => {
    const names: { [key: string]: string } = {
      'goles': 'Goles Totales',
      'tiros': 'Tiros Totales',
      'tiros_al_arco': 'Tiros al Arco',
      'faltas': 'Faltas Totales',
      'tarjetas': 'Tarjetas Totales',
      'corners': 'Corners Totales',
      'btts': 'Ambos Marcan'
    };
    return names[statKey] || statKey;
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-700 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-4 bg-slate-700 rounded w-full"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center gap-3 text-slate-400">
          <Target className="w-5 h-5" />
          <span className="text-sm">
            {error || 'Sin datos H2H suficientes para análisis'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-purple-500/30 overflow-hidden">
      {/* Header */}
      <div className="p-4 sm:p-6 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg sm:text-xl font-bold text-purple-400">
                🎯 H2H Scoring System
              </h3>
              <p className="text-slate-400 text-xs sm:text-sm">
                ¿Cómo le hubiera ido a cada pronóstico en los últimos {data.total_h2h_matches} enfrentamientos?
              </p>
            </div>
          </div>

          {/* Confianza General */}
          <div className="text-left sm:text-right w-full sm:w-auto">
            <div className="text-xs text-slate-400 mb-1">Confianza General</div>
            <div className={`px-3 py-1 rounded-lg font-bold text-sm inline-block ${
              data.overall_confidence >= 8 ? 'bg-green-500/20 text-green-400' :
              data.overall_confidence >= 6 ? 'bg-yellow-500/20 text-yellow-400' :
              data.overall_confidence >= 4 ? 'bg-orange-500/20 text-orange-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {data.overall_confidence.toFixed(1)}/12
            </div>
          </div>
        </div>
      </div>

      {/* Leyenda — una sola vez, corta, pegada a lo que explica en vez de un
          bloque de texto aparte que el usuario tenía que ir a leer. */}
      <div className="px-4 sm:px-6 pt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-sm bg-green-500 inline-block" /> Habría acertado
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-sm bg-slate-600 inline-block" /> Habría fallado
        </span>
        <span>· de más reciente (izquierda) a más antiguo</span>
      </div>

      {/* Tarjetas de scoring — una por estadística, sin scroll horizontal */}
      <div className="p-4 sm:p-6 space-y-2.5">
        {Object.entries(data.predictions).map(([statKey, statData]) => (
          <div key={statKey} className="bg-slate-900/40 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-start justify-between gap-2 mb-2.5">
              <div className="min-w-0">
                <div className="text-white font-semibold text-sm truncate">
                  {formatStatName(statKey)}
                </div>
                {(statData.line !== undefined || statData.predicted_total !== undefined) && (
                  <div className="text-slate-500 text-[11px] truncate">
                    {statData.line !== undefined && `Línea ${statData.line}`}
                    {statData.predicted_total !== undefined && ` · Predicho ${statData.predicted_total.toFixed(1)}`}
                  </div>
                )}
              </div>
              <span className={`shrink-0 px-2.5 py-1 rounded text-xs font-bold ${
                statData.prediction.includes('OVER') ? 'bg-green-500/20 text-green-400' :
                statData.prediction.includes('UNDER') ? 'bg-blue-500/20 text-blue-400' :
                statData.prediction === 'YES' ? 'bg-green-500/20 text-green-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {statData.prediction}
              </span>
            </div>

            <div className="flex items-center justify-between gap-2">
              {statData.hit_sequence && statData.hit_sequence.length > 0 ? (
                <div className="flex items-center gap-1 flex-wrap flex-1 min-w-0">
                  {statData.hit_sequence.map((hit, i) => (
                    <span
                      key={i}
                      className={`w-2.5 h-2.5 rounded-sm shrink-0 ${hit ? 'bg-green-500' : 'bg-slate-600'}`}
                      title={hit ? 'Habría acertado' : 'Habría fallado'}
                    />
                  ))}
                </div>
              ) : (
                <span className="text-slate-500 text-[11px] italic flex-1">Sin historial suficiente</span>
              )}
              <span className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded ${getScoreColor(statData.score)}`}>
                {statData.hit_count}/{statData.valid_matches}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="px-4 sm:px-6 pb-4 sm:pb-6 -mt-1">
        {/* Indicador de recomendación */}
        {data.overall_confidence >= 8 && (
          <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-green-400" />
              <div>
                <p className="text-green-400 font-semibold text-sm">
                  ✅ ALTA CONFIANZA H2H - Recomendado para apuestas
                </p>
                <p className="text-slate-400 text-xs">
                  Este enfrentamiento tiene patrones históricos muy consistentes
                </p>
              </div>
            </div>
          </div>
        )}

        {data.overall_confidence < 4 && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-red-400" />
              <div>
                <p className="text-red-400 font-semibold text-sm">
                  ⚠️ BAJA CONFIANZA H2H - No recomendado
                </p>
                <p className="text-slate-400 text-xs">
                  Los patrones históricos son inconsistentes para este enfrentamiento
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
