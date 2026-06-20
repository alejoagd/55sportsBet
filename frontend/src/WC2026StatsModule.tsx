import { useState, useEffect } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────
interface TopScorer {
  player: string;
  team: string;
  goals: number;
  penalties: number;
  own_goals: number;
  minutes: number[];
}

interface TopAssister {
  player: string;
  team: string;
  assists: number;
  minutes: number[];
}

interface CleanSheet {
  team: string;
  matches_played: number;
  clean_sheets: number;
  goals_conceded: number;
  goals_scored: number;
}

// ── Flag map (same as WorldCupDashboard) ─────────────────────────────────────
const FLAG: Record<string, string> = {
  'Mexico': '🇲🇽', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷', 'Czechia': '🇨🇿',
  'Canada': '🇨🇦', 'Bosnia and Herzegovina': '🇧🇦', 'Qatar': '🇶🇦', 'Switzerland': '🇨🇭',
  'Brazil': '🇧🇷', 'Morocco': '🇲🇦', 'Haiti': '🇭🇹', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'United States': '🇺🇸', 'Paraguay': '🇵🇾', 'Australia': '🇦🇺', 'Turkey': '🇹🇷',
  'Germany': '🇩🇪', 'Curacao': '🇨🇼', 'Ivory Coast': '🇨🇮', 'Ecuador': '🇪🇨',
  'Netherlands': '🇳🇱', 'Japan': '🇯🇵', 'Sweden': '🇸🇪', 'Tunisia': '🇹🇳',
  'Belgium': '🇧🇪', 'Egypt': '🇪🇬', 'Iran': '🇮🇷', 'New Zealand': '🇳🇿',
  'Spain': '🇪🇸', 'Cape Verde': '🇨🇻', 'Saudi Arabia': '🇸🇦', 'Uruguay': '🇺🇾',
  'France': '🇫🇷', 'Senegal': '🇸🇳', 'Iraq': '🇮🇶', 'Norway': '🇳🇴',
  'Argentina': '🇦🇷', 'Algeria': '🇩🇿', 'Austria': '🇦🇹', 'Jordan': '🇯🇴',
  'Portugal': '🇵🇹', 'Congo DR': '🇨🇩', 'Uzbekistan': '🇺🇿', 'Colombia': '🇨🇴',
  'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Croatia': '🇭🇷', 'Ghana': '🇬🇭', 'Panama': '🇵🇦',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ icon, title, subtitle }: { icon: string; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <span className="text-3xl">{icon}</span>
      <div>
        <h2 className="text-lg font-black text-white">{title}</h2>
        {subtitle && <p className="text-slate-400 text-xs mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function Medal({ rank }: { rank: number }) {
  if (rank === 1) return <span className="text-xl">🥇</span>;
  if (rank === 2) return <span className="text-xl">🥈</span>;
  if (rank === 3) return <span className="text-xl">🥉</span>;
  return (
    <span className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-700 text-slate-300 text-xs font-bold">
      {rank}
    </span>
  );
}

// ── Top Scorers ───────────────────────────────────────────────────────────────
function TopScorersTable({ scorers }: { scorers: TopScorer[] }) {
  if (scorers.length === 0) {
    return (
      <div className="text-center py-10 text-slate-500">
        Sin goles registrados aún
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {scorers.slice(0, 20).map((s, i) => (
        <div
          key={`${s.player}-${s.team}`}
          className={`flex items-center gap-3 rounded-xl px-4 py-3 transition-colors
            ${i === 0 ? 'bg-yellow-500/10 border border-yellow-500/30' :
              i < 3 ? 'bg-slate-800 border border-slate-700/60' :
              'bg-slate-800/50 border border-slate-700/30'}`}
        >
          <div className="w-8 flex-shrink-0 flex justify-center">
            <Medal rank={i + 1} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-base leading-none">{FLAG[s.team] ?? '🏳'}</span>
              <span className="text-white font-semibold text-sm truncate">{s.player}</span>
            </div>
            <div className="text-slate-500 text-xs mt-0.5">{s.team}</div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {s.penalties > 0 && (
              <span className="text-[10px] text-slate-400 bg-slate-700 px-1.5 py-0.5 rounded">
                {s.penalties} P
              </span>
            )}
            <div className="text-center">
              <div className="text-2xl font-black text-yellow-400 leading-none">{s.goals}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">goles</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Top Assisters ─────────────────────────────────────────────────────────────
function TopAssistersTable({ assisters }: { assisters: TopAssister[] }) {
  if (assisters.length === 0) {
    return (
      <div className="text-center py-10 text-slate-500">
        Sin asistencias registradas aún
        <p className="text-xs mt-2 text-slate-600">Los datos de asistidores se cargan desde ESPN</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {assisters.slice(0, 20).map((a, i) => (
        <div
          key={`${a.player}-${a.team}`}
          className={`flex items-center gap-3 rounded-xl px-4 py-3 transition-colors
            ${i === 0 ? 'bg-blue-500/10 border border-blue-500/30' :
              i < 3 ? 'bg-slate-800 border border-slate-700/60' :
              'bg-slate-800/50 border border-slate-700/30'}`}
        >
          <div className="w-8 flex-shrink-0 flex justify-center">
            <Medal rank={i + 1} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-base leading-none">{FLAG[a.team] ?? '🏳'}</span>
              <span className="text-white font-semibold text-sm truncate">{a.player}</span>
            </div>
            <div className="text-slate-500 text-xs mt-0.5">{a.team}</div>
          </div>

          <div className="text-center flex-shrink-0">
            <div className="text-2xl font-black text-blue-400 leading-none">{a.assists}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">asist.</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Clean Sheets ──────────────────────────────────────────────────────────────
function CleanSheetsTable({ data }: { data: CleanSheet[] }) {
  if (data.length === 0) {
    return <div className="text-center py-10 text-slate-500">Sin datos disponibles</div>;
  }

  const withCS = data.filter(d => d.clean_sheets > 0);
  const noCS   = data.filter(d => d.clean_sheets === 0);

  const Row = ({ d, i }: { d: CleanSheet; i: number }) => (
    <div
      className={`flex items-center gap-3 rounded-xl px-4 py-3
        ${i < 3 && d.clean_sheets > 0
          ? 'bg-green-500/10 border border-green-500/30'
          : 'bg-slate-800/50 border border-slate-700/30'}`}
    >
      <div className="w-8 flex-shrink-0 flex justify-center">
        {d.clean_sheets > 0 ? <Medal rank={i + 1} /> : (
          <span className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-700 text-slate-500 text-xs">{i + 1}</span>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none">{FLAG[d.team] ?? '🏳'}</span>
          <span className="text-white font-semibold text-sm truncate">{d.team}</span>
        </div>
        <div className="text-slate-500 text-xs mt-0.5">
          {d.matches_played} PJ · {d.goals_conceded} GC · {d.goals_scored} GF
        </div>
      </div>

      <div className="flex items-center gap-4 flex-shrink-0">
        <div className="text-center">
          <div className={`text-2xl font-black leading-none ${d.clean_sheets > 0 ? 'text-green-400' : 'text-slate-600'}`}>
            {d.clean_sheets}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">valla(s)</div>
        </div>
        <div className="text-center hidden sm:block">
          <div className="text-lg font-bold text-slate-400 leading-none">{d.goals_conceded}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">GC</div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-5">
      {withCS.length > 0 && (
        <div className="space-y-2">
          {withCS.map((d, i) => <Row key={d.team} d={d} i={i} />)}
        </div>
      )}
      {noCS.length > 0 && (
        <div>
          <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide px-1 mb-2">
            Sin valla invicta
          </div>
          <div className="space-y-1.5">
            {noCS.map((d, i) => <Row key={d.team} d={d} i={withCS.length + i} />)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
type StatsTab = 'scorers' | 'assisters' | 'clean-sheets';

export default function WC2026StatsModule() {
  const [activeTab, setActiveTab] = useState<StatsTab>('scorers');
  const [scorers, setScorers] = useState<TopScorer[]>([]);
  const [assisters, setAssistiers] = useState<TopAssister[]>([]);
  const [cleanSheets, setCleanSheets] = useState<CleanSheet[]>([]);
  const [loading, setLoading] = useState<Record<StatsTab, boolean>>({
    scorers: true, assisters: true, 'clean-sheets': true,
  });

  useEffect(() => {
    fetch(`${API_URL}/api/wc2026/top-scorers`)
      .then(r => r.json())
      .then(d => { setScorers(d); setLoading(p => ({ ...p, scorers: false })); })
      .catch(() => setLoading(p => ({ ...p, scorers: false })));

    fetch(`${API_URL}/api/wc2026/top-assisters`)
      .then(r => r.json())
      .then(d => { setAssistiers(d); setLoading(p => ({ ...p, assisters: false })); })
      .catch(() => setLoading(p => ({ ...p, assisters: false })));

    fetch(`${API_URL}/api/wc2026/clean-sheets`)
      .then(r => r.json())
      .then(d => { setCleanSheets(d); setLoading(p => ({ ...p, 'clean-sheets': false })); })
      .catch(() => setLoading(p => ({ ...p, 'clean-sheets': false })));
  }, []);

  const tabs: { id: StatsTab; icon: string; label: string }[] = [
    { id: 'scorers',       icon: '⚽', label: 'Goleadores' },
    { id: 'assisters',     icon: '🎯', label: 'Asistidores' },
    { id: 'clean-sheets',  icon: '🧤', label: 'Vallas Invictas' },
  ];

  const isLoading = loading[activeTab];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-gradient-to-r from-yellow-900/30 to-slate-900 border border-yellow-500/20 rounded-xl p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🏅</span>
          <div>
            <h2 className="text-lg font-black text-white">Estadísticas del Torneo</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Goleadores · Asistidores · Vallas Invictas — Mundial 2026
            </p>
          </div>
        </div>
      </div>

      {/* Tab selector */}
      <div className="bg-slate-800/60 p-1 rounded-xl border border-slate-700/50 flex gap-1">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-semibold transition-all
              ${activeTab === t.id
                ? 'bg-yellow-500 text-slate-900 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/60'}`}
          >
            <span>{t.icon}</span>
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[300px]">
        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <div className="text-slate-400 animate-pulse">Cargando estadísticas...</div>
          </div>
        ) : activeTab === 'scorers' ? (
          <>
            <SectionHeader
              icon="⚽"
              title="Tabla de Goleadores"
              subtitle={`${scorers.length} jugadores con goles · fuente: international_results`}
            />
            <TopScorersTable scorers={scorers} />
          </>
        ) : activeTab === 'assisters' ? (
          <>
            <SectionHeader
              icon="🎯"
              title="Tabla de Asistidores"
              subtitle={`${assisters.length} jugadores con asistencias · fuente: ESPN`}
            />
            <TopAssistersTable assisters={assisters} />
          </>
        ) : (
          <>
            <SectionHeader
              icon="🧤"
              title="Vallas Invictas por Equipo"
              subtitle="Partidos sin recibir goles · calculado desde resultados reales"
            />
            <CleanSheetsTable data={cleanSheets} />
          </>
        )}
      </div>
    </div>
  );
}
