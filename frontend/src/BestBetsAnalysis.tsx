// ============================================================================
// COMPONENTE: BestBetsAnalysis.tsx
// Análisis completo de las "Mejores Apuestas" con ROI
// Versión unificada con mejor manejo de errores
// ============================================================================

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Target, Award, CheckCircle, XCircle } from 'lucide-react';
import { AdminOnly } from './AdminButton';

// Por debajo de esto, un % (accuracy o ROI) se marca visualmente como poco confiable —
// una sola apuesta acertada mostrando "100%" no es una tendencia.
const LOW_SAMPLE_THRESHOLD = 10;

interface GeneralStats {
  total_bets: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
  total_profit_loss: number;
  with_odds: number;
  roi_pct: number | null;
}

interface TypeStats {
  bet_type: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  profit_loss: number | null;
  with_odds: number;
  roi_pct: number | null;
}

interface ModelStats {
  model: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  profit_loss: number | null;
  with_odds: number;
  roi_pct: number | null;
}

interface ModelTypeStats {
  model: string;
  bet_type: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  profit_loss: number | null;
  with_odds: number;
  roi_pct: number | null;
}

interface RankStats {
  rank: number;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
  profit_loss: number | null;
  with_odds: number;
  roi_pct: number | null;
}

interface EvolutionPoint {
  week: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  profit_loss: number | null;
  with_odds: number;
  roi_pct: number | null;
}

interface BestBetsStats {
  general: GeneralStats;
  by_type: TypeStats[];
  by_model: ModelStats[];
  by_model_type: ModelTypeStats[];
  by_rank: RankStats[];
  evolution: EvolutionPoint[];
}

interface HistoryBet {
  id: number;
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
  rank: number;
  odds: number | null;
  actual_result: string | null;
  hit: boolean | null;
  home_goals: number | null;
  away_goals: number | null;
  profit_loss: number | null;
}

