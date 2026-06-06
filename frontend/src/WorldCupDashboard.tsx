import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

interface Match {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
  referee: string | null;
  poisson_home_goals: number;
  poisson_away_goals: number;
  poisson_prob_home: number;
  poisson_prob_draw: number;
  poisson_prob_away: number;
  poisson_over_25: number;
  poisson_btts: number;
  weinston_home_goals: number;
  weinston_away_goals: number;
  weinston_result: string;
  weinston_over_25: number;
  weinston_btts: number;
  weinston_prob_over_25?: number;
  weinston_prob_btts?: number;
}

interface GroupMatch {
  match_id: number;
  home_team: string;
  away_team: string;
  home_goals: number | null;
  away_goals: number | null;
  date: string;
}

interface TeamStanding {
  team: string;
  pj: number; g: number; e: number; p: number;
  gf: number; gc: number; dg: number; pts: number;
}

// ── Group assignments ────────────────────────────────────────────────
const TEAM_GROUP: Record<string, string> = {
  'Mexico': 'A', 'South Africa': 'A', 'South Korea': 'A', 'Czechia': 'A',
  'Canada': 'B', 'Bosnia and Herzegovina': 'B', 'Qatar': 'B', 'Switzerland': 'B',
  'Brazil': 'C', 'Morocco': 'C', 'Haiti': 'C', 'Scotland': 'C',
  'United States': 'D', 'Paraguay': 'D', 'Australia': 'D', 'Turkey': 'D',
  'Germany': 'E', 'Curacao': 'E', 'Ivory Coast': 'E', 'Ecuador': 'E',
  'Netherlands': 'F', 'Japan': 'F', 'Sweden': 'F', 'Tunisia': 'F',
  'Belgium': 'G', 'Egypt': 'G', 'Iran': 'G', 'New Zealand': 'G',
  'Spain': 'H', 'Cape Verde': 'H', 'Saudi Arabia': 'H', 'Uruguay': 'H',
  'France': 'I', 'Senegal': 'I', 'Iraq': 'I', 'Norway': 'I',
  'Argentina': 'J', 'Algeria': 'J', 'Austria': 'J', 'Jordan': 'J',
  'Portugal': 'K', 'Congo DR': 'K', 'Uzbekistan': 'K', 'Colombia': 'K',
  'England': 'L', 'Croatia': 'L', 'Ghana': 'L', 'Panama': 'L',
};

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
};

const GROUPS = ['A','B','C','D','E','F','G','H','I','J','K','L'];

const GROUP_TEAMS: Record<string, string[]> = {
  'A': ['Mexico','South Africa','South Korea','Czechia'],
  'B': ['Canada','Bosnia and Herzegovina','Qatar','Switzerland'],
  'C': ['Brazil','Morocco','Haiti','Scotland'],
  'D': ['United States','Paraguay','Australia','Turkey'],
  'E': ['Germany','Curacao','Ivory Coast','Ecuador'],
  'F': ['Netherlands','Japan','Sweden','Tunisia'],
  'G': ['Belgium','Egypt','Iran','New Zealand'],
  'H': ['Spain','Cape Verde','Saudi Arabia','Uruguay'],
  'I': ['France','Senegal','Iraq','Norway'],
  'J': ['Argentina','Algeria','Austria','Jordan'],
  'K': ['Portugal','Congo DR','Uzbekistan','Colombia'],
  'L': ['England','Croatia','Ghana','Panama'],
};


// ── Standings computation ────────────────────────────────────────────
function computeStandings(group: string, allMatches: GroupMatch[]): TeamStanding[] {
  const teams = GROUP_TEAMS[group] || [];
  const st: Record<string, TeamStanding> = {};
  for (const t of teams) st[t] = { team: t, pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0 };

  for (const m of allMatches) {
    if (TEAM_GROUP[m.home_team] !== group) continue;
    if (m.home_goals === null || m.away_goals === null) continue;
    const hg = m.home_goals, ag = m.away_goals;
    const h = m.home_team, a = m.away_team;
    if (!st[h] || !st[a]) continue;
    st[h].pj++; st[a].pj++;
    st[h].gf += hg; st[h].gc += ag;
    st[a].gf += ag; st[a].gc += hg;
    st[h].dg = st[h].gf - st[h].gc;
    st[a].dg = st[a].gf - st[a].gc;
    if (hg > ag) { st[h].g++; st[h].pts += 3; st[a].p++; }
    else if (ag > hg) { st[a].g++; st[a].pts += 3; st[h].p++; }
    else { st[h].e++; st[a].e++; st[h].pts++; st[a].pts++; }
  }

  return Object.values(st).sort((a, b) =>
    b.pts !== a.pts ? b.pts - a.pts :
    b.dg !== a.dg ? b.dg - a.dg :
    b.gf !== a.gf ? b.gf - a.gf :
    a.team.localeCompare(b.team)
  );
}

// ── Helper functions ─────────────────────────────────────────────────
function getMatchGroup(match: Match): string {
  return TEAM_GROUP[match.home_team] || TEAM_GROUP[match.away_team] || '?';
}

