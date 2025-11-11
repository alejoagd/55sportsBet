// ============================================================================
// COMPONENTE: BestBetsAnalysis.tsx
// Análisis completo de las "Mejores Apuestas" con ROI
// Versión unificada con mejor manejo de errores
// ============================================================================

import { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Target, Award, CheckCircle, XCircle } from 'lucide-react';

interface GeneralStats {
  total_bets: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
  total_profit_loss: number;
  roi_pct: number;
}

interface TypeStats {
  bet_type: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  profit_loss: number;
  roi_pct: number;
}

interface ModelStats {
  model: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  profit_loss: number;
  roi_pct: number;
}

interface RankStats {
  rank: number;
  total: number;
  hits: number;
  accuracy_pct: number;
  avg_confidence: number;
  avg_score: number;
  profit_loss: number;
  roi_pct: number;
}

interface EvolutionPoint {
  week: string;
  total: number;
  hits: number;
  accuracy_pct: number;
  profit_loss: number;
  roi_pct: number;
}

interface BestBetsStats {
  general: GeneralStats;
  by_type: TypeStats[];
  by_model: ModelStats[];
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
  const [seasonId] = useState(2);
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
      console.log('📊 Fetching stats...');
      const response = await fetch(
        `http://localhost:8000/api/best-bets/stats?season_id=${seasonId}`
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
      
      console.log('📋 Fetching history...');
      const response = await fetch(
        `http://localhost:8000/api/best-bets/history?season_id=${seasonId}&limit=50${validatedParam}`
      );
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ History:', data.length, 'registros');
        setHistory(data);
      }
    } catch (error) {
      console.error('❌ Error fetching history:', error);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/best-bets/validate?season_id=${seasonId}`,
        { method: 'POST' }
      );
      const result = await response.json();
      
      alert(`✅ Validación completada:\n- Validadas: ${result.validated}\n- Aciertos: ${result.hits}\n- Fallos: ${result.misses}\n- Accuracy: ${result.accuracy}%`);
      
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
      'BTTS': 'BTTS',
      '1X2': '1X2'
    };
    return labels[type] || type;
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

  const { general, by_type, by_model, by_rank, evolution } = stats;

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
          <button
            onClick={handleValidate}
            disabled={validating}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded-lg transition-colors font-semibold flex items-center gap-2"
          >
            {validating ? '⏳ Validando...' : '🔄 Validar Resultados'}
          </button>
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
            Stake: $10 por apuesta
          </div>
        </div>

        {/* ROI */}
        <div className={`rounded-lg p-6 border ${
          general.roi_pct >= 0 
            ? 'bg-green-900/20 border-green-500/30' 
            : 'bg-red-900/20 border-red-500/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">ROI</span>
            {general.roi_pct >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-400" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-400" />
            )}
          </div>
          <div className={`text-3xl font-bold ${general.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {general.roi_pct >= 0 ? '+' : ''}{general.roi_pct.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Inversión total: ${(general.total_bets * 10).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Por Tipo de Apuesta */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 className="text-xl font-bold text-white mb-4">📊 Rendimiento por Tipo de Apuesta</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left text-slate-400 p-3">Tipo</th>
                <th className="text-right text-slate-400 p-3">Total</th>
                <th className="text-right text-slate-400 p-3">Aciertos</th>
                <th className="text-right text-slate-400 p-3">Accuracy</th>
                <th className="text-right text-slate-400 p-3">Ganancia</th>
                <th className="text-right text-slate-400 p-3">ROI</th>
              </tr>
            </thead>
            <tbody>
              {by_type.map((type) => (
                <tr key={type.bet_type} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="text-white p-3 font-medium">{getBetTypeLabel(type.bet_type)}</td>
                  <td className="text-slate-300 text-right p-3">{type.total}</td>
                  <td className="text-green-300 text-right p-3">{type.hits}</td>
                  <td className="text-right p-3">
                    <span className={`font-bold ${
                      type.accuracy_pct >= 70 ? 'text-green-400' :
                      type.accuracy_pct >= 60 ? 'text-yellow-400' :
                      'text-orange-400'
                    }`}>
                      {type.accuracy_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td className={`text-right p-3 font-bold ${type.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(type.profit_loss)}
                  </td>
                  <td className={`text-right p-3 font-bold ${type.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {type.roi_pct >= 0 ? '+' : ''}{type.roi_pct.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Grid: Por Modelo + Por Ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Por Modelo */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-xl font-bold text-white mb-4">🎯 Por Modelo</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={by_model}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="model" 
                stroke="#9CA3AF" 
                style={{ fontSize: '12px', textTransform: 'capitalize' }} 
              />
              <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                labelStyle={{ color: '#e2e8f0', textTransform: 'capitalize' }}
              />
              <Legend />
              <Bar dataKey="accuracy_pct" name="Accuracy (%)" fill="#10b981" />
              <Bar dataKey="roi_pct" name="ROI (%)" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
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
                    <div className={`text-2xl font-bold ${
                      rank.accuracy_pct >= 70 ? 'text-green-400' :
                      rank.accuracy_pct >= 60 ? 'text-yellow-400' :
                      'text-orange-400'
                    }`}>
                      {rank.accuracy_pct.toFixed(1)}%
                    </div>
                    <div className={`text-xs font-bold ${rank.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ROI: {rank.roi_pct >= 0 ? '+' : ''}{rank.roi_pct.toFixed(1)}%
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
              <div key={bet.id} className={`rounded-lg p-4 border ${
                bet.hit === null ? 'bg-slate-900/30 border-slate-700' :
                bet.hit ? 'bg-green-900/20 border-green-500/30' :
                'bg-red-900/20 border-red-500/30'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center text-slate-900 font-bold text-sm">
                        #{bet.rank}
                      </div>
                      <div>
                        <div className="text-white font-semibold">
                          {bet.home_team} vs {bet.away_team}
                        </div>
                        <div className="text-slate-400 text-xs">
                          {new Date(bet.date).toLocaleDateString('es-ES', { 
                            weekday: 'short', day: '2-digit', month: 'short' 
                          })}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-slate-400 text-xs">Apuesta</div>
                        <div className="text-white font-semibold">
                          {bet.prediction} ({getBetTypeLabel(bet.bet_type)})
                        </div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Modelo</div>
                        <div className="text-white capitalize">{bet.model}</div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Confianza</div>
                        <div className="text-white">{(bet.confidence * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-slate-400 text-xs">Odds</div>
                        <div className="text-white">{bet.odds?.toFixed(2) || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    {bet.hit === null ? (
                      <div className="text-slate-400">⏳ Pendiente</div>
                    ) : bet.hit ? (
                      <div>
                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-1" />
                        <div className="text-green-400 font-bold text-lg">
                          {formatCurrency(bet.profit_loss || 0)}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <XCircle className="w-8 h-8 text-red-400 mx-auto mb-1" />
                        <div className="text-red-400 font-bold text-lg">
                          {formatCurrency(bet.profit_loss || 0)}
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