export default function BestBetsAnalysis() {
  const [stats, setStats] = useState<BestBetsStats | null>(null);
  const [history, setHistory] = useState<HistoryBet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  // ✅ REMOVIDO: const [seasonId] = useState(2); - Ahora es MULTILIGA
  const [showHistory, setShowHistory] = useState<'all' | 'validated' | 'pending'>('validated');

  useEffect(() => {
    console.log('🎯 BestBetsAnalysis montado');
    fetchStats();
    fetchHistory();
  }, [showHistory]);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('📊 Fetching stats (MULTILIGA)...');
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // ✅ CORREGIDO: Sin season_id para obtener datos de TODAS las ligas
      const response = await fetch(
        `${API_URL}/api/best-bets/stats`
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('✅ Stats recibidas:', data);
      setStats(data);
    } catch (error) {
      console.error('❌ Error fetching stats:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const validatedParam = showHistory === 'all' ? '' : 
                            showHistory === 'validated' ? '&validated=true' : 
                            '&validated=false';
      
      console.log('📋 Fetching history (MULTILIGA)...');
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // ✅ CORREGIDO: Sin season_id para obtener datos de TODAS las ligas
      const response = await fetch(
        `${API_URL}/api/best-bets/history?limit=50${validatedParam}`
      );
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ History:', data.length, 'registros (multiliga)');
        setHistory(data);
      }
    } catch (error) {
      console.error('❌ Error fetching history:', error);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // ✅ CORREGIDO: Sin season_id para validar TODAS las ligas
      const response = await fetch(
        `${API_URL}/api/best-bets/validate`,
        { method: 'POST' }
      );
      const result = await response.json();
      
      alert(`✅ Validación completada (MULTILIGA):\n- Validadas: ${result.validated}\n- Aciertos: ${result.hits}\n- Fallos: ${result.misses}\n- Accuracy: ${result.accuracy}%`);
      
      fetchStats();
      fetchHistory();
    } catch (error) {
      console.error('Error validating:', error);
      alert('❌ Error al validar best bets');
    } finally {
      setValidating(false);
    }
  };

  const formatCurrency = (value: number) => {
    return `$${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
  };

  const getBetTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'OVER_25': 'Over/Under 2.5',
      'OVER_UNDER': 'Over/Under (líneas)',
      'BTTS': 'BTTS',
      '1X2': '1X2',
      'CORNERS': 'Corners',
      'SHOTS': 'Tiros',
      'SHOTS_ON_TARGET': 'Tiros a puerta',
      'CARDS': 'Tarjetas',
      'FOULS': 'Faltas'
    };
    return labels[type] || type;
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

  // 🎯 LOADING STATE
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-slate-900">
        <div className="text-center">
          <div className="text-slate-400 text-xl mb-4">⏳ Cargando análisis...</div>
          <div className="text-slate-500 text-sm">Consultando base de datos...</div>
        </div>
      </div>
    );
  }

  // 🎯 ERROR STATE
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96 bg-slate-900 p-6">
        <div className="max-w-2xl w-full">
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
            <h2 className="text-red-400 text-2xl font-bold mb-4">❌ Error al cargar datos</h2>
            <div className="text-red-300 mb-4 font-mono text-sm bg-red-950/50 p-3 rounded">
              {error}
            </div>
            
            <div className="bg-slate-800 rounded p-4 text-sm text-slate-300 mb-4">
              <p className="font-semibold mb-2">💡 Posibles causas:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>La tabla <code className="bg-slate-700 px-1 rounded">best_bets_history</code> no existe</li>
                <li>El endpoint <code className="bg-slate-700 px-1 rounded">/api/best-bets/stats</code> no está implementado</li>
                <li>Error en el backend (revisar logs)</li>
              </ul>
            </div>

            <div className="bg-blue-900/20 border border-blue-500/30 rounded p-4 text-sm text-blue-300 mb-4">
              <p className="font-semibold mb-2">🔧 Soluciones:</p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Ejecutar: <code className="bg-blue-950/50 px-1 rounded">create_best_bets_tracking.sql</code></li>
                <li>Verificar que los endpoints estén en <code className="bg-blue-950/50 px-1 rounded">api.py</code></li>
                <li>Reiniciar el backend</li>
              </ol>
            </div>

            <div className="flex gap-3">
              <button
                onClick={fetchStats}
                className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-semibold"
              >
                🔄 Reintentar
              </button>
              <button
                onClick={() => window.open('http://localhost:8000/api/best-bets/stats?season_id=2', '_blank')}
                className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm"
              >
                🔗 Abrir Endpoint
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 🎯 NO DATA STATE
  if (!stats || stats.general.total_bets === 0) {
    return (
      <div className="flex items-center justify-center min-h-96 bg-slate-900 p-6">
        <div className="max-w-2xl w-full">
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-6 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h2 className="text-yellow-400 text-2xl font-bold mb-4">No hay datos aún</h2>
            <p className="text-slate-300 mb-6">
              Aún no se han guardado "Best Bets" para analizar.
            </p>
            
            <div className="bg-slate-800 rounded p-4 text-sm text-slate-300 mb-6">
              <p className="font-semibold mb-3">📋 Pasos para generar datos:</p>
              <ol className="list-decimal text-left space-y-2 ml-6">
                <li>Ir a la sección <strong className="text-white">"Mejores Apuestas"</strong></li>
                <li>Click en el botón <strong className="text-white">"Actualizar"</strong></li>
                <li>Esperar a que se jueguen los partidos</li>
                <li>Regresar aquí y click en <strong className="text-white">"Validar Resultados"</strong></li>
              </ol>
            </div>

            <a
              href="/best-bets"
              className="inline-block px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors font-semibold"
            >
              🎯 Ir a Mejores Apuestas
            </a>
          </div>
        </div>
      </div>
    );
  }

  const { general, by_type, by_model, by_model_type, by_rank, evolution } = stats;
  const generalRoi = general.roi_pct;

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 rounded-lg p-6 shadow-xl border border-green-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="w-10 h-10 text-green-400" />
            <div>
              <h1 className="text-3xl font-bold text-white">
                📊 Análisis de Mejores Apuestas
              </h1>
              <p className="text-slate-300 text-sm">
                Rendimiento de las Top 4 recomendaciones
              </p>
            </div>
          </div>
          <AdminOnly hideCompletely={true}>
          <button
            onClick={handleValidate}
            disabled={validating}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded-lg transition-colors font-semibold flex items-center gap-2"
          >
            {validating ? '⏳ Validando...' : '🔄 Validar Resultados'}
          </button>
          </AdminOnly>
        </div>
      </div>

      {/* Resumen General */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Apuestas */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Total Apuestas</span>
            <Award className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-3xl font-bold text-white">{general.total_bets}</div>
          <div className="text-xs text-slate-400 mt-1">
            {general.hits} aciertos • {general.total_bets - general.hits} fallos
          </div>
        </div>

        {/* Accuracy */}
        <div className="bg-slate-800 rounded-lg p-6 border border-green-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Accuracy</span>
            <CheckCircle className="w-5 h-5 text-green-400" />
          </div>
          <div className="text-3xl font-bold text-green-400">
            {general.accuracy_pct.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Confianza promedio: {general.avg_confidence.toFixed(1)}%
          </div>
        </div>

        {/* Ganancia/Pérdida */}
        <div className={`rounded-lg p-6 border ${
          general.total_profit_loss >= 0
            ? 'bg-green-900/20 border-green-500/30'
            : 'bg-red-900/20 border-red-500/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Ganancia/Pérdida</span>
            <DollarSign className={`w-5 h-5 ${general.total_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`} />
          </div>
          <div className={`text-3xl font-bold ${general.total_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatCurrency(general.total_profit_loss)}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Sobre {general.with_odds} de {general.total_bets} apuestas con cuota registrada
          </div>
        </div>

        {/* ROI */}
        <div className={`rounded-lg p-6 border ${
          generalRoi === null ? 'bg-slate-800 border-slate-700' :
          generalRoi >= 0
            ? 'bg-green-900/20 border-green-500/30'
            : 'bg-red-900/20 border-red-500/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">ROI</span>
            {generalRoi === null ? null : generalRoi >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-400" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-400" />
            )}
          </div>
          <div className={`text-3xl font-bold ${
            generalRoi === null ? 'text-slate-500' : generalRoi >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {generalRoi === null ? 'N/D' : `${generalRoi >= 0 ? '+' : ''}${generalRoi.toFixed(1)}%`}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Inversión con cuota: ${(general.with_odds * 10).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Rentabilidad por Tipo de Apuesta */}
      {(() => {
        const withRoi = by_type.filter(t => t.roi_pct !== null) as (TypeStats & { roi_pct: number; profit_loss: number })[];
        const withoutRoi = by_type.filter(t => t.roi_pct === null);
        const ranked = [...withRoi].sort((a, b) => b.roi_pct - a.roi_pct);
        const maxAbsRoi = Math.max(1, ...ranked.map(t => Math.abs(t.roi_pct)));
        const reliable = ranked.filter(t => t.with_odds >= LOW_SAMPLE_THRESHOLD);
        const best = reliable[0] ?? ranked[0];
        const worst = reliable[reliable.length - 1] ?? ranked[ranked.length - 1];

        return (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-xl font-bold text-white">💰 Rentabilidad por Tipo de Apuesta</h2>
            </div>
            <p className="text-slate-400 text-xs mb-4">
              Ordenado de mejor a peor ROI. Solo se calcula sobre apuestas con cuota registrada. El número entre paréntesis es cuántas apuestas respaldan ese dato — menos de {LOW_SAMPLE_THRESHOLD} se marca como muestra baja.
            </p>

            {best && worst && best.bet_type !== worst.bet_type && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
                <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-2xl">🏆</span>
                  <div>
                    <div className="text-green-400 text-xs font-semibold">Más rentable</div>
                    <div className="text-white font-bold">{getBetTypeLabel(best.bet_type)}</div>
                    <div className="text-slate-400 text-[11px]">{best.with_odds} apuestas con cuota</div>
                  </div>
                  <div className="ml-auto text-green-400 font-bold text-lg">+{best.roi_pct.toFixed(1)}%</div>
                </div>
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div>
                    <div className="text-red-400 text-xs font-semibold">Evitar</div>
                    <div className="text-white font-bold">{getBetTypeLabel(worst.bet_type)}</div>
                    <div className="text-slate-400 text-[11px]">{worst.with_odds} apuestas con cuota</div>
                  </div>
                  <div className="ml-auto text-red-400 font-bold text-lg">{worst.roi_pct.toFixed(1)}%</div>
                </div>
              </div>
            )}

            <div className="space-y-2.5">
              {ranked.map((type) => {
                const barPct = (Math.abs(type.roi_pct) / maxAbsRoi) * 50;
                const isPositive = type.roi_pct >= 0;
                const lowSample = type.with_odds < LOW_SAMPLE_THRESHOLD;
                return (
                  <div key={type.bet_type} className={`flex items-center gap-3 text-sm ${lowSample ? 'opacity-60' : ''}`}>
                    <div className="w-32 sm:w-40 shrink-0 text-white font-medium truncate flex items-center gap-1">
                      {lowSample && <span title={`Muestra baja: solo ${type.with_odds} apuestas con cuota`}>⚠️</span>}
                      {getBetTypeLabel(type.bet_type)}
                    </div>
                    <div className="flex-1 h-6 relative bg-slate-900/50 rounded overflow-hidden">
                      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-600" />
                      <div
                        className={`absolute top-0 bottom-0 ${isPositive ? 'bg-green-500/70 left-1/2' : 'bg-red-500/70 right-1/2'}`}
                        style={{ width: `${barPct}%` }}
                      />
                    </div>
                    <div className={`w-24 shrink-0 text-right font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{type.roi_pct.toFixed(1)}% <span className="text-slate-500 font-normal">({type.with_odds})</span>
                    </div>
                    <div className={`w-14 shrink-0 text-right text-xs px-1.5 py-0.5 rounded ${getAccuracyBgColor(type.accuracy_pct)} ${getAccuracyColor(type.accuracy_pct)}`}>
                      {type.accuracy_pct.toFixed(0)}%
                    </div>
                  </div>
                );
              })}
            </div>

            {withoutRoi.length > 0 && (
              <div className="mt-5 pt-4 border-t border-slate-700">
                <div className="text-slate-400 text-xs font-semibold mb-2">Sin datos suficientes de cuota (se muestra solo accuracy):</div>
                <div className="flex flex-wrap gap-2">
                  {withoutRoi.map((type) => {
                    const lowSample = type.total < LOW_SAMPLE_THRESHOLD;
                    return (
                      <div key={type.bet_type} className={`bg-slate-900/50 rounded-lg px-3 py-1.5 flex items-center gap-2 text-xs ${lowSample ? 'opacity-60' : ''}`}>
                        {lowSample && <span title={`Muestra baja: solo ${type.total} apuestas`}>⚠️</span>}
                        <span className="text-slate-300">{getBetTypeLabel(type.bet_type)}</span>
                        <span className={`font-bold px-1.5 py-0.5 rounded ${getAccuracyBgColor(type.accuracy_pct)} ${getAccuracyColor(type.accuracy_pct)}`}>
                          {type.accuracy_pct.toFixed(0)}%
                        </span>
                        <span className="text-slate-500">({type.total})</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Matriz Modelo x Tipo de Apuesta */}
      {(() => {
        const models = Array.from(new Set(by_model_type.map(r => r.model))).sort();
        const betTypes = Array.from(new Set(by_model_type.map(r => r.bet_type)));
        const cell = (model: string, betType: string) =>
          by_model_type.find(r => r.model === model && r.bet_type === betType);

        return (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-1">🧩 Matriz Modelo × Tipo de Apuesta</h2>
            <p className="text-slate-400 text-xs mb-4">Accuracy de cada modelo por tipo de apuesta — el marco dorado es el modelo más acertivo en esa fila.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left text-slate-400 p-2">Tipo</th>
                    {models.map(m => (
                      <th key={m} className="text-center text-slate-400 p-2 capitalize">{m}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {betTypes.map((bt) => {
                    const cells = models.map(m => ({ model: m, data: cell(m, bt) }));
                    const bestAcc = Math.max(...cells.filter(c => c.data).map(c => c.data!.accuracy_pct));
                    return (
                      <tr key={bt} className="border-b border-slate-700/50">
                        <td className="text-white p-2 font-medium whitespace-nowrap">{getBetTypeLabel(bt)}</td>
                        {cells.map(({ model, data }) => (
                          <td key={model} className="p-2 text-center">
                            {!data ? (
                              <span className="text-slate-600 text-xs">—</span>
                            ) : (
                              <div
                                className={`inline-flex flex-col items-center rounded-lg px-2.5 py-1.5 ${getAccuracyBgColor(data.accuracy_pct)} ${data.accuracy_pct === bestAcc ? 'ring-2 ring-yellow-400' : ''} ${data.total < LOW_SAMPLE_THRESHOLD ? 'opacity-60' : ''}`}
                                title={data.total < LOW_SAMPLE_THRESHOLD ? `Muestra baja: solo ${data.total} apuestas` : undefined}
                              >
                                <span className={`font-bold ${getAccuracyColor(data.accuracy_pct)}`}>
                                  {data.total < LOW_SAMPLE_THRESHOLD && '⚠️ '}{data.accuracy_pct.toFixed(0)}%
                                </span>
                                <span className="text-[10px] text-slate-400">
                                  {data.total} ap. {data.roi_pct !== null && (
                                    <span className={data.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                                      · {data.roi_pct >= 0 ? '+' : ''}{data.roi_pct.toFixed(0)}%
                                    </span>
                                  )}
                                </span>
                              </div>
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}

      {/* Grid: Por Modelo + Por Ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Por Modelo */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-xl font-bold text-white mb-4">🎯 Por Modelo</h2>
          <div className="space-y-3">
            {(() => {
              const withRoi = by_model.filter(m => m.roi_pct !== null);
              const bestRoi = withRoi.length ? Math.max(...withRoi.map(m => m.roi_pct as number)) : null;
              return by_model.map((model) => (
                <div key={model.model} className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold capitalize">{model.model}</span>
                      {bestRoi !== null && model.roi_pct === bestRoi && (
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full font-bold">🏆 Más rentable</span>
                      )}
                    </div>
                    <span className="text-slate-400 text-xs">{model.total} apuestas</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className={`rounded-lg px-3 py-2 ${getAccuracyBgColor(model.accuracy_pct)}`}>
                      <div className="text-slate-400 text-xs mb-0.5">Accuracy</div>
                      <div className={`text-xl font-bold ${getAccuracyColor(model.accuracy_pct)}`}>{model.accuracy_pct.toFixed(1)}%</div>
                    </div>
                    <div className={`rounded-lg px-3 py-2 ${
                      model.roi_pct === null ? 'bg-slate-800' : model.roi_pct >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'
                    }`}>
                      <div className="text-slate-400 text-xs mb-0.5">ROI ({model.with_odds} c/cuota)</div>
                      <div className={`text-xl font-bold ${
                        model.roi_pct === null ? 'text-slate-500' : model.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {model.roi_pct === null ? 'N/D' : `${model.roi_pct >= 0 ? '+' : ''}${model.roi_pct.toFixed(1)}%`}
                      </div>
                    </div>
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>

        {/* Por Ranking */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-xl font-bold text-white mb-4">🏆 Por Ranking</h2>
          <div className="space-y-3">
            {by_rank.map((rank) => (
              <div key={rank.rank} className="bg-slate-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center text-slate-900 font-bold">
                      #{rank.rank}
                    </div>
                    <div>
                      <div className="text-white font-semibold">Posición {rank.rank}</div>
                      <div className="text-slate-400 text-xs">{rank.total} apuestas</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${getAccuracyColor(rank.accuracy_pct)}`}>
                      {rank.accuracy_pct.toFixed(1)}%
                    </div>
                    <div className={`text-xs font-bold ${
                      rank.roi_pct === null ? 'text-slate-500' : rank.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      ROI: {rank.roi_pct === null ? 'N/D' : `${rank.roi_pct >= 0 ? '+' : ''}${rank.roi_pct.toFixed(1)}%`}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Evolución Temporal */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 className="text-xl font-bold text-white mb-4">📈 Evolución Temporal</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={evolution}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="week" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
            <YAxis yAxisId="left" stroke="#9CA3AF" style={{ fontSize: '12px' }} domain={[0, 100]} />
            <YAxis yAxisId="right" orientation="right" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="accuracy_pct" 
              name="Accuracy (%)"
              stroke="#10b981" 
              strokeWidth={3}
              dot={{ fill: '#10b981', r: 4 }}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="roi_pct" 
              name="ROI (%)"
              stroke="#3b82f6" 
              strokeWidth={3}
              dot={{ fill: '#3b82f6', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Historial */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">📋 Historial de Apuestas</h2>
          <select
            value={showHistory}
            onChange={(e) => setShowHistory(e.target.value as any)}
            className="bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-2 text-sm"
          >
            <option value="validated">Validadas</option>
            <option value="pending">Pendientes</option>
            <option value="all">Todas</option>
          </select>
        </div>
        
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {history.length === 0 ? (
            <div className="text-center text-slate-400 py-8">
              No hay apuestas {showHistory === 'validated' ? 'validadas' : showHistory === 'pending' ? 'pendientes' : ''} aún
            </div>
          ) : (
            history.map((bet) => (
              <div key={bet.id} className={`rounded-lg p-3 sm:p-4 border ${
                bet.hit === null ? 'bg-slate-900/30 border-slate-700' :
                bet.hit ? 'bg-green-900/20 border-green-500/30' :
                'bg-red-900/20 border-red-500/30'
              }`}>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="flex-1 w-full">
                    <div className="flex items-center gap-2 sm:gap-3 mb-2">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 bg-yellow-500 rounded-full flex items-center justify-center text-slate-900 font-bold text-xs sm:text-sm flex-shrink-0">
                        #{bet.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-white font-semibold text-sm sm:text-base truncate">
                          {bet.home_team} vs {bet.away_team}
                        </div>
                        <div className="text-slate-400 text-xs">
                          {new Date(bet.date).toLocaleDateString('es-ES', {
                            weekday: 'short', day: '2-digit', month: 'short'
                          })}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 text-xs sm:text-sm">
                      <div>
                        <div className="text-slate-400 text-xs">Apuesta</div>
                        <div className="text-white font-semibold text-xs sm:text-sm truncate">
                          {bet.prediction}
                        </div>
                        <div className="text-slate-500 text-xs">({getBetTypeLabel(bet.bet_type)})</div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Modelo</div>
                        <div className="text-white capitalize text-xs sm:text-sm">{bet.model}</div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Confianza</div>
                        <div className="text-white text-xs sm:text-sm">{(bet.confidence * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Odds</div>
                        <div className="text-white text-xs sm:text-sm">{bet.odds?.toFixed(2) || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-center sm:text-right w-full sm:w-auto sm:ml-4 flex-shrink-0">
                    {bet.hit === null ? (
                      <div className="text-slate-400">⏳ Pendiente</div>
                    ) : bet.hit ? (
                      <div>
                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-1" />
                        <div className="text-green-400 font-bold text-lg">
                          {bet.profit_loss !== null ? formatCurrency(bet.profit_loss) : 'N/D'}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <XCircle className="w-8 h-8 text-red-400 mx-auto mb-1" />
                        <div className={`font-bold text-lg ${bet.profit_loss !== null ? 'text-red-400' : 'text-slate-500'}`}>
                          {bet.profit_loss !== null ? formatCurrency(bet.profit_loss) : 'N/D'}
                        </div>
                      </div>
                    )}
                    {bet.home_goals !== null && (
                      <div className="text-slate-400 text-xs mt-1">
                        {bet.home_goals}-{bet.away_goals}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Explicación */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="text-slate-300 text-sm space-y-2">
          <div className="font-semibold text-white mb-2">💡 Cómo se calcula el ROI</div>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><strong>Stake fijo:</strong> $10 por cada apuesta</li>
            <li><strong>Si acierta:</strong> Ganancia = (Odds - 1) × $10</li>
            <li><strong>Si falla:</strong> Pérdida = -$10</li>
            <li><strong>ROI:</strong> (Ganancia Total / Inversión Total) × 100</li>
            <li><strong className="text-yellow-400">N/D:</strong> esa apuesta no tiene una cuota registrada, así que no se puede calcular ganancia/pérdida real — el accuracy sigue siendo válido, solo falta el dato de cuota</li>
          </ul>
          <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded">
            <div className="text-blue-300 text-xs">
              <strong>Ejemplo:</strong> Si apuestas $100 (10 apuestas) y ganas $130, tu ROI es +30%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}