function safeNum(v: any, def = 0): number {
  if (v === null || v === undefined || isNaN(Number(v))) return def;
  return Number(v);
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const [year, month, day] = dateStr.split('T')[0].split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('es-ES', {
    weekday: 'short', day: '2-digit', month: 'short',
  });
}

function daysUntil(targetDate: string): number {
  const now = new Date();
  const target = new Date(targetDate);
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

// ── Countdown banner ─────────────────────────────────────────────────
function WorldCupBanner({ matchCount }: { matchCount: number }) {
  const daysLeft = daysUntil('2026-06-11');

  return (
    <div className="relative overflow-hidden rounded-2xl mb-6">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-[#0d1f3c] to-slate-900" />
      <div className="absolute inset-0 bg-gradient-to-r from-yellow-500/10 via-transparent to-yellow-500/10" />
      <div className="absolute -top-16 -left-16 w-64 h-64 bg-yellow-400/5 rounded-full blur-3xl" />
      <div className="absolute -bottom-16 -right-16 w-64 h-64 bg-yellow-400/5 rounded-full blur-3xl" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-yellow-400/50 to-transparent" />
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-yellow-400/50 to-transparent" />

      <div className="relative px-4 sm:px-8 py-6 sm:py-10">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-4xl sm:text-5xl drop-shadow-lg">🏆</span>
            <div>
              <p className="text-yellow-400 font-bold text-xs sm:text-sm tracking-[0.2em] uppercase">FIFA</p>
              <h1 className="text-2xl sm:text-4xl font-black text-white leading-none tracking-tight">
                WORLD CUP
                <span className="ml-2 text-yellow-400">2026</span>
              </h1>
            </div>
          </div>

          {daysLeft > 0 ? (
            <div className="flex items-center gap-2 bg-yellow-400/10 border border-yellow-400/30 rounded-xl px-4 py-3">
              <div className="text-center">
                <p className="text-yellow-300 text-3xl sm:text-4xl font-black leading-none">{daysLeft}</p>
                <p className="text-yellow-400/70 text-xs uppercase tracking-widest mt-1">
                  {daysLeft === 1 ? 'día' : 'días'}
                </p>
              </div>
              <div className="text-yellow-400/50 text-2xl ml-1">⏳</div>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-green-400/10 border border-green-400/30 rounded-xl px-4 py-3">
              <span className="text-green-400 font-bold text-sm animate-pulse">● EN CURSO</span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 justify-center sm:justify-start mb-6">
          {['🇺🇸 USA', '🇨🇦 Canadá', '🇲🇽 México'].map(host => (
            <span key={host} className="text-xs sm:text-sm text-slate-300 bg-white/5 border border-white/10 px-3 py-1 rounded-full">
              {host}
            </span>
          ))}
          <span className="text-xs sm:text-sm text-slate-400 bg-white/5 border border-white/10 px-3 py-1 rounded-full">
            11 Jun — 19 Jul 2026
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3 sm:gap-6 max-w-sm sm:max-w-lg">
          {[
            { val: '48', label: 'Equipos' },
            { val: '12', label: 'Grupos' },
            { val: matchCount.toString(), label: 'Partidos' },
          ].map(({ val, label }) => (
            <div key={label} className="text-center bg-white/5 rounded-xl py-3 border border-white/5">
              <p className="text-xl sm:text-2xl font-black text-yellow-400">{val}</p>
              <p className="text-xs text-slate-400 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tab navigation ────────────────────────────────────────────────────
type Tab = 'matches' | 'standings' | 'bracket';

function TabNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'matches', label: 'Partidos', icon: '⚽' },
    { id: 'standings', label: 'Posiciones', icon: '📊' },
    { id: 'bracket', label: 'Bracket', icon: '🗺️' },
  ];
  return (
    <div className="flex gap-1 bg-slate-800/60 p-1 rounded-xl mb-6 border border-slate-700/50">
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-lg text-sm font-semibold transition-all
            ${active === t.id
              ? 'bg-yellow-400 text-slate-900 shadow-md shadow-yellow-400/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
        >
          <span>{t.icon}</span>
          <span>{t.label}</span>
        </button>
      ))}
    </div>
  );
}

// ── Group selector ────────────────────────────────────────────────────
function GroupSelector({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (g: string | null) => void;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-white font-bold text-lg">Grupos</h2>
        <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">Fase de Grupos</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <button
          onClick={() => onSelect(null)}
          className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-all border
            ${selected === null
              ? 'bg-yellow-400 text-slate-900 border-yellow-400 shadow-lg shadow-yellow-400/20'
              : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'
            }`}
        >
          Todos
        </button>
        {GROUPS.map(g => (
          <button
            key={g}
            onClick={() => onSelect(g)}
            className={`flex-shrink-0 px-3 py-2 rounded-lg text-sm font-bold transition-all border
              ${selected === g
                ? 'bg-yellow-400 text-slate-900 border-yellow-400 shadow-lg shadow-yellow-400/20'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'
              }`}
          >
            Grupo {g}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Match card ────────────────────────────────────────────────────────
function WCMatchCard({ match, group, currentSearchParams }: { match: Match; group: string; currentSearchParams: string }) {
  const navigate = useNavigate();
  const homeFlag = TEAM_FLAG[match.home_team] ?? '🏳';
  const awayFlag = TEAM_FLAG[match.away_team] ?? '🏳';

  const homeProb = safeNum(match.poisson_prob_home);
  const drawProb = safeNum(match.poisson_prob_draw);
  const awayProb = safeNum(match.poisson_prob_away);
  const total = homeProb + drawProb + awayProb || 1;
  const homeP = (homeProb / total) * 100;
  const drawP = (drawProb / total) * 100;
  const awayP = (awayProb / total) * 100;

  const favorite = homeProb > awayProb && homeProb > drawProb ? 'home'
    : awayProb > homeProb && awayProb > drawProb ? 'away'
    : 'draw';

  const pHomeGoals = safeNum(match.poisson_home_goals);
  const pAwayGoals = safeNum(match.poisson_away_goals);
  const overProb = safeNum(match.poisson_over_25);
  const hasPredictions = match.poisson_prob_home != null && match.poisson_prob_home !== undefined;

  return (
    <div
      onClick={() => navigate(`/match/${match.match_id}`, { state: { group, returnSearch: currentSearchParams } })}
      className="bg-slate-800 border border-slate-700 hover:border-yellow-400/40 hover:bg-slate-750 rounded-xl overflow-hidden transition-all cursor-pointer group"
    >
      <div className="flex items-center justify-between px-3 sm:px-4 pt-3 pb-2 border-b border-slate-700/50">
        <span className="text-xs font-bold text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded">
          Grupo {group}
        </span>
        <span className="text-xs text-slate-400">{formatDate(match.date)}</span>
      </div>

      <div className="px-3 sm:px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className={`flex-1 text-right ${favorite === 'home' ? 'opacity-100' : 'opacity-70'}`}>
            <div className="text-2xl mb-1">{homeFlag}</div>
            <div className={`text-xs sm:text-sm font-bold leading-tight ${favorite === 'home' ? 'text-white' : 'text-slate-300'}`}>
              {match.home_team}
            </div>
          </div>

          <div className="flex-shrink-0 text-center px-2">
            {hasPredictions ? (
              <div className="bg-slate-900 rounded-lg px-3 py-2 border border-slate-600">
                <div className="text-white font-black text-lg sm:text-xl font-mono">
                  {Math.round(pHomeGoals)} — {Math.round(pAwayGoals)}
                </div>
                <div className="text-slate-500 text-xs mt-0.5">marcador esperado</div>
              </div>
            ) : (
              <div className="text-slate-500 text-sm font-bold px-3">vs</div>
            )}
          </div>

          <div className={`flex-1 text-left ${favorite === 'away' ? 'opacity-100' : 'opacity-70'}`}>
            <div className="text-2xl mb-1">{awayFlag}</div>
            <div className={`text-xs sm:text-sm font-bold leading-tight ${favorite === 'away' ? 'text-white' : 'text-slate-300'}`}>
              {match.away_team}
            </div>
          </div>
        </div>
      </div>

      {hasPredictions && (
        <div className="px-3 sm:px-4 pb-4 space-y-3">
          <div>
            <div className="flex text-xs text-slate-400 justify-between mb-1">
              <span className={favorite === 'home' ? 'text-green-400 font-bold' : ''}>{homeP.toFixed(0)}%</span>
              <span className={favorite === 'draw' ? 'text-yellow-400 font-bold' : ''}>Empate {drawP.toFixed(0)}%</span>
              <span className={favorite === 'away' ? 'text-green-400 font-bold' : ''}>{awayP.toFixed(0)}%</span>
            </div>
            <div className="flex h-2 rounded-full overflow-hidden gap-px bg-slate-900">
              <div className="bg-blue-500 transition-all rounded-l-full" style={{ width: `${homeP}%` }} />
              <div className="bg-slate-500 transition-all" style={{ width: `${drawP}%` }} />
              <div className="bg-orange-500 transition-all rounded-r-full" style={{ width: `${awayP}%` }} />
            </div>
            <div className="flex text-xs text-slate-500 justify-between mt-0.5">
              <span>Local</span>
              <span>Visitante</span>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
              ${overProb >= 0.5
                ? 'text-green-400 border-green-400/30 bg-green-400/10'
                : 'text-orange-400 border-orange-400/30 bg-orange-400/10'
              }`}>
              {overProb >= 0.5 ? `Over 2.5 · ${(overProb * 100).toFixed(0)}%` : `Under 2.5 · ${((1 - overProb) * 100).toFixed(0)}%`}
            </span>
            {match.poisson_btts != null && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
                ${safeNum(match.poisson_btts) >= 0.5
                  ? 'text-purple-400 border-purple-400/30 bg-purple-400/10'
                  : 'text-slate-400 border-slate-600 bg-slate-700/50'
                }`}>
                BTTS {(safeNum(match.poisson_btts) * 100).toFixed(0)}%
              </span>
            )}
            <span className="text-xs text-slate-500 ml-auto self-center group-hover:text-slate-300 transition-colors">
              Ver detalle →
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Group header ──────────────────────────────────────────────────────
function GroupHeader({ group }: { group: string }) {
  const teams = GROUP_TEAMS[group] ?? [];
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="flex-shrink-0 w-10 h-10 bg-yellow-400 rounded-lg flex items-center justify-center">
        <span className="text-slate-900 font-black text-lg">{group}</span>
      </div>
      <div>
        <h3 className="text-white font-bold text-lg">Grupo {group}</h3>
        <div className="flex gap-2 flex-wrap mt-0.5">
          {teams.map(t => (
            <span key={t} className="text-xs text-slate-400">
              {TEAM_FLAG[t]} {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Standings table for one group ─────────────────────────────────────
function GroupStandingTable({ group, allMatches }: { group: string; allMatches: GroupMatch[] }) {
  const rows = computeStandings(group, allMatches);
  const gamesPlayed = rows.reduce((s, r) => s + r.pj, 0) / 2;

  const rowStyle = (pos: number) =>
    pos <= 2 ? 'border-l-2 border-l-green-500 bg-green-500/5'
    : pos === 3 ? 'border-l-2 border-l-yellow-500 bg-yellow-500/5'
    : 'border-l-2 border-l-slate-700 bg-transparent';

  const posBadge = (pos: number) =>
    pos <= 2 ? 'bg-green-500 text-white'
    : pos === 3 ? 'bg-yellow-500 text-slate-900'
    : 'bg-slate-700 text-slate-400';

  return (
    <div className="mb-8">
      <GroupHeader group={group} />
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        {/* Header row */}
        <div className="hidden sm:grid sm:grid-cols-[2.5rem_1fr_repeat(8,3rem)] text-xs text-slate-400 font-semibold px-3 py-2.5 border-b border-slate-700 bg-slate-900/60 uppercase tracking-wide">
          <span>#</span>
          <span>Equipo</span>
          <span className="text-center">PJ</span>
          <span className="text-center">G</span>
          <span className="text-center">E</span>
          <span className="text-center">P</span>
          <span className="text-center">GF</span>
          <span className="text-center">GC</span>
          <span className="text-center">DG</span>
          <span className="text-center text-yellow-400">Pts</span>
        </div>
        {/* Mobile header */}
        <div className="grid grid-cols-[2.5rem_1fr_repeat(4,2.5rem)] sm:hidden text-xs text-slate-400 font-semibold px-3 py-2.5 border-b border-slate-700 bg-slate-900/60 uppercase tracking-wide">
          <span>#</span>
          <span>Equipo</span>
          <span className="text-center">PJ</span>
          <span className="text-center">DG</span>
          <span className="text-center text-yellow-400">Pts</span>
          <span className="text-center">GF</span>
        </div>

        {rows.map((row, i) => (
          <div key={row.team} className={`border-b border-slate-700/40 last:border-0 ${rowStyle(i + 1)}`}>
            {/* Desktop row */}
            <div className="hidden sm:grid sm:grid-cols-[2.5rem_1fr_repeat(8,3rem)] px-3 py-3 items-center">
              <span className={`w-6 h-6 rounded text-xs font-bold flex items-center justify-center ${posBadge(i + 1)}`}>{i + 1}</span>
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-lg leading-none">{TEAM_FLAG[row.team] ?? '🏳'}</span>
                <span className="text-sm font-semibold text-white truncate">{row.team}</span>
              </div>
              <span className="text-center text-sm text-slate-300">{row.pj}</span>
              <span className="text-center text-sm text-slate-300">{row.g}</span>
              <span className="text-center text-sm text-slate-300">{row.e}</span>
              <span className="text-center text-sm text-slate-300">{row.p}</span>
              <span className="text-center text-sm text-slate-300">{row.gf}</span>
              <span className="text-center text-sm text-slate-300">{row.gc}</span>
              <span className={`text-center text-sm font-medium ${row.dg > 0 ? 'text-green-400' : row.dg < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                {row.dg > 0 ? '+' : ''}{row.dg}
              </span>
              <span className="text-center text-base font-black text-yellow-400">{row.pts}</span>
            </div>
            {/* Mobile row */}
            <div className="grid grid-cols-[2.5rem_1fr_repeat(4,2.5rem)] sm:hidden px-3 py-3 items-center">
              <span className={`w-6 h-6 rounded text-xs font-bold flex items-center justify-center ${posBadge(i + 1)}`}>{i + 1}</span>
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-base leading-none">{TEAM_FLAG[row.team] ?? '🏳'}</span>
                <span className="text-xs font-semibold text-white truncate">{row.team}</span>
              </div>
              <span className="text-center text-sm text-slate-300">{row.pj}</span>
              <span className={`text-center text-sm font-medium ${row.dg > 0 ? 'text-green-400' : row.dg < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                {row.dg > 0 ? '+' : ''}{row.dg}
              </span>
              <span className="text-center text-sm font-black text-yellow-400">{row.pts}</span>
              <span className="text-center text-sm text-slate-300">{row.gf}</span>
            </div>
          </div>
        ))}
      </div>

      {gamesPlayed === 0 && (
        <p className="text-xs text-slate-500 mt-2 text-center">Sin partidos jugados — tabla se actualizará al iniciar el torneo</p>
      )}

      <div className="flex gap-4 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block"></span>Clasificado a R32</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-yellow-500 inline-block"></span>Posible clasificación</span>
      </div>
    </div>
  );
}

function StandingsView({
  allMatches,
  selectedGroup,
  loading,
}: {
  allMatches: GroupMatch[];
  selectedGroup: string | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="text-slate-400 text-sm animate-pulse">Cargando posiciones...</div>
      </div>
    );
  }
  const groupsToShow = selectedGroup ? [selectedGroup] : GROUPS;
  return (
    <div>
      {groupsToShow.map(g => (
        <GroupStandingTable key={g} group={g} allMatches={allMatches} />
      ))}
    </div>
  );
}

// ── Interactive Bracket ───────────────────────────────────────────────

type BracketSlot =
  | { kind: 'pos'; group: string; pos: 0 | 1 }   // 0=1st, 1=2nd
  | { kind: 'third'; label: string };

interface R32Match {
  num: number;
  slotA: BracketSlot;
  slotB: BracketSlot;
  side: 'L' | 'R';
}

// Official 2026 WC Round of 32 bracket matchups
const R32_MATCHES: R32Match[] = [
  // ── Left half ──────────────────────────────────────────────────────
  { num: 1,  side: 'L', slotA: { kind: 'pos', group: 'E', pos: 0 }, slotB: { kind: 'third', label: '3° ABCDF' } },
  { num: 2,  side: 'L', slotA: { kind: 'pos', group: 'I', pos: 0 }, slotB: { kind: 'third', label: '3° GHJKL' } },
  { num: 3,  side: 'L', slotA: { kind: 'pos', group: 'A', pos: 1 }, slotB: { kind: 'pos', group: 'B', pos: 1 } },
  { num: 4,  side: 'L', slotA: { kind: 'pos', group: 'F', pos: 0 }, slotB: { kind: 'pos', group: 'C', pos: 1 } },
  { num: 5,  side: 'L', slotA: { kind: 'pos', group: 'K', pos: 1 }, slotB: { kind: 'pos', group: 'L', pos: 1 } },
  { num: 6,  side: 'L', slotA: { kind: 'pos', group: 'H', pos: 0 }, slotB: { kind: 'pos', group: 'J', pos: 1 } },
  { num: 7,  side: 'L', slotA: { kind: 'pos', group: 'D', pos: 0 }, slotB: { kind: 'third', label: '3° BEFIJ' } },
  { num: 8,  side: 'L', slotA: { kind: 'pos', group: 'G', pos: 0 }, slotB: { kind: 'third', label: '3° AEHIJ' } },
  // ── Right half ─────────────────────────────────────────────────────
  { num: 9,  side: 'R', slotA: { kind: 'pos', group: 'C', pos: 0 }, slotB: { kind: 'pos', group: 'F', pos: 1 } },
  { num: 10, side: 'R', slotA: { kind: 'pos', group: 'E', pos: 1 }, slotB: { kind: 'pos', group: 'I', pos: 1 } },
  { num: 11, side: 'R', slotA: { kind: 'pos', group: 'A', pos: 0 }, slotB: { kind: 'third', label: '3° GEFH' } },
  { num: 12, side: 'R', slotA: { kind: 'pos', group: 'L', pos: 0 }, slotB: { kind: 'third', label: '3° EHIJK' } },
  { num: 13, side: 'R', slotA: { kind: 'pos', group: 'J', pos: 0 }, slotB: { kind: 'pos', group: 'H', pos: 1 } },
  { num: 14, side: 'R', slotA: { kind: 'pos', group: 'D', pos: 1 }, slotB: { kind: 'pos', group: 'G', pos: 1 } },
  { num: 15, side: 'R', slotA: { kind: 'pos', group: 'B', pos: 0 }, slotB: { kind: 'third', label: '3° EFGL' } },
  { num: 16, side: 'R', slotA: { kind: 'pos', group: 'K', pos: 0 }, slotB: { kind: 'third', label: '3° EHIJK' } },
];

// Draggable group card ─────────────────────────────────────────────────
function DraggableGroupCard({
  group, ranking, dragState,
  onDragStart, onDrop, onDragEnd,
}: {
  group: string;
  ranking: string[];
  dragState: { group: string; fromIdx: number } | null;
  onDragStart: (g: string, i: number) => void;
  onDrop: (g: string, toIdx: number) => void;
  onDragEnd: () => void;
}) {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-900/60 border-b border-slate-700">
        <div className="w-5 h-5 bg-yellow-400 rounded flex items-center justify-center flex-shrink-0">
          <span className="text-slate-900 font-black text-xs">{group}</span>
        </div>
        <span className="text-xs font-bold text-slate-300">Grupo {group}</span>
      </div>
      <div className="p-1.5 space-y-1">
        {ranking.map((team, idx) => {
          const isDraggingThis = dragState?.group === group && dragState?.fromIdx === idx;
          const isDragTarget = dragState?.group === group && dragState?.fromIdx !== idx;
          const rowBg =
            idx === 0 ? 'bg-green-500/15 border-green-500/30' :
            idx === 1 ? 'bg-green-500/8 border-green-500/20' :
            idx === 2 ? 'bg-yellow-500/10 border-yellow-500/30' :
            'bg-slate-700/20 border-slate-700/50';
          return (
            <div
              key={team}
              draggable
              onDragStart={() => onDragStart(group, idx)}
              onDragOver={(e) => { e.preventDefault(); }}
              onDrop={() => onDrop(group, idx)}
              onDragEnd={onDragEnd}
              className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border cursor-grab active:cursor-grabbing select-none transition-all
                ${rowBg}
                ${isDraggingThis ? 'opacity-30 scale-95' : ''}
                ${isDragTarget ? 'ring-1 ring-yellow-400/50' : ''}`}
            >
              <span className={`text-xs font-black w-3 flex-shrink-0
                ${idx < 2 ? 'text-green-400' : idx === 2 ? 'text-yellow-400' : 'text-slate-600'}`}>
                {idx + 1}
              </span>
              <span className="text-sm leading-none flex-shrink-0">{TEAM_FLAG[team] ?? '🏳'}</span>
              <span className="text-xs font-medium text-white truncate flex-1">{team}</span>
              <span className="text-slate-600 text-xs flex-shrink-0">⠿</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// R32 match card ──────────────────────────────────────────────────────
function R32Card({
  match, rankings, isTopOfPair, isBottomOfPair,
}: {
  match: R32Match;
  rankings: Record<string, string[]>;
  isTopOfPair: boolean;
  isBottomOfPair: boolean;
}) {
  const getTeam = (slot: BracketSlot): string | null => {
    if (slot.kind === 'third') return null;
    return rankings[slot.group]?.[slot.pos] ?? null;
  };

  const labelFor = (slot: BracketSlot) => {
    if (slot.kind === 'third') return slot.label;
    return `${slot.pos === 0 ? '1°' : '2°'} Grp ${slot.group}`;
  };

  const badgeFor = (slot: BracketSlot) => {
    if (slot.kind === 'third') return { text: '3°', cls: 'text-yellow-400 bg-yellow-400/10' };
    if (slot.pos === 0) return { text: '1°', cls: 'text-green-400 bg-green-400/10' };
    return { text: '2°', cls: 'text-blue-400 bg-blue-400/10' };
  };

  const teamA = getTeam(match.slotA);
  const teamB = getTeam(match.slotB);
  const badge = { a: badgeFor(match.slotA), b: badgeFor(match.slotB) };

  const connectorStyle = isTopOfPair
    ? 'rounded-t-xl rounded-br-none border-b-0 border-r-2 border-r-yellow-400/40'
    : isBottomOfPair
    ? 'rounded-b-xl rounded-tr-none border-r-2 border-r-yellow-400/40'
    : 'rounded-xl';

  return (
    <div className={`bg-slate-800 border border-slate-700 overflow-hidden ${connectorStyle}`}>
      <div className="flex items-center px-2 py-1 bg-slate-900/60 border-b border-slate-700/50">
        <span className="text-xs text-slate-500 font-bold">M{match.num}</span>
      </div>
      {/* Team A */}
      <div className="flex items-center gap-2 px-2 py-2 min-w-0">
        <span className={`text-xs font-bold px-1 rounded flex-shrink-0 ${badge.a.cls}`}>{badge.a.text}</span>
        {teamA ? (
          <>
            <span className="text-base leading-none flex-shrink-0">{TEAM_FLAG[teamA] ?? '🏳'}</span>
            <span className="text-xs font-semibold text-white truncate">{teamA}</span>
          </>
        ) : (
          <span className="text-xs text-slate-500 italic truncate">{labelFor(match.slotA)}</span>
        )}
      </div>
      <div className="mx-2 h-px bg-slate-700" />
      {/* Team B */}
      <div className="flex items-center gap-2 px-2 py-2 min-w-0">
        <span className={`text-xs font-bold px-1 rounded flex-shrink-0 ${badge.b.cls}`}>{badge.b.text}</span>
        {teamB ? (
          <>
            <span className="text-base leading-none flex-shrink-0">{TEAM_FLAG[teamB] ?? '🏳'}</span>
            <span className="text-xs font-semibold text-white truncate">{teamB}</span>
          </>
        ) : (
          <span className={`text-xs italic truncate ${match.slotB.kind === 'third' ? 'text-yellow-500/70' : 'text-slate-500'}`}>
            {labelFor(match.slotB)}
          </span>
        )}
      </div>
    </div>
  );
}

// TBD match slot ──────────────────────────────────────────────────────
function TBDSlot({ label }: { label: string }) {
  return (
    <div className="bg-slate-800/50 border border-dashed border-slate-700 rounded-xl overflow-hidden w-36">
      <div className="px-2 py-1 bg-slate-900/40 border-b border-slate-700/50">
        <span className="text-xs text-slate-600 font-bold">{label}</span>
      </div>
      <div className="flex items-center gap-2 px-2 py-2">
        <span className="w-4 h-4 rounded bg-slate-700 flex-shrink-0" />
        <span className="text-xs text-slate-600">Ganador</span>
      </div>
      <div className="mx-2 h-px bg-slate-700/50" />
      <div className="flex items-center gap-2 px-2 py-2">
        <span className="w-4 h-4 rounded bg-slate-700 flex-shrink-0" />
        <span className="text-xs text-slate-600">Ganador</span>
      </div>
    </div>
  );
}

// Bracket half (left or right) ────────────────────────────────────────
function BracketHalf({
  matches, rankings, side,
}: {
  matches: R32Match[];
  rankings: Record<string, string[]>;
  side: 'L' | 'R';
}) {
  // Pairs: matches come in groups of 2 feeding into same R16 match
  const pairs = [
    [matches[0], matches[1]],
    [matches[2], matches[3]],
    [matches[4], matches[5]],
    [matches[6], matches[7]],
  ];

  const r32 = (
    <div className="space-y-3">
      {pairs.map((pair, pi) => (
        <div key={pi} className="space-y-0">
          <R32Card match={pair[0]} rankings={rankings} isTopOfPair isBottomOfPair={false} />
          <R32Card match={pair[1]} rankings={rankings} isTopOfPair={false} isBottomOfPair />
        </div>
      ))}
    </div>
  );

  const connector = (count: number, key: string) => (
    <div key={key} className="flex flex-col justify-around py-4" style={{ gap: count === 4 ? '0.75rem' : count === 2 ? '3.5rem' : '8.5rem' }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center">
          <div className="w-3 h-px bg-slate-600" />
        </div>
      ))}
    </div>
  );

  const r16 = (
    <div className="flex flex-col justify-around py-1" style={{ gap: '1.5rem' }}>
      {[0,1,2,3].map(i => <TBDSlot key={i} label={`R16 M${i+1+(side === 'R' ? 4 : 0)}`} />)}
    </div>
  );

  const qf = (
    <div className="flex flex-col justify-around py-1" style={{ gap: '5.5rem' }}>
      {[0,1].map(i => <TBDSlot key={i} label={`QF M${i+1+(side === 'R' ? 2 : 0)}`} />)}
    </div>
  );

  const sf = (
    <div className="flex items-center justify-center h-full">
      <TBDSlot label={`SF M${side === 'R' ? 2 : 1}`} />
    </div>
  );

  const columns = side === 'L'
    ? [r32, connector(4, 'c1'), r16, connector(2, 'c2'), qf, connector(1, 'c3'), sf]
    : [sf, connector(1, 'c3'), qf, connector(2, 'c2'), r16, connector(4, 'c1'), r32];

  return (
    <div className="flex items-stretch gap-0">
      {columns}
    </div>
  );
}

// Interactive bracket view ────────────────────────────────────────────
function InteractiveBracketView() {
  const [rankings, setRankings] = useState<Record<string, string[]>>({ ...GROUP_TEAMS });
  const [dragState, setDragState] = useState<{ group: string; fromIdx: number } | null>(null);

  const handleDrop = (toGroup: string, toIdx: number) => {
    if (!dragState || dragState.group !== toGroup || dragState.fromIdx === toIdx) {
      setDragState(null);
      return;
    }
    setRankings(prev => {
      const arr = [...prev[toGroup]];
      const [removed] = arr.splice(dragState.fromIdx, 1);
      arr.splice(toIdx, 0, removed);
      return { ...prev, [toGroup]: arr };
    });
    setDragState(null);
  };

  const leftMatches = R32_MATCHES.filter(m => m.side === 'L');
  const rightMatches = R32_MATCHES.filter(m => m.side === 'R');

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="flex items-start gap-3 bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-sm">
        <span className="text-xl flex-shrink-0">🎮</span>
        <div>
          <p className="text-blue-300 font-semibold mb-0.5">Simulador interactivo</p>
          <p className="text-slate-400">Arrastra los equipos dentro de cada grupo para cambiar posiciones. El bracket de arriba se actualiza automáticamente.</p>
        </div>
      </div>

      {/* Bracket preview */}
      <div>
        <h3 className="text-white font-bold text-base mb-3">Round of 32 — Vista del Bracket</h3>
        <div className="overflow-x-auto pb-2">
          <div className="flex items-stretch gap-1 min-w-max">
            {/* Left half */}
            <BracketHalf matches={leftMatches} rankings={rankings} side="L" />

            {/* Final */}
            <div className="flex flex-col items-center justify-center px-4 gap-3">
              <span className="text-4xl">🏆</span>
              <div className="text-center">
                <p className="text-yellow-400 font-black text-xs uppercase tracking-widest">FINAL</p>
                <p className="text-slate-500 text-xs">19 Jul · NY</p>
              </div>
              <div className="bg-slate-800 border-2 border-yellow-400/50 rounded-xl overflow-hidden w-36">
                <div className="px-2 py-1 bg-yellow-400/10 border-b border-yellow-400/20">
                  <span className="text-xs font-black text-yellow-400">CAMPEÓN</span>
                </div>
                <div className="flex items-center gap-2 px-2 py-2">
                  <span className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center text-slate-500 text-xs flex-shrink-0">?</span>
                  <span className="text-xs text-slate-500">Semi 1</span>
                </div>
                <div className="mx-2 h-px bg-slate-700" />
                <div className="flex items-center gap-2 px-2 py-2">
                  <span className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center text-slate-500 text-xs flex-shrink-0">?</span>
                  <span className="text-xs text-slate-500">Semi 2</span>
                </div>
              </div>
            </div>

            {/* Right half */}
            <BracketHalf matches={rightMatches} rankings={rankings} side="R" />
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-slate-700" />
        <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Reordena los grupos</span>
        <div className="flex-1 h-px bg-slate-700" />
      </div>

      {/* Group editors */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {GROUPS.map(g => (
          <DraggableGroupCard
            key={g}
            group={g}
            ranking={rankings[g]}
            dragState={dragState}
            onDragStart={(grp, idx) => setDragState({ group: grp, fromIdx: idx })}
            onDrop={handleDrop}
            onDragEnd={() => setDragState(null)}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-500 pt-2">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500"></span>Clasificado directo (R32)</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-yellow-500"></span>Posible 3er clasificado</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-600"></span>Eliminado</span>
      </div>
    </div>
  );
}


function BracketView() {
  return <InteractiveBracketView />;
}

// ── Main component ────────────────────────────────────────────────────
interface Props {
  matches: Match[];
  initialGroup?: string | null;
}

export default function WorldCupDashboard({ matches, initialGroup }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedGroup, setSelectedGroup] = useState<string | null>(() => {
    if (initialGroup && GROUPS.includes(initialGroup)) return initialGroup;
    const fromSearch = new URLSearchParams(window.location.search).get('group');
    return fromSearch && GROUPS.includes(fromSearch) ? fromSearch : null;
  });
  const [activeTab, setActiveTab] = useState<Tab>('matches');
  const [groupMatches, setGroupMatches] = useState<GroupMatch[]>([]);
  const [loadingStandings, setLoadingStandings] = useState(false);

  useEffect(() => {
    if (activeTab === 'standings' && groupMatches.length === 0) {
      setLoadingStandings(true);
      fetch(`${API_URL}/api/wc2026/group-matches`)
        .then(r => r.json())
        .then(data => setGroupMatches(data))
        .catch(console.error)
        .finally(() => setLoadingStandings(false));
    }
  }, [activeTab]);

  const handleSelectGroup = (g: string | null) => {
    setSelectedGroup(g);
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (g) next.set('group', g);
      else next.delete('group');
      return next;
    });
  };

  const matchesByGroup: Record<string, Match[]> = {};
  for (const m of matches) {
    const g = getMatchGroup(m);
    if (!matchesByGroup[g]) matchesByGroup[g] = [];
    matchesByGroup[g].push(m);
  }

  const groupsToShow = selectedGroup ? [selectedGroup] : GROUPS.filter(g => matchesByGroup[g]?.length);

  return (
    <div className="min-h-screen bg-slate-900 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <WorldCupBanner matchCount={matches.length} />
        <TabNav active={activeTab} onChange={setActiveTab} />

        {activeTab !== 'bracket' && (
          <GroupSelector
            selected={selectedGroup}
            onSelect={handleSelectGroup}
          />
        )}

        {activeTab === 'matches' && (
          matches.length === 0 ? (
            <div className="text-center py-16 text-slate-500">
              <div className="text-5xl mb-4">⏳</div>
              <p className="text-lg">Cargando predicciones del Mundial...</p>
            </div>
          ) : (
            <div className="space-y-8">
              {groupsToShow.map(g => (
                <section key={g}>
                  <GroupHeader group={g} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4">
                    {(matchesByGroup[g] ?? []).map(m => (
                      <WCMatchCard key={m.match_id} match={m} group={g} currentSearchParams={searchParams.toString()} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )
        )}

        {activeTab === 'standings' && (
          <StandingsView
            allMatches={groupMatches}
            selectedGroup={selectedGroup}
            loading={loadingStandings}
          />
        )}

        {activeTab === 'bracket' && <BracketView />}
      </div>
    </div>
  );
}
