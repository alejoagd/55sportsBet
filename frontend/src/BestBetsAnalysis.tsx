// ============================================================================
// COMPONENTE: BestBetsAnalysis.tsx
// Efectividad histórica de las "Mejores Apuestas" — por modelo, tipo y liga
// Sin ROI: se enfoca en qué tan acertivo es cada corte, no en una
// simulación de ganancia en dinero (ver conversación 2026-09-12).
// ============================================================================

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Target, Award, CheckCircle, XCircle } from 'lucide-react';
import { AdminOnly } from './AdminButton';

// Por debajo de esto, un accuracy% se marca visualmente como poco confiable —
// una sola apuesta acertada mostrando "100%" no es una tendencia.
const LOW_SAMPLE_THRESHOLD = 10;

interface GeneralStats {
  total_bets: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
}

interface TypeStats {
  bet_type: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
}

interface ModelStats {
  model: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
}

interface ModelTypeStats {
  model: string;
  bet_type: string;
  total: number;
  hits: number;
  accuracy_pct: number;
}

interface LeagueStats {
  league: string;
  total: number;
  hits: number;
  accuracy_pct: number;
}

interface RankStats {
  rank: number;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
}

interface EvolutionPoint {
  week: string;
  total: number;
  hits: number;
  accuracy_pct: number;
}

interface BestBetsStats {
  general: GeneralStats;
  by_type: TypeStats[];
  by_model: ModelStats[];
  by_model_type: ModelTypeStats[];
  by_league: LeagueStats[];
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
}

