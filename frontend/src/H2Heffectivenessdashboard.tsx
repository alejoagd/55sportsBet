import { useState, useEffect } from 'react';
import { BarChart3, Target, TrendingUp, Award } from 'lucide-react';

interface EffectivenessData {
  by_stat: {
    [statName: string]: Array<{
      score: number;
      total: number;
      hits: number;
      accuracy: number;
    }>;
  };
  summary: {
    total_analyzed: number;
    high_confidence_bets: number;
    high_confidence_accuracy: number;
  };
}

interface H2HEffectivenessDashboardProps {
  seasonId: number;
}

export default function H2HEffectivenessDashboard({ seasonId }: H2HEffectivenessDashboardProps) {
  const [data, setData] = useState<EffectivenessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedStat, setSelectedStat] = useState<string>('corners');
  const [minScore, setMinScore] = useState<number>(8);

  useEffect(() => {
    fetchEffectivenessData();
  }, [seasonId, minScore]);

  const fetchEffectivenessData = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/leagues/${seasonId}/h2h-effectiveness?min_score=${minScore}`
      );

      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (error) {
      console.error('Error fetching effectiveness data:', error);
    } finally {
      setLoading(false);
    }
  };

  const runBulkAnalysis = async () => {
    try {
      setLoading(true);
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/leagues/${seasonId}/h2h-bulk-analysis`,
        { method: 'POST' }
      );

      if (response.ok) {
        // Recargar datos después del análisis
        await fetchEffectivenessData();
      }
    } catch (error) {
      console.error('Error running bulk analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  // Función para obtener color basado en accuracy
  const getAccuracyColor = (accuracy: number): string => {
    if (accuracy >= 80) return 'text-green-400 font-bold';
    if (accuracy >= 70) return 'text-green-300';
    if (accuracy >= 60) return 'text-yellow-400';
    if (accuracy >= 50) return 'text-orange-400';
    return 'text-red-400';
  };

  // Función para obtener color de fondo para highlighting
  const getRowBgColor = (accuracy: number): string => {
    if (accuracy >= 80) return 'bg-green-500/10 border-green-500/20';
    if (accuracy >= 70) return 'bg-green-500/5 border-green-500/10';
    return 'bg-slate-800/50 border-slate-700';
  };

  // Nombres de estadísticas
  const statNames: { [key: string]: string } = {
    'goles': 'Goles Totales',
    'corners': 'Corners',
    'tiros': 'Tiros',
    'tiros_al_arco': 'Tiros al Arco',
    'faltas': 'Faltas',
    'tarjetas': 'Tarjetas',
    'btts': 'BTTS'
  };

  if (loading) {
    return (
      <div className="bg-slate-900 rounded-lg p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-700 rounded w-1/2"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-6 bg-slate-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-lg">
              <BarChart3 className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                📊 Dashboard de Efectividad H2H
              </h1>
              <p className="text-purple-100 text-sm">
                Análisis de precisión por puntuación histórica
              </p>
            </div>
          </div>

          <button
            onClick={runBulkAnalysis}
            disabled={loading}
            className="px-6 py-3 bg-white/20 hover:bg-white/30 text-white rounded-lg font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Analizando...' : '🔄 Ejecutar Análisis'}
          </button>
        </div>
      </div>

      {/* Resumen General */}
      {data?.summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <Target className="w-6 h-6 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">Total Analizado</h3>
            </div>
            <p className="text-3xl font-bold text-blue-400">{data.summary.total_analyzed}</p>
            <p className="text-slate-400 text-sm">Partidos procesados</p>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <Award className="w-6 h-6 text-green-400" />
              <h3 className="text-lg font-semibold text-white">Alta Confianza</h3>
            </div>
            <p className="text-3xl font-bold text-green-400">{data.summary.high_confidence_bets}</p>
            <p className="text-slate-400 text-sm">Apuestas score ≥ {minScore}</p>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-6 h-6 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Accuracy Objetivo</h3>
            </div>
            <p className="text-3xl font-bold text-purple-400">
              {data.summary.high_confidence_accuracy.toFixed(1)}%
            </p>
            <p className="text-slate-400 text-sm">En apuestas de alta confianza</p>
          </div>
        </div>
      )}

      {/* Controles */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-slate-400 text-sm font-medium">Estadística:</label>
            <select
              value={selectedStat}
              onChange={(e) => setSelectedStat(e.target.value)}
              className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
            >
              {Object.entries(statNames).map(([key, name]) => (
                <option key={key} value={key}>{name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-slate-400 text-sm font-medium">Score Mínimo:</label>
            <select
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
            >
              <option value={6}>6+</option>
              <option value={7}>7+</option>
              <option value={8}>8+</option>
              <option value={9}>9+</option>
              <option value={10}>10+</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabla de Efectividad */}
      {data?.by_stat && selectedStat && data.by_stat[selectedStat] && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-700 bg-slate-900/50">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              📈 Efectividad: {statNames[selectedStat]}
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Precisión por puntuación H2H (estilo Excel)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-900">
                <tr>
                  <th className="py-4 px-6 text-left text-slate-400 font-semibold text-sm">
                    Score H2H
                  </th>
                  <th className="py-4 px-6 text-center text-slate-400 font-semibold text-sm">
                    Total Predicciones
                  </th>
                  <th className="py-4 px-6 text-center text-slate-400 font-semibold text-sm">
                    Aciertos
                  </th>
                  <th className="py-4 px-6 text-center text-slate-400 font-semibold text-sm">
                    Accuracy %
                  </th>
                  <th className="py-4 px-6 text-center text-slate-400 font-semibold text-sm">
                    Evaluación
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.by_stat[selectedStat]
                  .sort((a, b) => b.score - a.score) // Ordenar por score descendente
                  .map((row) => (
                    <tr 
                      key={row.score} 
                      className={`border-b border-slate-700 ${getRowBgColor(row.accuracy)} hover:bg-slate-700/30 transition-colors`}
                    >
                      {/* Score */}
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm ${
                            row.score >= 10 ? 'bg-green-500 text-white' :
                            row.score >= 8 ? 'bg-green-400 text-white' :
                            row.score >= 6 ? 'bg-yellow-500 text-black' :
                            row.score >= 4 ? 'bg-orange-500 text-white' :
                            'bg-red-500 text-white'
                          }`}>
                            {row.score}
                          </div>
                          <span className="text-white font-medium">
                            {row.score}/12
                          </span>
                        </div>
                      </td>

                      {/* Total */}
                      <td className="py-4 px-6 text-center">
                        <span className="text-white font-mono text-lg">
                          {row.total}
                        </span>
                      </td>

                      {/* Hits */}
                      <td className="py-4 px-6 text-center">
                        <span className="text-green-400 font-mono text-lg font-bold">
                          {row.hits}
                        </span>
                      </td>

                      {/* Accuracy */}
                      <td className="py-4 px-6 text-center">
                        <div className="flex flex-col items-center">
                          <span className={`font-mono text-xl font-bold ${getAccuracyColor(row.accuracy)}`}>
                            {row.accuracy.toFixed(1)}%
                          </span>
                          <div className="w-full bg-slate-700 rounded-full h-2 mt-1">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                row.accuracy >= 80 ? 'bg-green-500' :
                                row.accuracy >= 70 ? 'bg-green-400' :
                                row.accuracy >= 60 ? 'bg-yellow-500' :
                                row.accuracy >= 50 ? 'bg-orange-500' :
                                'bg-red-500'
                              }`}
                              style={{ width: `${Math.min(row.accuracy, 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>

                      {/* Evaluación */}
                      <td className="py-4 px-6 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                          row.accuracy >= 80 ? 'bg-green-500/20 text-green-400' :
                          row.accuracy >= 70 ? 'bg-green-400/20 text-green-300' :
                          row.accuracy >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
                          row.accuracy >= 50 ? 'bg-orange-500/20 text-orange-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {row.accuracy >= 80 ? 'EXCELENTE 🔥' :
                           row.accuracy >= 70 ? 'MUY BUENO ✅' :
                           row.accuracy >= 60 ? 'BUENO 🟢' :
                           row.accuracy >= 50 ? 'REGULAR 🟡' :
                           'MALO 🔴'}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* Insights */}
          {data.by_stat[selectedStat] && (
            <div className="p-6 bg-slate-900/50 border-t border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-3">
                💡 Insights de {statNames[selectedStat]}:
              </h3>
              <div className="space-y-2 text-sm">
                {(() => {
                  const bestScore = data.by_stat[selectedStat]?.reduce((max, curr) => 
                    curr.accuracy > max.accuracy ? curr : max
                  );
                  const worstScore = data.by_stat[selectedStat]?.reduce((min, curr) => 
                    curr.accuracy < min.accuracy ? curr : min
                  );
                  
                  return (
                    <>
                      {bestScore && (
                        <p className="text-green-400">
                          ✅ <strong>Mejor Score:</strong> {bestScore.score}/12 con {bestScore.accuracy.toFixed(1)}% de accuracy
                          {bestScore.accuracy >= 80 && ' (¡Excelente para apostar!)'}
                        </p>
                      )}
                      {worstScore && (
                        <p className="text-red-400">
                          ❌ <strong>Peor Score:</strong> {worstScore.score}/12 con {worstScore.accuracy.toFixed(1)}% de accuracy
                          {worstScore.accuracy < 50 && ' (Evitar apostar)'}
                        </p>
                      )}
                      <p className="text-slate-400">
                        📊 <strong>Recomendación:</strong> Apostar solo en scores ≥ 8 para {statNames[selectedStat]}
                      </p>
                    </>
                  );
                })()}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Nota explicativa */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
        <h4 className="text-blue-400 font-semibold mb-3 flex items-center gap-2">
          ℹ️ Cómo interpretar este dashboard:
        </h4>
        <div className="space-y-2 text-sm text-slate-300">
          <p>• <strong>Score H2H:</strong> Número de veces (de 12 max) que la predicción acertó en enfrentamientos históricos</p>
          <p>• <strong>Accuracy %:</strong> Porcentaje de acierto real cuando el score H2H era ese valor</p>
          <p>• <strong>Uso práctico:</strong> Si ves un partido con score 11/12 en corners, significa que históricamente esa predicción ha acertado 11 de 12 veces</p>
          <p>• <strong>Estrategia:</strong> Apostar solo en scores altos (≥8) con accuracy ≥70% para ser rentable</p>
        </div>
      </div>
    </div>
  );
}