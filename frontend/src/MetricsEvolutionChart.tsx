import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import BestBetsAnalysis from './BestBetsAnalysis';

// Interfaces de TypeScript
interface MetricData {
  period: number | string;
  period_start?: string;
  period_end?: string;
  total_matches: number;
  acc_1x2_pct: number | null;
  acc_over25_pct: number | null;
  acc_btts_pct: number | null;
  avg_rmse: number | null;
}

interface EvolutionData {
  window_type: string;
  poisson: MetricData[];
  weinston: MetricData[];
}

interface ChartDataPoint {
  period: number | string;
  period_label: string;
  poisson_1x2: number | null;
  weinston_1x2: number | null;
  poisson_over25: number | null;
  weinston_over25: number | null;
  poisson_btts: number | null;
  weinston_btts: number | null;
  poisson_rmse: number | null;
  weinston_rmse: number | null;
  total_matches: number;
}

interface Filters {
  season_id: number;
  date_from: string;
  date_to: string;
}

interface MetricOption {
  value: string;
  label: string;
  suffix: string;
}

interface WindowOption {
  value: string;
  label: string;
}

interface Trend {
  diff: number;
  isUp: boolean;
}

export default function MetricsEvolutionChart() {
  // 🎯 NUEVO: State para tabs
  const [activeTab, setActiveTab] = useState<'metrics' | 'best-bets'>('metrics');
  
  const [data, setData] = useState<EvolutionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedMetric, setSelectedMetric] = useState<string>('acc_1x2_pct');
  const [windowType, setWindowType] = useState<string>('gameweek');
  
  const [filters] = useState<Filters>({
    season_id: 2,
    date_from: '2025-08-15',
    date_to: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    // Solo fetch evolution si estamos en tab de metrics
    if (activeTab === 'metrics') {
      fetchEvolution();
    }
  }, [filters, windowType, activeTab]);

  const fetchEvolution = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        season_id: filters.season_id.toString(),
        window_type: windowType
      });
      
      if (filters.date_from) {
        params.append('date_from', filters.date_from);
      }
      if (filters.date_to) {
        params.append('date_to', filters.date_to);
      }
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/predictions/evolution?${params}`);
      const result: EvolutionData = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching evolution:', error);
    } finally {
      setLoading(false);
    }
  };

  // 🎯 Si estamos en tab de Best Bets, renderizar solo ese componente
  if (activeTab === 'best-bets') {
    return (
      <div className="min-h-screen bg-slate-900 p-6">
        {/* Header con tabs */}
        <div className="max-w-7xl mx-auto mb-6">
          <div className="flex gap-4 border-b border-slate-700">
            <button
              onClick={() => setActiveTab('metrics')}
              className="px-6 py-3 font-semibold transition-colors text-slate-400 hover:text-white"
            >
              📈 Evolución de Métricas
            </button>
            <button
              onClick={() => setActiveTab('best-bets')}
              className="px-6 py-3 font-semibold transition-colors text-white border-b-2 border-green-500"
            >
              🎯 Análisis de Best Bets
            </button>
          </div>
        </div>

        {/* Contenido de Best Bets */}
        <BestBetsAnalysis />
      </div>
    );
  }

  // 🎯 A partir de aquí es el contenido de Métricas (cuando activeTab === 'metrics')
  
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-slate-400">Cargando evolución...</div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-900 p-6">
        <div className="text-slate-400">No hay datos disponibles</div>
      </div>
    );
  }

  // Combinar datos para la gráfica
  const chartData: ChartDataPoint[] = (data.poisson || []).map((p, idx) => {
    const w = data.weinston[idx] || {} as MetricData;
    return {
      period: p.period,
      period_label: `${p.period_start?.slice(5) || p.period}`,
      poisson_1x2: p.acc_1x2_pct,
      weinston_1x2: w.acc_1x2_pct,
      poisson_over25: p.acc_over25_pct,
      weinston_over25: w.acc_over25_pct,
      poisson_btts: p.acc_btts_pct,
      weinston_btts: w.acc_btts_pct,
      poisson_rmse: p.avg_rmse,
      weinston_rmse: w.avg_rmse,
      total_matches: p.total_matches
    };
  });

  const metrics: MetricOption[] = [
    { value: 'acc_1x2_pct', label: 'Acierto 1X2 (%)', suffix: '%' },
    { value: 'acc_over25_pct', label: 'Acierto O/U 2.5 (%)', suffix: '%' },
    { value: 'acc_btts_pct', label: 'Acierto BTTS (%)', suffix: '%' },
    { value: 'rmse', label: 'RMSE Goles', suffix: '' }
  ];

  const windows: WindowOption[] = [
    { value: 'gameweek', label: 'Por Jornada (~10 partidos)' },
    { value: 'rolling_5', label: 'Últimos 5 partidos' },
    { value: 'rolling_10', label: 'Últimos 10 partidos' },
    { value: 'weekly', label: 'Por Semana' },
    { value: 'monthly', label: 'Por Mes' }
  ];

  const currentMetric = metrics.find(m => `acc_${selectedMetric}` === `acc_${m.value}` || selectedMetric === m.value);
  const metricLabel = currentMetric?.label || 'Métrica';
  const suffix = currentMetric?.suffix || '';

  // Calcular tendencia
  const getTrend = (dataKey: string): Trend | null => {
    if (chartData.length < 2) return null;
    const last = chartData[chartData.length - 1]?.[dataKey as keyof ChartDataPoint] as number | null;
    const prev = chartData[chartData.length - 2]?.[dataKey as keyof ChartDataPoint] as number | null;
    if (!last || !prev) return null;
    const diff = last - prev;
    return { diff, isUp: diff > 0 };
  };

  const poissonTrend = getTrend(`poisson_${selectedMetric.replace('acc_', '').replace('_pct', '')}`);
  const weinstonTrend = getTrend(`weinston_${selectedMetric.replace('acc_', '').replace('_pct', '')}`);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      {/* 🎯 Header con tabs */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex gap-4 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('metrics')}
            className="px-6 py-3 font-semibold transition-colors text-white border-b-2 border-blue-500"
          >
            📈 Evolución de Métricas
          </button>
          <button
            onClick={() => setActiveTab('best-bets')}
            className="px-6 py-3 font-semibold transition-colors text-slate-400 hover:text-white"
          >
            🎯 Análisis de Best Bets
          </button>
        </div>
      </div>

      {/* Contenido de Métricas */}
      <div className="w-full max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-6 shadow-xl">
          <h1 className="text-3xl font-bold text-white mb-2">
            📈 Evolución de Métricas
          </h1>
          <p className="text-slate-300">
            Analiza el comportamiento de los modelos a lo largo del tiempo
          </p>
        </div>

        {/* Controles */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Selector de Métrica */}
          <div className="bg-slate-800 rounded-lg p-4">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Métrica a Visualizar
            </label>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="w-full bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {metrics.map(m => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Ventana */}
          <div className="bg-slate-800 rounded-lg p-4">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Tipo de Ventana Temporal
            </label>
            <select
              value={windowType}
              onChange={(e) => setWindowType(e.target.value)}
              className="w-full bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {windows.map(w => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Indicadores de Tendencia */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-800 rounded-lg p-4 border border-blue-500/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-400">Poisson - Tendencia</div>
                <div className="text-2xl font-bold text-blue-400">
                  {(() => {
                    const value = chartData[chartData.length - 1]?.[`poisson_${selectedMetric.replace('acc_', '').replace('_pct', '')}` as keyof ChartDataPoint] as number | null;
                    return value != null ? value.toFixed(1) : 'N/A';
                  })()}{suffix}
                </div>
              </div>
              {poissonTrend && (
                <div className={`flex items-center gap-1 text-lg font-bold ${poissonTrend.isUp ? 'text-green-400' : 'text-red-400'}`}>
                  {poissonTrend.isUp ? '↗' : '↘'}
                  {Math.abs(poissonTrend.diff).toFixed(1)}{suffix}
                </div>
              )}
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-4 border border-orange-500/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-400">Weinston - Tendencia</div>
                <div className="text-2xl font-bold text-orange-400">
                  {(() => {
                    const value = chartData[chartData.length - 1]?.[`weinston_${selectedMetric.replace('acc_', '').replace('_pct', '')}` as keyof ChartDataPoint] as number | null;
                    return value != null ? value.toFixed(1) : 'N/A';
                  })()}{suffix}
                </div>
              </div>
              {weinstonTrend && (
                <div className={`flex items-center gap-1 text-lg font-bold ${weinstonTrend.isUp ? 'text-green-400' : 'text-red-400'}`}>
                  {weinstonTrend.isUp ? '↗' : '↘'}
                  {Math.abs(weinstonTrend.diff).toFixed(1)}{suffix}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Gráfica */}
        <div className="bg-slate-800 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4">{metricLabel}</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="period_label" 
                stroke="#9CA3AF"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="#9CA3AF"
                style={{ fontSize: '12px' }}
                domain={selectedMetric.includes('rmse') ? ['auto', 'auto'] : [0, 100]}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#e2e8f0' }}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey={`poisson_${selectedMetric.replace('acc_', '').replace('_pct', '')}`}
                name="Poisson"
                stroke="#3b82f6" 
                strokeWidth={3}
                dot={{ fill: '#3b82f6', r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line 
                type="monotone" 
                dataKey={`weinston_${selectedMetric.replace('acc_', '').replace('_pct', '')}`}
                name="Weinston"
                stroke="#f97316" 
                strokeWidth={3}
                dot={{ fill: '#f97316', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Tabla de Datos */}
        <div className="bg-slate-800 rounded-lg p-6 overflow-x-auto">
          <h3 className="text-lg font-bold text-white mb-4">Datos Detallados</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left text-slate-400 p-2">Período</th>
                <th className="text-right text-slate-400 p-2">Partidos</th>
                <th className="text-right text-blue-400 p-2">Poisson</th>
                <th className="text-right text-orange-400 p-2">Weinston</th>
                <th className="text-right text-slate-400 p-2">Diferencia</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((row, idx) => {
                const pValue = row[`poisson_${selectedMetric.replace('acc_', '').replace('_pct', '')}` as keyof ChartDataPoint] as number | null;
                const wValue = row[`weinston_${selectedMetric.replace('acc_', '').replace('_pct', '')}` as keyof ChartDataPoint] as number | null;
                const diff = (wValue || 0) - (pValue || 0);
                
                return (
                  <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="text-white p-2">{row.period_label}</td>
                    <td className="text-slate-300 text-right p-2">{row.total_matches}</td>
                    <td className="text-blue-300 text-right p-2 font-mono">
                      {pValue != null ? pValue.toFixed(1) : 'N/A'}{suffix}
                    </td>
                    <td className="text-orange-300 text-right p-2 font-mono">
                      {wValue != null ? wValue.toFixed(1) : 'N/A'}{suffix}
                    </td>
                    <td className={`text-right p-2 font-mono font-bold ${diff > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {diff > 0 ? '+' : ''}{diff.toFixed(1)}{suffix}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}