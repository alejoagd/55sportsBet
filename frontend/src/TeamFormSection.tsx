import { useState, useEffect } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

interface FormMatch {
  date: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  tournament: string;
  is_home: boolean;
  result: 'W' | 'D' | 'L';
}

interface TeamFormResponse {
  home_team: string;
  away_team: string;
  home_form: FormMatch[];
  away_form: FormMatch[];
}

const TEAM_FLAG: Record<string, string> = {
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
  'Honduras': '🇭🇳', 'Costa Rica': '🇨🇷', 'El Salvador': '🇸🇻', 'Jamaica': '🇯🇲',
  'Bolivia': '🇧🇴', 'Chile': '🇨🇱', 'Venezuela': '🇻🇪', 'Peru': '🇵🇪',
  'Nigeria': '🇳🇬', 'Cameroon': '🇨🇲', 'Mali': '🇲🇱', 'Angola': '🇦🇴',
  'Zimbabwe': '🇿🇼', 'Rwanda': '🇷🇼', 'Tanzania': '🇹🇿', 'Zambia': '🇿🇲',
  'China PR': '🇨🇳', 'Thailand': '🇹🇭', 'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
  'Serbia': '🇷🇸', 'Ukraine': '🇺🇦', 'Poland': '🇵🇱', 'Denmark': '🇩🇰',
  'Wales': '🏴󠁧󠁢󠁷󠁬󠁳󠁿', 'Ireland': '🇮🇪', 'Finland': '🇫🇮', 'Greece': '🇬🇷',
  'Iceland': '🇮🇸', 'Hungary': '🇭🇺', 'Romania': '🇷🇴', 'Slovakia': '🇸🇰',
  'Suriname': '🇸🇷', 'Dominican Republic': '🇩🇴', 'Trinidad and Tobago': '🇹🇹',
};

const TEAM_CODE: Record<string, string> = {
  'Mexico': 'MEX', 'South Africa': 'SAF', 'South Korea': 'KOR', 'Czechia': 'CZE',
  'Canada': 'CAN', 'Bosnia and Herzegovina': 'BIH', 'Qatar': 'QAT', 'Switzerland': 'SUI',
  'Brazil': 'BRA', 'Morocco': 'MAR', 'Haiti': 'HAI', 'Scotland': 'SCO',
  'United States': 'USA', 'Paraguay': 'PAR', 'Australia': 'AUS', 'Turkey': 'TUR',
  'Germany': 'GER', 'Curacao': 'CUR', 'Ivory Coast': 'CIV', 'Ecuador': 'ECU',
  'Netherlands': 'NED', 'Japan': 'JPN', 'Sweden': 'SWE', 'Tunisia': 'TUN',
  'Belgium': 'BEL', 'Egypt': 'EGY', 'Iran': 'IRN', 'New Zealand': 'NZL',
  'Spain': 'ESP', 'Cape Verde': 'CPV', 'Saudi Arabia': 'KSA', 'Uruguay': 'URU',
  'France': 'FRA', 'Senegal': 'SEN', 'Iraq': 'IRQ', 'Norway': 'NOR',
  'Argentina': 'ARG', 'Algeria': 'ALG', 'Austria': 'AUT', 'Jordan': 'JOR',
  'Portugal': 'POR', 'Congo DR': 'COD', 'Uzbekistan': 'UZB', 'Colombia': 'COL',
  'England': 'ENG', 'Croatia': 'CRO', 'Ghana': 'GHA', 'Panama': 'PAN',
};

function getTournamentAbbr(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('gold cup')) return 'GC';
  if (lower.includes('concacaf nations')) return 'CNL';
  if (lower.includes('nations league') && lower.includes('uefa')) return 'UNL';
  if (lower.includes('nations league')) return 'NL';
  if (lower.includes('africa cup') || lower.includes('afcon')) return 'ACN';
  if (lower.includes('asian cup') || lower.includes('afc asian')) return 'ACU';
  if (lower.includes('copa america') || lower.includes('copa')) return 'CA';
  if (lower.includes('euro 20') || lower.includes('uefa euro')) return 'EUR';
  if (lower.includes('finalissima')) return 'FIN';
  if (lower.includes('qualification') || lower.includes('qualifier') || lower.includes('qualifying')) return 'WCQ';
  if (lower.includes('world cup')) return 'WC';
  if (lower.includes('friendly') || lower.includes('amistoso')) return 'AMI';
  return name.split(/\s+/).filter(Boolean).map(w => w[0]).join('').toUpperCase().slice(0, 4);
}

function formatFormDate(dateStr: string): { top: string; bottom: string } {
  const d = new Date(dateStr + 'T12:00:00');
  return {
    top: `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`,
    bottom: String(d.getFullYear()),
  };
}

function resultClass(result: 'W' | 'D' | 'L'): string {
  if (result === 'W') return 'bg-green-600 text-white';
  if (result === 'D') return 'bg-yellow-500 text-black';
  return 'bg-red-600 text-white';
}

