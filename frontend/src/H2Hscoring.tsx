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
      const response = await fetch(
        `http://localhost:8000/api/matches/${matchId}/h2h-scoring`
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

  // Función para obtener el color del score basado en la confianza
  const getScoreColor = (score: number | null): string => {
    if (score === null) return 'bg-slate-600 text-slate-400';
    
    // Colores basados en tu sistema Excel
    if (score >= 10) return 'bg-green-500 text-white font-bold'; // Verde intenso 80%+
    if (score >= 8) return 'bg-green-400 text-white font-bold';   // Verde 70%+
    if (score >= 6) return 'bg-yellow-500 text-black font-bold'; // Amarillo 50%+
    if (score >= 4) return 'bg-orange-500 text-white';           // Naranja 33%+
    return 'bg-red-500 text-white';                              // Rojo menor a 33%
  };

  // Función para obtener texto de confianza
  const getConfidenceText = (score: number | null): string => {
    if (score === null) return 'Sin datos';
    
    if (score >= 10) return 'MUY ALTA 🔥';
    if (score >= 8) return 'ALTA 🟢';
    if (score >= 6) return 'MEDIA 🟡';
    if (score >= 4) return 'BAJA 🟠';
    return 'MUY BAJA 🔴';
  };

  // Función para formatear el nombre de la estadística
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
      <div className="p-6 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <BarChart3 className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-purple-400">
                🎯 H2H Scoring System
              </h3>
              <p className="text-slate-400 text-sm">
                Análisis basado en {data.total_h2h_matches} enfrentamientos directos
              </p>
            </div>
          </div>
          
          {/* Confianza General */}
          <div className="text-right">
            <div className="text-xs text-slate-400 mb-1">Confianza General</div>
            <div className={`px-3 py-1 rounded-lg font-bold text-sm ${
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

      {/* Tabla de Scoring */}
      <div className="p-6">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="py-3 px-4 text-left text-slate-400 font-medium text-sm">
                  Estadística
                </th>
                <th className="py-3 px-4 text-center text-slate-400 font-medium text-sm">
                  Predicción
                </th>
                <th className="py-3 px-4 text-center text-slate-400 font-medium text-sm">
                  H2H Score
                </th>
                <th className="py-3 px-4 text-center text-slate-400 font-medium text-sm">
                  Aciertos
                </th>
                <th className="py-3 px-4 text-center text-slate-400 font-medium text-sm">
                  Confianza
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.predictions).map(([statKey, statData]) => (
                <tr key={statKey} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                  {/* Nombre de la estadística */}
                  <td className="py-4 px-4">
                    <div className="font-medium text-slate-300">
                      {formatStatName(statKey)}
                    </div>
                    {statData.line && (
                      <div className="text-xs text-slate-500">
                        Línea: {statData.line}
                      </div>
                    )}
                  </td>

                  {/* Predicción */}
                  <td className="py-4 px-4 text-center">
                    <span className={`px-3 py-1 rounded text-xs font-bold ${
                      statData.prediction.includes('OVER') ? 'bg-green-500/20 text-green-400' :
                      statData.prediction.includes('UNDER') ? 'bg-blue-500/20 text-blue-400' :
                      statData.prediction === 'YES' ? 'bg-green-500/20 text-green-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {statData.prediction}
                    </span>
                    {statData.predicted_total && (
                      <div className="text-xs text-slate-500 mt-1">
                        Total: {statData.predicted_total.toFixed(1)}
                      </div>
                    )}
                  </td>

                  {/* Score Visual */}
                  <td className="py-4 px-4 text-center">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-lg text-lg font-bold ${getScoreColor(statData.score)}`}>
                      {statData.score || '?'}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      de {data.total_h2h_matches}
                    </div>
                  </td>

                  {/* Aciertos */}
                  <td className="py-4 px-4 text-center">
                    <div className="text-white font-mono font-bold">
                      {statData.hit_count}/{statData.valid_matches}
                    </div>
                    {statData.percentage && (
                      <div className="text-xs text-slate-400">
                        {statData.percentage}%
                      </div>
                    )}
                  </td>

                  {/* Confianza */}
                  <td className="py-4 px-4 text-center">
                    <div className="text-xs font-bold">
                      {getConfidenceText(statData.score)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Leyenda del sistema de scoring */}
        <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
          <h4 className="text-slate-300 text-sm font-semibold mb-3">
            📊 Leyenda del Sistema de Scoring:
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-green-500 rounded text-white flex items-center justify-center font-bold text-xs">
                10+
              </div>
              <span className="text-slate-400">MUY ALTA (80%+)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-green-400 rounded text-white flex items-center justify-center font-bold text-xs">
                8+
              </div>
              <span className="text-slate-400">ALTA (65%+)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-yellow-500 rounded text-black flex items-center justify-center font-bold text-xs">
                6+
              </div>
              <span className="text-slate-400">MEDIA (50%+)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-orange-500 rounded text-white flex items-center justify-center font-bold text-xs">
                4+
              </div>
              <span className="text-slate-400">BAJA (33%+)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-red-500 rounded text-white flex items-center justify-center font-bold text-xs">
                &lt;4
              </div>
              <span className="text-slate-400">MUY BAJA (&lt;33%)</span>
            </div>
          </div>
          
          <div className="mt-3 pt-3 border-t border-slate-700">
            <p className="text-slate-400 text-xs">
              💡 <span className="font-semibold">Score = Aciertos en H2H.</span> 
              {" "}Ejemplo: Si en 12 enfrentamientos anteriores, la predicción OVER 10.5 Corners
              {" "}acertó 9 veces, el score es 9 (75% de confianza).
            </p>
          </div>
        </div>

        {/* Indicador de recomendación */}
        {data.overall_confidence >= 8 && (
          <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
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
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
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