export default function BestBetsAnalysis() {
  const [stats, setStats] = useState<BestBetsStats | null>(null);
  const [history, setHistory] = useState<HistoryBet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [showHistory, setShowHistory] = useState<'all' | 'validated' | 'pending'>('validated');

  useEffect(() => {
    fetchStats();
    fetchHistory();
  }, [showHistory]);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/best-bets/stats`);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error ${response.status}: ${errorText}`);
      }

      const data = await response.json();
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

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/best-bets/history?limit=50${validatedParam}`);

      if (response.ok) {
        const data = await response.json();
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
      const response = await fetch(`${API_URL}/api/best-bets/validate`, { method: 'POST' });
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

  const getAccuracyBarColor = (accuracy: number): string => {
    if (accuracy >= 70) return 'bg-green-500/70';
    if (accuracy >= 60) return 'bg-yellow-500/70';
    if (accuracy >= 50) return 'bg-orange-500/70';
    return 'bg-red-500/70';
  };

  // Elige el "mejor" de una lista priorizando muestra confiable (>= LOW_SAMPLE_THRESHOLD)
  // sobre un accuracy más alto pero basado en pocos datos.
  const pickBest = <T extends { total: number; accuracy_pct: number }>(items: T[]): T | undefined => {
    const reliable = items.filter(i => i.total >= LOW_SAMPLE_THRESHOLD);
    const pool = reliable.length ? reliable : items;
    return [...pool].sort((a, b) => b.accuracy_pct - a.accuracy_pct)[0];
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
            <div className="flex gap-3">
              <button
                onClick={fetchStats}
                className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-semibold"
              >
                🔄 Reintentar
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

  const { general, by_type, by_model, by_model_type, by_league, by_rank, evolution } = stats;
  const bestType = pickBest(by_type);
  const bestLeague = pickBest(by_league);

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 rounded-lg p-6 shadow-xl border border-green-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="w-10 h-10 text-green-400" />
            <div>
              <h1 className="text-3xl font-bold text-white">
                📊 Efectividad de Mejores Apuestas
              </h1>
              <p className="text-slate-300 text-sm">
                Qué tan acertivo ha sido cada modelo, tipo y liga en las Top 4 recomendaciones
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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

        <div className="bg-slate-800 rounded-lg p-6 border border-green-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Accuracy General</span>
            <CheckCircle className="w-5 h-5 text-green-400" />
          </div>
          <div className={`text-3xl font-bold ${getAccuracyColor(general.accuracy_pct)}`}>
            {general.accuracy_pct.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Confianza promedio del modelo: {general.avg_confidence.toFixed(1)}%
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Tipo más acertivo</span>
            <span className="text-lg">🎯</span>
          </div>
          {bestType ? (
            <>
              <div className="text-xl font-bold text-white truncate">{getBetTypeLabel(bestType.bet_type)}</div>
              <div className={`text-sm font-bold mt-1 ${getAccuracyColor(bestType.accuracy_pct)}`}>
                {bestType.accuracy_pct.toFixed(1)}% ({bestType.total} apuestas)
              </div>
            </>
          ) : <div className="text-slate-500">—</div>}
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Liga más acertiva</span>
            <span className="text-lg">🌍</span>
          </div>
          {bestLeague ? (
            <>
              <div className="text-xl font-bold text-white truncate">{bestLeague.league}</div>
              <div className={`text-sm font-bold mt-1 ${getAccuracyColor(bestLeague.accuracy_pct)}`}>
                {bestLeague.accuracy_pct.toFixed(1)}% ({bestLeague.total} apuestas)
              </div>
            </>
          ) : <div className="text-slate-500">—</div>}
        </div>
      </div>

      {/* Efectividad por Tipo de Apuesta */}
      {(() => {
        const ranked = [...by_type].sort((a, b) => b.accuracy_pct - a.accuracy_pct);
        const best = pickBest(by_type);
        const reliableSorted = ranked.filter(t => t.total >= LOW_SAMPLE_THRESHOLD);
        const worst = reliableSorted[reliableSorted.length - 1] ?? ranked[ranked.length - 1];

        return (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-1">🎯 Efectividad por Tipo de Apuesta</h2>
            <p className="text-slate-400 text-xs mb-4">
              Ordenado de mejor a peor accuracy. El número entre paréntesis es cuántas apuestas respaldan ese dato — menos de {LOW_SAMPLE_THRESHOLD} se marca como muestra baja.
            </p>

            {best && worst && best.bet_type !== worst.bet_type && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
                <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-2xl">🏆</span>
                  <div>
                    <div className="text-green-400 text-xs font-semibold">Más acertivo</div>
                    <div className="text-white font-bold">{getBetTypeLabel(best.bet_type)}</div>
                    <div className="text-slate-400 text-[11px]">{best.total} apuestas</div>
                  </div>
                  <div className="ml-auto text-green-400 font-bold text-lg">{best.accuracy_pct.toFixed(1)}%</div>
                </div>
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div>
                    <div className="text-red-400 text-xs font-semibold">Menos acertivo</div>
                    <div className="text-white font-bold">{getBetTypeLabel(worst.bet_type)}</div>
                    <div className="text-slate-400 text-[11px]">{worst.total} apuestas</div>
                  </div>
                  <div className="ml-auto text-red-400 font-bold text-lg">{worst.accuracy_pct.toFixed(1)}%</div>
                </div>
              </div>
            )}

            <div className="space-y-2.5">
              {ranked.map((type) => {
                const lowSample = type.total < LOW_SAMPLE_THRESHOLD;
                return (
                  <div key={type.bet_type} className={`flex items-center gap-3 text-sm ${lowSample ? 'opacity-60' : ''}`}>
                    <div className="w-32 sm:w-44 shrink-0 text-white font-medium truncate flex items-center gap-1">
                      {lowSample && <span title={`Muestra baja: solo ${type.total} apuestas`}>⚠️</span>}
                      {getBetTypeLabel(type.bet_type)}
                    </div>
                    <div className="flex-1 h-5 relative bg-slate-900/50 rounded overflow-hidden">
                      <div
                        className={`absolute left-0 top-0 bottom-0 ${getAccuracyBarColor(type.accuracy_pct)}`}
                        style={{ width: `${type.accuracy_pct}%` }}
                      />
                    </div>
                    <div className={`w-28 shrink-0 text-right font-bold ${getAccuracyColor(type.accuracy_pct)}`}>
                      {type.accuracy_pct.toFixed(1)}% <span className="text-slate-500 font-normal">({type.total})</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* Efectividad por Liga */}
      {by_league.length > 0 && (() => {
        const ranked = [...by_league].sort((a, b) => b.accuracy_pct - a.accuracy_pct);
        return (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-1">🌍 Efectividad por Liga</h2>
            <p className="text-slate-400 text-xs mb-4">
              Se agrupa por la liga actual del partido — no por la liga guardada cuando se generó la recomendación, para que siga siendo correcto si la temporada cambió de id.
            </p>
            <div className="space-y-2.5">
              {ranked.map((league) => {
                const lowSample = league.total < LOW_SAMPLE_THRESHOLD;
                return (
                  <div key={league.league} className={`flex items-center gap-3 text-sm ${lowSample ? 'opacity-60' : ''}`}>
                    <div className="w-32 sm:w-44 shrink-0 text-white font-medium truncate flex items-center gap-1">
                      {lowSample && <span title={`Muestra baja: solo ${league.total} apuestas`}>⚠️</span>}
                      {league.league}
                    </div>
                    <div className="flex-1 h-5 relative bg-slate-900/50 rounded overflow-hidden">
                      <div
                        className={`absolute left-0 top-0 bottom-0 ${getAccuracyBarColor(league.accuracy_pct)}`}
                        style={{ width: `${league.accuracy_pct}%` }}
                      />
                    </div>
                    <div className={`w-28 shrink-0 text-right font-bold ${getAccuracyColor(league.accuracy_pct)}`}>
                      {league.accuracy_pct.toFixed(1)}% <span className="text-slate-500 font-normal">({league.total})</span>
                    </div>
                  </div>
                );
              })}
            </div>
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
                                <span className="text-[10px] text-slate-400">{data.total} ap.</span>
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
              const bestModel = pickBest(by_model);
              return by_model.map((model) => (
                <div key={model.model} className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold capitalize">{model.model}</span>
                      {bestModel?.model === model.model && (
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full font-bold">🏆 Más acertivo</span>
                      )}
                    </div>
                    <span className="text-slate-400 text-xs">{model.total} apuestas</span>
                  </div>
                  <div className={`rounded-lg px-3 py-2 ${getAccuracyBgColor(model.accuracy_pct)}`}>
                    <div className="text-slate-400 text-xs mb-0.5">Accuracy</div>
                    <div className={`text-2xl font-bold ${getAccuracyColor(model.accuracy_pct)}`}>{model.accuracy_pct.toFixed(1)}%</div>
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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center text-slate-900 font-bold">
                      #{rank.rank}
                    </div>
                    <div>
                      <div className="text-white font-semibold">Posición {rank.rank}</div>
                      <div className="text-slate-400 text-xs">{rank.total} apuestas</div>
                    </div>
                  </div>
                  <div className={`text-2xl font-bold ${getAccuracyColor(rank.accuracy_pct)}`}>
                    {rank.accuracy_pct.toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Evolución Temporal */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 className="text-xl font-bold text-white mb-4">📈 Evolución del Accuracy</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={evolution}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="week" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
            <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Accuracy']}
            />
            <Line
              type="monotone"
              dataKey="accuracy_pct"
              name="Accuracy (%)"
              stroke="#10b981"
              strokeWidth={3}
              dot={{ fill: '#10b981', r: 4 }}
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
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-4 text-xs sm:text-sm">
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
                    </div>
                  </div>
                  <div className="text-center sm:text-right w-full sm:w-auto sm:ml-4 flex-shrink-0">
                    {bet.hit === null ? (
                      <div className="text-slate-400">⏳ Pendiente</div>
                    ) : bet.hit ? (
                      <div className="flex sm:flex-col items-center gap-1">
                        <CheckCircle className="w-8 h-8 text-green-400" />
                        <span className="text-green-400 font-bold text-sm">Acertó</span>
                      </div>
                    ) : (
                      <div className="flex sm:flex-col items-center gap-1">
                        <XCircle className="w-8 h-8 text-red-400" />
                        <span className="text-red-400 font-bold text-sm">Falló</span>
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
          <div className="font-semibold text-white mb-2">💡 Cómo leer el accuracy</div>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><strong>Accuracy:</strong> aciertos ÷ apuestas validadas de ese corte (tipo, modelo, liga, etc.), en %</li>
            <li><strong>Confianza:</strong> la probabilidad que el modelo le asignó a la predicción antes de saber el resultado</li>
            <li><strong className="text-yellow-400">⚠️ Muestra baja:</strong> menos de {LOW_SAMPLE_THRESHOLD} apuestas respaldan ese %, así que puede cambiar mucho con el próximo resultado — tómalo con cautela</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