function TeamFormPanel({ team, form }: { team: string; form: FormMatch[] }) {
  const flag = TEAM_FLAG[team] ?? '🏳';
  const code = TEAM_CODE[team] ?? team.slice(0, 3).toUpperCase();

  const tournaments = Array.from(new Set(form.map(m => m.tournament)));
  const [activeTab, setActiveTab] = useState('Todos');

  const displayed = activeTab === 'Todos'
    ? form.slice(0, 6)
    : form.filter(m => m.tournament === activeTab).slice(0, 6);

  const wins   = displayed.filter(m => m.result === 'W').length;
  const draws  = displayed.filter(m => m.result === 'D').length;
  const losses = displayed.filter(m => m.result === 'L').length;
  const total  = displayed.length || 1;

  return (
    <div className="flex-1 min-w-0">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl leading-none">{flag}</span>
        <div>
          <span className="text-sm font-bold text-slate-200 tracking-wide">{code}</span>
          <p className="text-[10px] text-slate-400 uppercase tracking-widest">Últimos 6 Partidos</p>
        </div>
      </div>

      {/* Tournament filter tabs */}
      {tournaments.length > 1 && (
        <div className="flex gap-1 mb-3 flex-wrap">
          <button
            onClick={() => setActiveTab('Todos')}
            className={`text-[11px] px-2.5 py-1 rounded-full transition-colors font-medium ${
              activeTab === 'Todos'
                ? 'bg-slate-500 text-white'
                : 'bg-slate-700/60 text-slate-400 hover:text-slate-200'
            }`}
          >
            Todos
          </button>
          {tournaments.map(t => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`text-[11px] px-2.5 py-1 rounded-full transition-colors font-medium ${
                activeTab === t
                  ? 'bg-slate-500 text-white'
                  : 'bg-slate-700/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {getTournamentAbbr(t)}
            </button>
          ))}
        </div>
      )}

      {/* Match rows */}
      <div className="space-y-1.5">
        {displayed.length === 0 ? (
          <p className="text-xs text-slate-500 italic">Sin partidos</p>
        ) : (
          displayed.map((m, i) => {
            const { top, bottom } = formatFormDate(m.date);
            const abbr = getTournamentAbbr(m.tournament);
            return (
              <div key={i} className="flex items-center gap-2 text-xs">
                {/* Date */}
                <div className="w-12 flex-shrink-0 text-center leading-tight">
                  <div className="text-slate-300 font-medium tabular-nums">{top}</div>
                  <div className="text-slate-500 tabular-nums">{bottom}</div>
                </div>

                {/* Home team */}
                <span className={`flex-1 text-right truncate ${m.is_home ? 'text-slate-100 font-semibold' : 'text-slate-400'}`}>
                  {m.home_team}
                </span>

                {/* Score badge */}
                <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-bold tabular-nums ${resultClass(m.result)}`}>
                  {m.home_goals}-{m.away_goals}
                </span>

                {/* Away team */}
                <span className={`flex-1 text-left truncate ${!m.is_home ? 'text-slate-100 font-semibold' : 'text-slate-400'}`}>
                  {m.away_team}
                </span>

                {/* Tournament abbr */}
                <span className="w-8 text-right flex-shrink-0 text-[10px] text-slate-500 font-medium">{abbr}</span>
              </div>
            );
          })
        )}
      </div>

      {/* Summary bar */}
      {displayed.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-slate-700/60">
          <div className="flex gap-4 text-xs mb-1.5">
            <span className="text-green-400 font-semibold">Victoria {wins}</span>
            <span className="text-yellow-400 font-semibold">Empate {draws}</span>
            <span className="text-red-400 font-semibold">Derrota {losses}</span>
          </div>
          <div className="flex h-1.5 rounded-full overflow-hidden">
            <div className="bg-green-500" style={{ width: `${(wins / total) * 100}%` }} />
            <div className="bg-yellow-500" style={{ width: `${(draws / total) * 100}%` }} />
            <div className="bg-red-500" style={{ width: `${(losses / total) * 100}%` }} />
          </div>
          <div className="flex gap-4 text-[10px] text-slate-500 mt-1">
            <span>{((wins / total) * 100).toFixed(0)}%</span>
            <span>{((draws / total) * 100).toFixed(0)}%</span>
            <span>{((losses / total) * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TeamFormSection({ matchId }: { matchId: number }) {
  const [data, setData] = useState<TeamFormResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/matches/${matchId}/team-form`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [matchId]);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 animate-pulse">
        <div className="h-4 w-48 bg-slate-700 rounded mb-4" />
        <div className="h-40 bg-slate-700 rounded" />
      </div>
    );
  }

  if (!data || (data.home_form.length === 0 && data.away_form.length === 0)) {
    return null;
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-xl border border-slate-700">
      <h2 className="text-lg font-bold text-slate-200 mb-5 flex items-center gap-2">
        📈 Últimos Partidos
      </h2>
      <div className="flex flex-col sm:flex-row gap-6">
        <TeamFormPanel team={data.home_team} form={data.home_form} />
        <div className="hidden sm:block w-px bg-slate-700 flex-shrink-0" />
        <TeamFormPanel team={data.away_team} form={data.away_form} />
      </div>
    </div>
  );
}
