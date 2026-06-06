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

// Round of 32 cross-group matchup: 1st of group X faces 2nd of group Y
// e.g. 'A' -> 'C' means 1st of A faces 2nd of C, and 2nd of A faces 1st of C
const R32_CROSS: Record<string, string> = {
  'A': 'C', 'C': 'A', 'B': 'D', 'D': 'B',
  'E': 'G', 'G': 'E', 'F': 'H', 'H': 'F',
  'I': 'K', 'K': 'I', 'J': 'L', 'L': 'J',
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
  matchesByGroup,
  onSelect,
}: {
  selected: string | null;
  matchesByGroup: Record<string, unknown[]>;
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

// ── Bracket / Routes view ─────────────────────────────────────────────
function RouteCard({ group }: { group: string }) {
  const crossGroup = R32_CROSS[group] || '?';
  const teams = GROUP_TEAMS[group] ?? [];

  const positions = [
    {
      pos: 1,
      medal: '🥇',
      label: '1er lugar',
      status: 'CLASIFICADO',
      statusColor: 'text-green-400 bg-green-400/10 border-green-400/30',
      detail: `R32 vs 2º Grupo ${crossGroup}`,
      path: ['R32', 'Octavos', 'Cuartos', 'Semis', 'Final'],
      borderColor: 'border-l-green-500',
    },
    {
      pos: 2,
      medal: '🥈',
      label: '2do lugar',
      status: 'CLASIFICADO',
      statusColor: 'text-green-400 bg-green-400/10 border-green-400/30',
      detail: `R32 vs 1º Grupo ${crossGroup}`,
      path: ['R32', 'Octavos', 'Cuartos', 'Semis', 'Final'],
      borderColor: 'border-l-green-500',
    },
    {
      pos: 3,
      medal: '🥉',
      label: '3er lugar',
      status: 'POSIBLE',
      statusColor: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
      detail: 'Si es uno de los 8 mejores 3eros → R32',
      path: ['(R32)', 'Octavos', 'Cuartos', 'Semis', 'Final'],
      borderColor: 'border-l-yellow-500',
    },
    {
      pos: 4,
      medal: '4️⃣',
      label: '4to lugar',
      status: 'ELIMINADO',
      statusColor: 'text-red-400 bg-red-400/10 border-red-400/30',
      detail: 'No avanza a la fase eliminatoria',
      path: [],
      borderColor: 'border-l-slate-700',
    },
  ];

  return (
    <div className="mb-8">
      <GroupHeader group={group} />
      <div className="space-y-3">
        {positions.map((pos) => (
          <div
            key={pos.pos}
            className={`bg-slate-800 rounded-xl border border-slate-700 border-l-4 ${pos.borderColor} overflow-hidden`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4">
              {/* Position + team name */}
              <div className="flex items-center gap-3 min-w-0 sm:w-48">
                <span className="text-2xl">{pos.medal}</span>
                <div className="min-w-0">
                  <p className="text-xs text-slate-500 font-medium">{pos.label}</p>
                  {teams[pos.pos - 1] && (
                    <p className="text-sm font-bold text-white truncate">
                      {TEAM_FLAG[teams[pos.pos - 1]]} {teams[pos.pos - 1]}
                    </p>
                  )}
                </div>
              </div>

              {/* Status badge */}
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full border self-start sm:self-center flex-shrink-0 ${pos.statusColor}`}>
                {pos.status}
              </span>

              {/* Detail + path */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-400 mb-2">{pos.detail}</p>
                {pos.path.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    {pos.path.map((round, idx) => (
                      <div key={round} className="flex items-center gap-1">
                        <span className={`text-xs px-2 py-0.5 rounded font-semibold
                          ${idx === 0 ? 'bg-slate-700 text-slate-300'
                          : idx === pos.path.length - 1 ? 'bg-yellow-400/20 text-yellow-300 border border-yellow-400/30'
                          : 'bg-slate-700/50 text-slate-400'}`}>
                          {round}
                        </span>
                        {idx < pos.path.length - 1 && (
                          <span className="text-slate-600 text-xs">→</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BracketView({ selectedGroup }: { selectedGroup: string | null }) {
  const groupsToShow = selectedGroup ? [selectedGroup] : GROUPS;

  return (
    <div>
      {/* Info banner */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 mb-6 text-sm text-slate-400 flex gap-3">
        <span className="text-xl flex-shrink-0">ℹ️</span>
        <div>
          <p className="text-white font-semibold mb-1">Formato de clasificación</p>
          <p>Los <strong className="text-green-400">2 primeros</strong> de cada grupo avanzan directamente al Round of 32.
          Los <strong className="text-yellow-400">8 mejores terceros</strong> de los 12 grupos también clasifican.
          El <strong className="text-slate-300">4to lugar</strong> queda eliminado.</p>
        </div>
      </div>

      {groupsToShow.map(g => (
        <RouteCard key={g} group={g} />
      ))}
    </div>
  );
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

        <GroupSelector
          selected={selectedGroup}
          matchesByGroup={matchesByGroup}
          onSelect={handleSelectGroup}
        />

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

        {activeTab === 'bracket' && (
          <BracketView selectedGroup={selectedGroup} />
        )}
      </div>
    </div>
  );
}
