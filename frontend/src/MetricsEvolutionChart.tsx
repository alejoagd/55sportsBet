import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import BestBetsAnalysis from './BestBetsAnalysis';
import BettingLinesStats from './BettingLinesStats';
import i18n, { localeTag } from './i18n';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// ── WC 2026 Accuracy types ────────────────────────────────────────────────────
interface WCModelAcc { acc_1x2: number | null; acc_over25: number | null; acc_btts: number | null; }
interface WCDateRow  { date: string; total: number; poisson: WCModelAcc; weinston: WCModelAcc; }
interface WCAccuracy {
  total_matches: number;
  overall: { poisson: WCModelAcc; weinston: WCModelAcc };
  by_date: WCDateRow[];
}

// ── WC 2026 Accuracy View ─────────────────────────────────────────────────────
type WCMetricKey = 'acc_1x2' | 'acc_over25' | 'acc_btts';

function WC2026AccuracyView() {
  const [wc, setWc] = useState<WCAccuracy | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState<WCMetricKey>('acc_1x2');

  useEffect(() => {
    fetch(`${API_URL}/api/wc2026/accuracy`)
      .then(r => r.json())
      .then(d => { setWc(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400 text-center py-16">{i18n.t('evolution.cargandoMetricasDelMundial')}</div>;
  if (!wc || wc.total_matches === 0) return <div className="text-slate-500 text-center py-16">{i18n.t('evolution.sinPartidosCompletadosAun')}</div>;

  const metricKey = selectedMetric;
  const metricLabel = selectedMetric === 'acc_1x2' ? i18n.t('evolution.acierto1x2')
    : selectedMetric === 'acc_over25' ? i18n.t('evolution.aciertoOU25') : i18n.t('evolution.aciertoBtts');

  const chartData = wc.by_date.map(d => ({
    date: d.date.slice(5),
    total: d.total,
    poisson:  d.poisson[metricKey],
    weinston: d.weinston[metricKey],
  }));

  const allMetrics: { key: keyof WCModelAcc; label: string }[] = [
    { key: 'acc_1x2',   label: '1X2' },
    { key: 'acc_over25', label: 'O/U 2.5' },
    { key: 'acc_btts',  label: 'BTTS' },
  ];

  const metricButtons: { key: WCMetricKey; label: string }[] = [
    { key: 'acc_1x2', label: '1X2' },
    { key: 'acc_over25', label: 'O/U 2.5' },
    { key: 'acc_btts', label: 'BTTS' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-yellow-900/40 to-slate-900 border border-yellow-500/30 rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🏆</span>
            <div>
              <h2 className="text-xl font-black text-white">{i18n.t('evolution.mundial2026AciertosDePrediccion')}</h2>
              <p className="text-slate-400 text-sm">{i18n.t('evolution.completedGroup', { n: wc.total_matches })}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {metricButtons.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setSelectedMetric(key)}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
                  selectedMetric === key
                    ? 'bg-yellow-500 text-slate-900'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Resumen de las 3 métricas para ambos modelos */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {allMetrics.map(({ key, label }) => {
          const pv = wc.overall.poisson[key];
          const wv = wc.overall.weinston[key];
          const winner = pv != null && wv != null ? (pv > wv ? 'poisson' : wv > pv ? 'weinston' : 'tie') : null;
          return (
            <div key={key} className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="bg-slate-900/60 px-4 py-2 border-b border-slate-700">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wide">{label}</span>
              </div>
              <div className="p-4 grid grid-cols-2 gap-3">
                <div className={`text-center rounded-lg p-3 ${winner === 'poisson' ? 'bg-blue-500/20 ring-1 ring-blue-400' : 'bg-slate-700/40'}`}>
                  <div className="text-xs text-blue-400 font-semibold mb-1">Poisson</div>
                  <div className="text-2xl font-black text-blue-300">{pv != null ? `${pv.toFixed(1)}%` : 'N/A'}</div>
                  {winner === 'poisson' && <div className="text-[10px] text-yellow-400 mt-1">{i18n.t('evolution.mejor')}</div>}
                </div>
                <div className={`text-center rounded-lg p-3 ${winner === 'weinston' ? 'bg-orange-500/20 ring-1 ring-orange-400' : 'bg-slate-700/40'}`}>
                  <div className="text-xs text-orange-400 font-semibold mb-1">Weinston</div>
                  <div className="text-2xl font-black text-orange-300">{wv != null ? `${wv.toFixed(1)}%` : 'N/A'}</div>
                  {winner === 'weinston' && <div className="text-[10px] text-yellow-400 mt-1">{i18n.t('evolution.mejor')}</div>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Gráfico de evolución por fecha para la métrica seleccionada */}
      <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
        <h3 className="text-white font-bold mb-4">{i18n.t('evolution.byDate', { metric: metricLabel })}</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} barCategoryGap="30%">
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '11px' }} />
            <YAxis stroke="#9CA3AF" style={{ fontSize: '11px' }} domain={[0, 100]} tickFormatter={v => `${v}%`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
              formatter={(v: any) => v != null ? `${Number(v).toFixed(1)}%` : 'N/A'}
            />
            <Legend />
            <Bar dataKey="poisson"  name="Poisson"  fill="#3b82f6" radius={[4,4,0,0]} />
            <Bar dataKey="weinston" name="Weinston" fill="#f97316" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Tabla por fecha */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="bg-slate-900/60 px-5 py-3 border-b border-slate-700">
          <h3 className="text-white font-bold text-sm">{i18n.t('evolution.detallePorFecha')}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-900/40">
                <th className="text-left text-slate-400 px-4 py-2.5">{i18n.t('evolution.fecha')}</th>
                <th className="text-center text-slate-400 px-3 py-2.5">{i18n.t('evolution.partidos')}</th>
                <th className="text-center text-blue-400 px-3 py-2.5">Poisson 1X2</th>
                <th className="text-center text-orange-400 px-3 py-2.5">Weinston 1X2</th>
                <th className="text-center text-blue-400 px-3 py-2.5">Poisson O/U</th>
                <th className="text-center text-orange-400 px-3 py-2.5">Weinston O/U</th>
                <th className="text-center text-blue-400 px-3 py-2.5">Poisson BTTS</th>
                <th className="text-center text-orange-400 px-3 py-2.5">Weinston BTTS</th>
              </tr>
            </thead>
            <tbody>
              {wc.by_date.map((row) => (
                <tr key={row.date} className="border-b border-slate-700/40 hover:bg-slate-700/30">
                  <td className="text-white px-4 py-2.5 font-medium">{row.date}</td>
                  <td className="text-slate-400 text-center px-3 py-2.5">{row.total}</td>
                  {(['poisson','weinston'] as const).flatMap(model => [
                    <td key={`${row.date}-${model}-1x2`} className={`text-center px-3 py-2.5 font-mono font-bold ${model === 'poisson' ? 'text-blue-300' : 'text-orange-300'}`}>
                      {row[model].acc_1x2 != null ? `${row[model].acc_1x2}%` : '—'}
                    </td>
                  ]).concat(
                    (['poisson','weinston'] as const).flatMap(model => [
                      <td key={`${row.date}-${model}-ou`} className={`text-center px-3 py-2.5 font-mono font-bold ${model === 'poisson' ? 'text-blue-300' : 'text-orange-300'}`}>
                        {row[model].acc_over25 != null ? `${row[model].acc_over25}%` : '—'}
                      </td>
                    ])
                  ).concat(
                    (['poisson','weinston'] as const).flatMap(model => [
                      <td key={`${row.date}-${model}-btts`} className={`text-center px-3 py-2.5 font-mono font-bold ${model === 'poisson' ? 'text-blue-300' : 'text-orange-300'}`}>
                        {row[model].acc_btts != null ? `${row[model].acc_btts}%` : '—'}
                      </td>
                    ])
                  )}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-yellow-400/10 border-t-2 border-yellow-400/30">
                <td className="text-yellow-400 font-bold px-4 py-2.5">TOTAL</td>
                <td className="text-yellow-400 font-bold text-center px-3 py-2.5">{wc.total_matches}</td>
                <td className="text-blue-300 font-black text-center px-3 py-2.5">{wc.overall.poisson.acc_1x2 != null ? `${wc.overall.poisson.acc_1x2}%` : '—'}</td>
                <td className="text-orange-300 font-black text-center px-3 py-2.5">{wc.overall.weinston.acc_1x2 != null ? `${wc.overall.weinston.acc_1x2}%` : '—'}</td>
                <td className="text-blue-300 font-black text-center px-3 py-2.5">{wc.overall.poisson.acc_over25 != null ? `${wc.overall.poisson.acc_over25}%` : '—'}</td>
                <td className="text-orange-300 font-black text-center px-3 py-2.5">{wc.overall.weinston.acc_over25 != null ? `${wc.overall.weinston.acc_over25}%` : '—'}</td>
                <td className="text-blue-300 font-black text-center px-3 py-2.5">{wc.overall.poisson.acc_btts != null ? `${wc.overall.poisson.acc_btts}%` : '—'}</td>
                <td className="text-orange-300 font-black text-center px-3 py-2.5">{wc.overall.weinston.acc_btts != null ? `${wc.overall.weinston.acc_btts}%` : '—'}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

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
  period_full: string;
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

type EvolutionTab = 'metrics' | 'best-bets' | 'betting-lines' | 'wc2026';

// Una sola barra de tabs reusada por las 4 vistas de esta pantalla — antes
// cada una tenía su propia copia pegada a mano, y dos de ellas (Best Bets y
// Betting Lines) habían quedado con un estilo fijo más grande mientras las
// otras dos ya usaban el compacto responsivo, así que la barra "saltaba" de
// tamaño al cambiar de tab. Con un solo componente esto no puede volver a
// desalinearse entre pestañas.
// Claves de traducción (se resuelven al renderizar, no al cargar el módulo).
// fullKey: etiqueta completa para desktop; shortKey: etiqueta corta (mobile).
const EVOLUTION_TABS: { id: EvolutionTab; icon: string; fullKey?: string; shortKey: string; activeBorder: string }[] = [
  { id: 'metrics', icon: '📈', fullKey: 'evolution.tabMetricsFull', shortKey: 'evolution.tabMetrics', activeBorder: 'border-blue-500' },
  { id: 'best-bets', icon: '🎯', fullKey: 'evolution.tabBestBetsFull', shortKey: 'evolution.tabBestBets', activeBorder: 'border-green-500' },
  { id: 'betting-lines', icon: '📊', fullKey: 'evolution.tabLinesFull', shortKey: 'evolution.tabLines', activeBorder: 'border-blue-500' },
  // Pestaña del Mundial 2026 oculta: el torneo terminó (19 jul 2026). El código de
  // la vista (activeTab === 'wc2026') se conserva por si se reactiva; para volver a
  // mostrarla, descomentar esta línea y agregar 'wc2026' a VALID_EVOLUTION_TABS.
  // { id: 'wc2026', icon: '🏆', shortKey: 'evolution.tabWc', activeBorder: 'border-yellow-500' },
];

function EvolutionTabBar({ activeTab, setActiveTab }: { activeTab: EvolutionTab; setActiveTab: (t: EvolutionTab) => void }) {
  return (
    <div className="flex gap-2 sm:gap-4 border-b border-slate-700 overflow-x-auto scrollbar-hide">
      {EVOLUTION_TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`px-4 sm:px-6 py-2 sm:py-3 font-semibold transition-colors whitespace-nowrap text-sm sm:text-base ${
            activeTab === tab.id ? `text-white border-b-2 ${tab.activeBorder}` : 'text-slate-400 hover:text-white'
          }`}
        >
          {tab.icon}{' '}
          {tab.fullKey ? (
            <>
              <span className="hidden sm:inline">{i18n.t(tab.fullKey)}</span>
              <span className="sm:hidden">{i18n.t(tab.shortKey)}</span>
            </>
          ) : i18n.t(tab.shortKey)}
        </button>
      ))}
    </div>
  );
}

// 'wc2026' no está acá a propósito (pestaña oculta): un ?tab=wc2026 en la URL cae en 'metrics'.
const VALID_EVOLUTION_TABS: EvolutionTab[] = ['metrics', 'best-bets', 'betting-lines'];

// "2025-08-01 00:00:00-05" / "2025-08-31" -> Date local. Solo se usa el día: la hora y la
// zona horaria que trae la API para meses y semanas corrían o ensuciaban la etiqueta.
const parseDay = (s?: string | null): Date | null => {
  const m = s?.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
};
const fmtDay = (d: Date, opts: Intl.DateTimeFormatOptions) => d.toLocaleDateString(localeTag(), opts);
// Para el eje (poco espacio): "15 de ago de 25" -> "15 ago 25"
const compact = (t: string) => t.replace(/\s+de\s+/g, ' ').replace(/\./g, '');

// Etiquetas legibles del eje X y del tooltip, siempre con el año, según la agrupación.
function periodLabels(windowType: string, p: MetricData): { axis: string; full: string } {
  const start = parseDay(p.period_start);
  const end = parseDay(p.period_end) ?? start;
  if (!start || !end) return { axis: String(p.period), full: String(p.period) };

  const short = { day: 'numeric', month: 'short', year: '2-digit' } as const;
  const long = { day: 'numeric', month: 'short', year: 'numeric' } as const;
  // Rango "15 – 18 ago 2025" (o "28 ago – 3 sep 2025" si cruza de mes)
  const range = () => start.getTime() === end.getTime()
    ? fmtDay(end, long)
    : `${fmtDay(start, { day: 'numeric', month: 'short' })} – ${fmtDay(end, long)}`;

  if (windowType === 'monthly') {
    return {
      axis: compact(fmtDay(start, { month: 'short', year: 'numeric' })),   // ago 2025
      full: fmtDay(start, { month: 'long', year: 'numeric' }),    // agosto de 2025
    };
  }
  if (windowType === 'weekly') {
    return { axis: compact(fmtDay(start, short)), full: i18n.t('evolution.tipWeek', { range: range() }) };
  }
  if (windowType === 'gameweek') {
    return { axis: compact(fmtDay(start, short)), full: i18n.t('evolution.tipGameweek', { n: Math.round(Number(p.period)), range: range() }) };
  }
  // rolling_5 / rolling_10: ventana de los últimos N partidos que termina en esa fecha
  const n = Number(windowType.replace('rolling_', '')) || 0;
  return { axis: compact(fmtDay(end, short)), full: i18n.t('evolution.tipRolling', { n, date: fmtDay(end, long) }) };
}

export default function MetricsEvolutionChart() {
  // 🎯 Tab inicial: si llega ?tab=best-bets en la URL (ej. al volver de un
  // partido con returnPath), arranca ahí en vez de siempre en 'metrics'.
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab');
  const [activeTab, setActiveTab] = useState<EvolutionTab>(
    VALID_EVOLUTION_TABS.includes(initialTab as EvolutionTab) ? (initialTab as EvolutionTab) : 'metrics'
  );

  const [data, setData] = useState<EvolutionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [windowType, setWindowType] = useState<string>('gameweek');
  
  const [filters] = useState<Filters>({
    season_id: 2,
    date_from: '2025-08-15',
    date_to: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
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
      <div className="min-h-screen bg-slate-900 p-3 sm:p-6">
        <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
          <EvolutionTabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
        <BestBetsAnalysis />
      </div>
    );
  }

  // 🎯 Si estamos en tab de Betting Lines, renderizar ese componente
  if (activeTab === 'betting-lines') {
    return (
      <div className="min-h-screen bg-slate-900 p-3 sm:p-6">
        <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
          <EvolutionTabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
        <BettingLinesStats />
      </div>
    );
  }

  // 🎯 Si estamos en tab Mundial 2026
  if (activeTab === 'wc2026') {
    return (
      <div className="min-h-screen bg-slate-900 p-3 sm:p-6">
        <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
          <EvolutionTabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
        <div className="w-full max-w-7xl mx-auto">
          <WC2026AccuracyView />
        </div>
      </div>
    );
  }

  // 🎯 A partir de aquí es el contenido de Métricas (cuando activeTab === 'metrics')
  
  if (loading && !data) {
    return (
      <div className="min-h-screen bg-slate-900 p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-slate-400">{i18n.t('evolution.cargandoEvolucion')}</div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-900 p-6">
        <div className="text-slate-400">{i18n.t('evolution.noHayDatosDisponibles')}</div>
      </div>
    );
  }

  // Combinar datos para la gráfica
  const chartData: ChartDataPoint[] = (data.poisson || []).map((p, idx) => {
    const w = data.weinston[idx] || {} as MetricData;
    const labels = periodLabels(windowType, p);
    return {
      period: p.period,
      period_label: labels.axis,
      period_full: labels.full,
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

  // Un par de series (Poisson / Weinston) por cada métrica: las 4 se muestran a la
  // vez, cada una en su tarjeta, en vez de elegir una en un desplegable.
  const cards: MetricCardDef[] = [
    { key: '1x2', labelKey: 'evolution.acierto1x22', suffix: '%', higherIsBetter: true },
    { key: 'over25', labelKey: 'evolution.aciertoOU252', suffix: '%', higherIsBetter: true },
    { key: 'btts', labelKey: 'evolution.aciertoBtts2', suffix: '%', higherIsBetter: true },
    { key: 'rmse', labelKey: 'evolution.rmseGoles', suffix: '', higherIsBetter: false },
  ];

  return (
    <div className="min-h-screen bg-slate-900 p-2 sm:p-6">
      {/* 🎯 Header con tabs */}
      <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
        <EvolutionTabBar activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>

      {/* Contenido de Métricas */}
      <div className="w-full max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-5 sm:p-6 shadow-xl">
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-1">
            {i18n.t('evolution.evolucionDeMetricas')}</h1>
          <p className="text-slate-300 text-sm sm:text-base">
            {i18n.t('evolution.analizaElComportamientoDeLos')}</p>
        </div>

        {/* Leyenda + agrupación (botones, no desplegable) */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-4 text-sm font-semibold">
            <span className="flex items-center gap-1.5 text-blue-400"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" />Poisson</span>
            <span className="flex items-center gap-1.5 text-orange-400"><span className="h-2.5 w-2.5 rounded-full bg-orange-500" />Weinston</span>
          </div>
          <div className="flex min-w-0 items-center gap-2">
            <span className="hidden text-xs text-slate-500 sm:inline">{i18n.t('evolution.groupBy')}</span>
            <div className="flex gap-1 overflow-x-auto rounded-lg bg-slate-800 p-1 scrollbar-hide">
              {WINDOW_OPTIONS.map(w => (
                <button
                  key={w.value}
                  onClick={() => setWindowType(w.value)}
                  className={`flex-shrink-0 whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                    windowType === w.value ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-700 hover:text-white'
                  }`}
                >
                  {i18n.t(w.labelKey)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Las 4 métricas a la vez */}
        <div className={`grid grid-cols-1 gap-4 xl:grid-cols-2 transition-opacity ${loading ? 'opacity-50' : ''}`}>
          {cards.map(card => (
            <MetricCard key={card.key} def={card} data={chartData} windowType={windowType} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tarjeta de una métrica: último valor de cada modelo, su cambio frente al
//    período anterior, mini gráfica y quién lidera ───────────────────────────
type MetricCardDef = { key: '1x2' | 'over25' | 'btts' | 'rmse'; labelKey: string; suffix: string; higherIsBetter: boolean };

const WINDOW_OPTIONS = [
  { value: 'gameweek', labelKey: 'evolution.winGameweek' },
  { value: 'rolling_5', labelKey: 'evolution.winRolling5' },
  { value: 'rolling_10', labelKey: 'evolution.winRolling10' },
  { value: 'weekly', labelKey: 'evolution.winWeekly' },
  { value: 'monthly', labelKey: 'evolution.winMonthly' },
];

function MetricCard({ def, data, windowType }: { def: MetricCardDef; data: ChartDataPoint[]; windowType: string }) {
  const get = (row: ChartDataPoint, model: 'poisson' | 'weinston') =>
    row[`${model}_${def.key}` as keyof ChartDataPoint] as number | null;
  const decimals = def.key === 'rmse' ? 2 : 1;
  const fmt = (v: number) => `${v.toFixed(decimals)}${def.suffix}`;

  // Último y anterior valor REAL de cada serie (un 0 es un valor válido, no un hueco)
  const lastTwo = (model: 'poisson' | 'weinston') => {
    const vals = data.map(r => get(r, model)).filter((v): v is number => v != null);
    return { last: vals.length ? vals[vals.length - 1] : null, prev: vals.length > 1 ? vals[vals.length - 2] : null };
  };
  // Promedio ponderado por partidos de cada período
  const average = (model: 'poisson' | 'weinston') => {
    let num = 0, den = 0;
    for (const r of data) { const v = get(r, model); if (v != null) { num += v * r.total_matches; den += r.total_matches; } }
    return den ? num / den : null;
  };

  const models = [
    { id: 'poisson' as const, name: 'Poisson', color: '#3b82f6', text: 'text-blue-400', ...lastTwo('poisson'), avg: average('poisson') },
    { id: 'weinston' as const, name: 'Weinston', color: '#f97316', text: 'text-orange-400', ...lastTwo('weinston'), avg: average('weinston') },
  ];

  // Quién lidera en el promedio del período (en RMSE, el menor es el mejor)
  let leader: { name: string; gap: number } | null = null;
  if (models[0].avg != null && models[1].avg != null) {
    const diff = models[1].avg - models[0].avg;
    if (Math.abs(diff) >= 0.05) {
      const weinstonLeads = def.higherIsBetter ? diff > 0 : diff < 0;
      leader = { name: weinstonLeads ? 'Weinston' : 'Poisson', gap: Math.abs(diff) };
    }
  }

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold text-white">{i18n.t(def.labelKey)}</h3>
        {leader ? (
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${leader.name === 'Weinston' ? 'bg-orange-500/15 text-orange-300' : 'bg-blue-500/15 text-blue-300'}`}>
            {i18n.t('evolution.leadsBy', { model: leader.name, n: `${leader.gap.toFixed(decimals)}${def.suffix === '%' ? ` ${i18n.t('evolution.pts')}` : ''}` })}
          </span>
        ) : (
          <span className="rounded-full bg-slate-700 px-2.5 py-0.5 text-[11px] font-semibold text-slate-300">{i18n.t('evolution.tied')}</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {models.map(m => {
          const rawDiff = m.last != null && m.prev != null ? m.last - m.prev : null;
          // un cambio que se redondea a 0.0 / 0.00 no se muestra (sería "↘0.00")
          const diff = rawDiff != null && Number(Math.abs(rawDiff).toFixed(decimals)) !== 0 ? rawDiff : null;
          const improved = diff != null && (def.higherIsBetter ? diff > 0 : diff < 0);
          return (
            <div key={m.id} className="rounded-lg bg-slate-900/50 px-3 py-2">
              <div className="text-[11px] text-slate-400">{m.name}<span className="hidden sm:inline"> · {i18n.t('evolution.latest')}</span></div>
              <div className="flex items-baseline justify-between gap-2">
                <span className={`text-2xl font-bold ${m.text}`}>{m.last != null ? fmt(m.last) : 'N/A'}</span>
                {diff != null && (
                  <span className={`text-sm font-bold ${improved ? 'text-green-400' : 'text-red-400'}`} title={i18n.t('evolution.vsPrev')}>
                    {diff > 0 ? '↗' : '↘'}{Math.abs(diff).toFixed(decimals)}{def.suffix}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 h-44 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="period_label" stroke="#64748b" tick={{ fontSize: 10 }} interval="preserveStartEnd" minTickGap={windowType === 'monthly' ? 6 : 28} />
            <YAxis
              stroke="#64748b"
              tick={{ fontSize: 10 }}
              domain={def.key === 'rmse' ? ['auto', 'auto'] : [0, 100]}
              ticks={def.key === 'rmse' ? undefined : [0, 50, 100]}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px', fontSize: '12px' }}
              labelStyle={{ color: '#e2e8f0' }}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.period_full ?? label}
              formatter={(v) => (typeof v === 'number' ? fmt(v) : v)}
            />
            {models.map(m => (
              <Line
                key={m.id}
                type="monotone"
                dataKey={`${m.id}_${def.key}`}
                name={m.name}
                stroke={m.color}
                strokeWidth={2}
                // con muchos puntos (ventanas por partido) las marcas saturan: solo la línea
                dot={data.length > 40 ? false : { r: 2, fill: m.color }}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 text-[11px] text-slate-500">
        <span>
          {i18n.t('evolution.avgLabel')}:{' '}
          <span className="text-blue-400">{models[0].avg != null ? fmt(models[0].avg) : '—'}</span>
          {' · '}
          <span className="text-orange-400">{models[1].avg != null ? fmt(models[1].avg) : '—'}</span>
        </span>
        {!def.higherIsBetter && <span>{i18n.t('evolution.lowerBetter')}</span>}
      </div>
    </div>
  );
}
