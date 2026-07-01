import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import WC2026StatsModule from './WC2026StatsModule';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

interface Match {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
  referee?: string | null;
  // Actual result (null = not played yet)
  home_goals: number | null;
  away_goals: number | null;
  actual_result: 'H' | 'D' | 'A' | null;
  penalty_winner: string | null;
  // Poisson predictions
  poisson_home_goals: number;
  poisson_away_goals: number;
  poisson_prob_home: number;
  poisson_prob_draw: number;
  poisson_prob_away: number;
  poisson_over_25: number;
  poisson_btts: number;
  // Weinston predictions
  weinston_home_goals: number;
  weinston_away_goals: number;
  weinston_prob_home: number;
  weinston_prob_draw: number;
  weinston_prob_away: number;
  weinston_result: string;
  weinston_over_25: number;
  weinston_btts: number;
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
const WC_KNOCKOUT_START = '2026-06-28'; // Group stage ends June 26; knockout starts June 28

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
type Tab = 'matches' | 'standings' | 'bracket' | 'news' | 'stats' | 'today';

function TabNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'today',     label: 'Hoy',           icon: '📅' },
    { id: 'matches',   label: 'Partidos',      icon: '⚽' },
    { id: 'standings', label: 'Posiciones',    icon: '📊' },
    { id: 'bracket',   label: 'Bracket',       icon: '🗺️' },
    { id: 'stats',     label: 'Estadísticas',  icon: '🏅' },
    { id: 'news',      label: 'Noticias',      icon: '📰' },
  ];
  return (
    <div className="bg-slate-800/60 p-1 rounded-xl mb-6 border border-slate-700/50 overflow-x-auto scrollbar-hide">
      <div className="flex gap-1">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`flex-shrink-0 flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-lg
                        text-sm font-semibold transition-all whitespace-nowrap
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
    </div>
  );
}

// ── Group selector ────────────────────────────────────────────────────
function GroupSelector({
  selected,
  onSelect,
  showR32 = false,
}: {
  selected: string | null;
  onSelect: (g: string | null) => void;
  showR32?: boolean;
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

        {showR32 && (
          <>
            <div className="w-px bg-slate-700 self-stretch mx-1 flex-shrink-0" />
            <button
              onClick={() => onSelect('16avos')}
              className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all border
                ${selected === '16avos'
                  ? 'bg-yellow-400 text-slate-900 border-yellow-400 shadow-lg shadow-yellow-400/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'
                }`}
            >
              <span>🎯</span>
              <span>16avos</span>
            </button>
            <div className="w-px bg-slate-700 self-stretch mx-1 flex-shrink-0" />
          </>
        )}

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

  const isCompleted = match.home_goals != null && match.away_goals != null;

  // Weinston probs with Poisson fallback
  const homeProb = safeNum(match.weinston_prob_home ?? match.poisson_prob_home);
  const drawProb = safeNum(match.weinston_prob_draw ?? match.poisson_prob_draw);
  const awayProb = safeNum(match.weinston_prob_away ?? match.poisson_prob_away);
  const total = homeProb + drawProb + awayProb || 1;
  const homeP = (homeProb / total) * 100;
  const drawP = (drawProb / total) * 100;
  const awayP = (awayProb / total) * 100;

  const favorite = homeProb > awayProb && homeProb > drawProb ? 'home'
    : awayProb > homeProb && awayProb > drawProb ? 'away'
    : 'draw';

  const pHomeGoals = safeNum(match.weinston_home_goals);
  const pAwayGoals = safeNum(match.weinston_away_goals);
  const overProb = safeNum(match.weinston_over_25 ?? match.poisson_over_25);
  const bttsProb = safeNum(match.weinston_btts ?? match.poisson_btts);
  const hasPredictions = match.weinston_home_goals != null || match.weinston_prob_home != null;

  // Prediction accuracy (only meaningful when completed)
  const predictedResult = homeP > awayP && homeP > drawP ? 'H'
    : awayP > homeP && awayP > drawP ? 'A' : 'D';
  const result1x2Hit  = isCompleted && predictedResult === match.actual_result;
  const result1x2Miss = isCompleted && predictedResult !== match.actual_result;

  const predictedOver  = overProb >= 0.5;
  const actualTotalGoals = isCompleted ? (match.home_goals! + match.away_goals!) : null;
  const actualOver     = actualTotalGoals != null ? actualTotalGoals > 2 : null;
  const overHit        = isCompleted && predictedOver === actualOver;
  const overMiss       = isCompleted && predictedOver !== actualOver;

  const predictedBtts  = bttsProb >= 0.5;
  const actualBtts     = isCompleted ? (match.home_goals! > 0 && match.away_goals! > 0) : null;
  const bttsHit        = isCompleted && predictedBtts === actualBtts;
  const bttsMiss       = isCompleted && predictedBtts !== actualBtts;

  // Score display usa floor (consistente entre partidos por jugar y completados)
  const predHomeFloor = Math.floor(pHomeGoals);
  const predAwayFloor = Math.floor(pAwayGoals);
  const isExactScoreHit = isCompleted &&
    predHomeFloor === match.home_goals &&
    predAwayFloor === match.away_goals;

  return (
    <div
      onClick={() => navigate(`/match/${match.match_id}`, { state: { group, returnSearch: currentSearchParams } })}
      className={`border rounded-xl overflow-hidden transition-all cursor-pointer group
        ${isCompleted
          ? 'bg-slate-800/70 border-slate-600 hover:border-slate-500'
          : 'bg-slate-800 border-slate-700 hover:border-yellow-400/40 hover:bg-slate-750'
        }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 sm:px-4 pt-3 pb-2 border-b border-slate-700/50">
        <span className="text-xs font-bold text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded">
          {group === 'R32' ? 'Dieciseisavos de Final' : `Grupo ${group}`}
        </span>
        <div className="flex items-center gap-2">
          {isCompleted && (
            <span className="text-[10px] font-bold text-slate-400 bg-slate-700 px-1.5 py-0.5 rounded uppercase tracking-wide">
              Final
            </span>
          )}
          <span className="text-xs text-slate-400">{formatDate(match.date)}</span>
        </div>
      </div>

      {/* Teams + Score */}
      <div className="px-3 sm:px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className={`flex-1 text-right ${!isCompleted && favorite === 'home' ? 'opacity-100' : isCompleted && match.actual_result === 'H' ? 'opacity-100' : 'opacity-70'}`}>
            <div className="text-2xl mb-1">{homeFlag}</div>
            <div className="text-xs sm:text-sm font-bold leading-tight text-slate-200">
              {match.home_team}
            </div>
          </div>

          <div className="flex-shrink-0 text-center px-2">
            {isCompleted ? (
              <div className="bg-slate-900 rounded-lg px-3 py-2 border border-slate-500 min-w-[96px]">
                <div className="text-white font-black text-lg sm:text-xl font-mono leading-none">
                  {match.home_goals} — {match.away_goals}
                </div>
                <div className="text-slate-400 text-xs mt-1">Resultado Final</div>
                {hasPredictions && (
                  <div className="flex items-center justify-center gap-1 mt-1.5 pt-1.5 border-t border-slate-700/60">
                    <span className="text-slate-500 text-[10px]">Pred.</span>
                    <span className={`text-xs font-mono font-semibold ${isExactScoreHit ? 'text-green-400' : 'text-slate-400'}`}>
                      {predHomeFloor}—{predAwayFloor}
                    </span>
                    <span className="text-[11px] leading-none">{isExactScoreHit ? '✅' : '❌'}</span>
                  </div>
                )}
              </div>
            ) : hasPredictions ? (
              <div className="bg-slate-900 rounded-lg px-3 py-2 border border-slate-600">
                <div className="text-white font-black text-lg sm:text-xl font-mono">
                  {predHomeFloor} — {predAwayFloor}
                </div>
                <div className="text-slate-500 text-xs mt-0.5">marcador esperado</div>
              </div>
            ) : (
              <div className="text-slate-500 text-sm font-bold px-3">vs</div>
            )}
          </div>

          <div className={`flex-1 text-left ${!isCompleted && favorite === 'away' ? 'opacity-100' : isCompleted && match.actual_result === 'A' ? 'opacity-100' : 'opacity-70'}`}>
            <div className="text-2xl mb-1">{awayFlag}</div>
            <div className="text-xs sm:text-sm font-bold leading-tight text-slate-200">
              {match.away_team}
            </div>
          </div>
        </div>
      </div>

      {hasPredictions && (
        <div className="px-3 sm:px-4 pb-4 space-y-3">
          {/* Probability bars */}
          <div>
            <div className="flex text-xs justify-between mb-1">
              <span className={`font-bold ${
                result1x2Hit && match.actual_result === 'H' ? 'text-green-400' :
                result1x2Miss && predictedResult === 'H' ? 'text-red-400' :
                !isCompleted && favorite === 'home' ? 'text-green-400' : 'text-slate-400'
              }`}>{homeP.toFixed(0)}%</span>
              <span className={`font-${result1x2Hit && match.actual_result === 'D' ? 'bold' : 'normal'} ${
                result1x2Hit && match.actual_result === 'D' ? 'text-green-400' :
                result1x2Miss && predictedResult === 'D' ? 'text-red-400' :
                !isCompleted && favorite === 'draw' ? 'text-yellow-400' : 'text-slate-400'
              }`}>Empate {drawP.toFixed(0)}%</span>
              <span className={`font-bold ${
                result1x2Hit && match.actual_result === 'A' ? 'text-green-400' :
                result1x2Miss && predictedResult === 'A' ? 'text-red-400' :
                !isCompleted && favorite === 'away' ? 'text-green-400' : 'text-slate-400'
              }`}>{awayP.toFixed(0)}%</span>
            </div>
            <div className={`flex h-2 rounded-full overflow-hidden gap-px bg-slate-900 ${
              isCompleted ? 'opacity-60' : ''
            }`}>
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
            {/* 1x2 result badge — uses probability prediction (most faithful to the model) */}
            {isCompleted && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-bold
                ${result1x2Hit
                  ? 'bg-green-600 border-green-500 text-white'
                  : 'bg-red-600/30 border-red-500/50 text-red-400'
                }`}>
                {result1x2Hit ? '✅' : '❌'} {predictedResult === 'H' ? 'Local' : predictedResult === 'A' ? 'Visit.' : 'Empate'}
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
              ${overHit ? 'bg-green-600 border-green-500 text-white' :
                overMiss ? 'bg-red-600/30 border-red-500/50 text-red-400' :
                overProb >= 0.5
                ? 'text-green-400 border-green-400/30 bg-green-400/10'
                : 'text-orange-400 border-orange-400/30 bg-orange-400/10'
              }`}>
              {isCompleted ? (overHit ? '✅ ' : '❌ ') : ''}
              {overProb >= 0.5 ? `Over 2.5 · ${(overProb * 100).toFixed(0)}%` : `Under 2.5 · ${((1 - overProb) * 100).toFixed(0)}%`}
            </span>
            {bttsProb > 0 && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
                ${bttsHit ? 'bg-green-600 border-green-500 text-white' :
                  bttsMiss ? 'bg-red-600/30 border-red-500/50 text-red-400' :
                  bttsProb >= 0.5
                  ? 'text-purple-400 border-purple-400/30 bg-purple-400/10'
                  : 'text-slate-400 border-slate-600 bg-slate-700/50'
                }`}>
                {isCompleted ? (bttsHit ? '✅ ' : '❌ ') : ''}BTTS {(bttsProb * 100).toFixed(0)}%
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

// ── (Interactive bracket removed — replaced by RealR32View) ──────────

// Confirmed third-place assignments from the official WC 2026 R32 bracket.
// All 8 third-place slots are now known from the published bracket.
const CONFIRMED_R32_THIRDS: Record<number, string> = {
  1:  'D',  // Germany  (E#1) vs Paraguay          (D 3rd)
  2:  'F',  // France   (I#1) vs Sweden             (F 3rd)
  7:  'B',  // USA      (D#1) vs Bosnia-Herzegovina (B 3rd)
  8:  'I',  // Belgium  (G#1) vs Senegal            (I 3rd)
  11: 'E',  // Mexico   (A#1) vs Ecuador            (E 3rd)
  12: 'K',  // England  (L#1) vs Congo DR           (K 3rd)
  15: 'J',  // Switzerland (B#1) vs Algeria         (J 3rd)
  16: 'L',  // Colombia (K#1) vs Ghana              (L 3rd)
};

type BracketSlot =
  | { kind: 'pos'; group: string; pos: 0 | 1 }
  | { kind: 'third'; fromGroups: string[] };

interface R32Match {
  num: number;
  slotA: BracketSlot;
  slotB: BracketSlot;
  side: 'L' | 'R';
}

// Official 2026 WC Round of 32 bracket matchups
// fromGroups: eligible groups for each third-place slot (adjusted to match actual 2026 WC assignments)
const R32_MATCHES: R32Match[] = [
  // ── Left half ──────────────────────────────────────────────────────
  { num: 1,  side: 'L', slotA: { kind: 'pos', group: 'E', pos: 0 }, slotB: { kind: 'third', fromGroups: ['A','C','D','F'] } },
  { num: 2,  side: 'L', slotA: { kind: 'pos', group: 'I', pos: 0 }, slotB: { kind: 'third', fromGroups: ['F','G','H','K'] } },
  { num: 3,  side: 'L', slotA: { kind: 'pos', group: 'A', pos: 1 }, slotB: { kind: 'pos', group: 'B', pos: 1 } },
  { num: 4,  side: 'L', slotA: { kind: 'pos', group: 'F', pos: 0 }, slotB: { kind: 'pos', group: 'C', pos: 1 } },
  { num: 5,  side: 'L', slotA: { kind: 'pos', group: 'K', pos: 1 }, slotB: { kind: 'pos', group: 'L', pos: 1 } },
  { num: 6,  side: 'L', slotA: { kind: 'pos', group: 'H', pos: 0 }, slotB: { kind: 'pos', group: 'J', pos: 1 } },
  { num: 7,  side: 'L', slotA: { kind: 'pos', group: 'D', pos: 0 }, slotB: { kind: 'third', fromGroups: ['B','E','F','I'] } },
  { num: 8,  side: 'L', slotA: { kind: 'pos', group: 'G', pos: 0 }, slotB: { kind: 'third', fromGroups: ['A','E','H','I'] } },
  // ── Right half ─────────────────────────────────────────────────────
  { num: 9,  side: 'R', slotA: { kind: 'pos', group: 'C', pos: 0 }, slotB: { kind: 'pos', group: 'F', pos: 1 } },
  { num: 10, side: 'R', slotA: { kind: 'pos', group: 'E', pos: 1 }, slotB: { kind: 'pos', group: 'I', pos: 1 } },
  { num: 11, side: 'R', slotA: { kind: 'pos', group: 'A', pos: 0 }, slotB: { kind: 'third', fromGroups: ['E','F','G','H'] } },
  { num: 12, side: 'R', slotA: { kind: 'pos', group: 'L', pos: 0 }, slotB: { kind: 'third', fromGroups: ['E','H','I','K'] } },
  { num: 13, side: 'R', slotA: { kind: 'pos', group: 'J', pos: 0 }, slotB: { kind: 'pos', group: 'H', pos: 1 } },
  { num: 14, side: 'R', slotA: { kind: 'pos', group: 'D', pos: 1 }, slotB: { kind: 'pos', group: 'G', pos: 1 } },
  { num: 15, side: 'R', slotA: { kind: 'pos', group: 'B', pos: 0 }, slotB: { kind: 'third', fromGroups: ['E','F','G','J'] } },
  { num: 16, side: 'R', slotA: { kind: 'pos', group: 'K', pos: 0 }, slotB: { kind: 'third', fromGroups: ['E','H','I','J','K','L'] } },
];

// Bracket connectivity: which two matches feed each subsequent match
const BRACKET_PAIRS: Record<string, [string, string]> = {
  'R16-1': ['R32-1',  'R32-2'],  'R16-2': ['R32-3',  'R32-4'],
  'R16-3': ['R32-5',  'R32-6'],  'R16-4': ['R32-7',  'R32-8'],
  'R16-5': ['R32-9',  'R32-10'], 'R16-6': ['R32-11', 'R32-12'],
  'R16-7': ['R32-13', 'R32-14'], 'R16-8': ['R32-15', 'R32-16'],
  'QF-1':  ['R16-1', 'R16-2'],  'QF-2':  ['R16-3', 'R16-4'],
  'QF-3':  ['R16-5', 'R16-6'],  'QF-4':  ['R16-7', 'R16-8'],
  'SF-1':  ['QF-1',  'QF-2'],   'SF-2':  ['QF-3',  'QF-4'],
  'Final': ['SF-1',  'SF-2'],
};

// Resolve which team occupies a bracket slot
function resolveTeam(
  matchId: string,
  pos: 'a' | 'b',
  rankings: Record<string, string[]>,
  thirdPicks: Record<number, string>,
  winners: Record<string, string>,
): string | null {
  if (matchId.startsWith('R32-')) {
    const num = parseInt(matchId.split('-')[1]);
    const match = R32_MATCHES.find(m => m.num === num);
    if (!match) return null;
    const slot = pos === 'a' ? match.slotA : match.slotB;
    if (slot.kind === 'pos') return rankings[slot.group]?.[slot.pos] ?? null;
    const group = thirdPicks[num];
    return group ? (rankings[group]?.[2] ?? null) : null;
  }
  const pair = BRACKET_PAIRS[matchId];
  if (!pair) return null;
  return winners[pos === 'a' ? pair[0] : pair[1]] ?? null;
}


// Shared team row ─────────────────────────────────────────────────────
function TeamRow({
  team, winner, canPick, onClick, badge, thirdLabel,
}: {
  team: string | null;
  winner: string | null;
  canPick: boolean;
  onClick: () => void;
  badge?: { text: string; cls: string };
  thirdLabel?: string;
}) {
  const isWinner = !!team && team === winner;
  const isLoser  = !!winner && team !== winner;
  return (
    <div
      onClick={canPick && !!team ? onClick : undefined}
      className={`flex items-center gap-1.5 px-2 py-2 min-w-0 transition-all
        ${canPick && team ? 'cursor-pointer' : ''}
        ${isWinner ? 'bg-green-500/20' : ''}
        ${isLoser  ? 'opacity-30' : ''}
        ${canPick && team && !winner ? 'hover:bg-slate-700/60' : ''}`}
    >
      {badge && (
        <span className={`text-xs font-bold px-1 rounded flex-shrink-0 ${badge.cls}`}>{badge.text}</span>
      )}
      {team ? (
        <>
          <span className="text-sm leading-none flex-shrink-0">{TEAM_FLAG[team] ?? '🏳'}</span>
          <span className="text-xs font-semibold text-white truncate flex-1">{team}</span>
          {isWinner && <span className="text-green-400 text-xs flex-shrink-0">✓</span>}
        </>
      ) : (
        <span className={`text-xs italic truncate ${thirdLabel ? 'text-yellow-500/60' : 'text-slate-600'}`}>
          {thirdLabel ?? 'Ganador'}
        </span>
      )}
    </div>
  );
}

// R32 match card ──────────────────────────────────────────────────────
function R32Card({
  match, rankings, thirdPicks, winners, onPickWinner, isTopOfPair, isBottomOfPair,
}: {
  match: R32Match;
  rankings: Record<string, string[]>;
  thirdPicks: Record<number, string>;
  winners: Record<string, string>;
  onPickWinner: (matchId: string, team: string) => void;
  isTopOfPair: boolean;
  isBottomOfPair: boolean;
}) {
  const matchId = `R32-${match.num}`;
  const teamA = resolveTeam(matchId, 'a', rankings, thirdPicks, winners);
  const teamB = resolveTeam(matchId, 'b', rankings, thirdPicks, winners);
  const winner = winners[matchId] ?? null;
  const canPick = !!teamA && !!teamB;

  const badgeFor = (slot: BracketSlot) => {
    if (slot.kind === 'third') return { text: '3°', cls: 'text-yellow-400 bg-yellow-400/10' };
    if (slot.pos === 0)        return { text: '1°', cls: 'text-green-400 bg-green-400/10' };
    return { text: '2°', cls: 'text-blue-400 bg-blue-400/10' };
  };

  const thirdLabelFor = (slot: BracketSlot) =>
    slot.kind === 'third' ? `3° (${slot.fromGroups.join('')})` : undefined;

  const connectorStyle = isTopOfPair
    ? 'rounded-t-xl rounded-br-none border-b-0 border-r-2 border-r-yellow-400/40'
    : isBottomOfPair
    ? 'rounded-b-xl rounded-tr-none border-r-2 border-r-yellow-400/40'
    : 'rounded-xl';

  return (
    <div className={`bg-slate-800 border border-slate-700 overflow-hidden ${connectorStyle}`}>
      <div className="flex items-center justify-between px-2 py-1 bg-slate-900/60 border-b border-slate-700/50">
        <span className="text-xs text-slate-500 font-bold">M{match.num}</span>
        {winner && (
          <button
            onClick={() => onPickWinner(matchId, '')}
            className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            title="Deshacer selección"
          >↺</button>
        )}
      </div>
      <TeamRow team={teamA} winner={winner} canPick={canPick}
        onClick={() => teamA && onPickWinner(matchId, teamA)}
        badge={badgeFor(match.slotA)} thirdLabel={thirdLabelFor(match.slotA)} />
      <div className="mx-2 h-px bg-slate-700" />
      <TeamRow team={teamB} winner={winner} canPick={canPick}
        onClick={() => teamB && onPickWinner(matchId, teamB)}
        badge={badgeFor(match.slotB)} thirdLabel={thirdLabelFor(match.slotB)} />
    </div>
  );
}

// Clickable match card for R16/QF/SF/Final ────────────────────────────
function ClickableMatchCard({
  matchId, rankings, thirdPicks, winners, onPickWinner, label,
}: {
  matchId: string;
  rankings: Record<string, string[]>;
  thirdPicks: Record<number, string>;
  winners: Record<string, string>;
  onPickWinner: (matchId: string, team: string) => void;
  label: string;
}) {
  const teamA = resolveTeam(matchId, 'a', rankings, thirdPicks, winners);
  const teamB = resolveTeam(matchId, 'b', rankings, thirdPicks, winners);
  const winner = winners[matchId] ?? null;
  const canPick = !!teamA && !!teamB;
  const isFinal = matchId === 'Final';

  return (
    <div className={`border rounded-xl overflow-hidden w-40
      ${isFinal ? 'border-2 border-yellow-400/60 bg-yellow-400/5' : 'border border-dashed border-slate-600 bg-slate-800/50'}`}>
      <div className="flex items-center justify-between px-2 py-1 bg-slate-900/40 border-b border-slate-700/40">
        <span className={`text-xs font-bold ${isFinal ? 'text-yellow-400' : 'text-slate-500'}`}>{label}</span>
        {winner && (
          <button
            onClick={() => onPickWinner(matchId, '')}
            className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            title="Deshacer selección"
          >↺</button>
        )}
      </div>
      <TeamRow team={teamA} winner={winner} canPick={canPick}
        onClick={() => teamA && onPickWinner(matchId, teamA)} />
      <div className="mx-2 h-px bg-slate-700/50" />
      <TeamRow team={teamB} winner={winner} canPick={canPick}
        onClick={() => teamB && onPickWinner(matchId, teamB)} />
    </div>
  );
}

// Bracket half (left or right) ────────────────────────────────────────
function BracketHalf({
  matches, rankings, thirdPicks, winners, onPickWinner, side,
}: {
  matches: R32Match[];
  rankings: Record<string, string[]>;
  thirdPicks: Record<number, string>;
  winners: Record<string, string>;
  onPickWinner: (matchId: string, team: string) => void;
  side: 'L' | 'R';
}) {
  const pairs = [
    [matches[0], matches[1]], [matches[2], matches[3]],
    [matches[4], matches[5]], [matches[6], matches[7]],
  ];

  const sharedProps = { rankings, thirdPicks, winners, onPickWinner };

  const r32 = (
    <div className="space-y-3">
      {pairs.map((pair, pi) => (
        <div key={pi} className="space-y-0">
          <R32Card match={pair[0]} {...sharedProps} isTopOfPair isBottomOfPair={false} />
          <R32Card match={pair[1]} {...sharedProps} isTopOfPair={false} isBottomOfPair />
        </div>
      ))}
    </div>
  );

  const connector = (count: number, key: string) => (
    <div key={key} className="flex flex-col justify-around py-4"
      style={{ gap: count === 4 ? '0.75rem' : count === 2 ? '3.5rem' : '8.5rem' }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center">
          <div className="w-3 h-px bg-slate-600" />
        </div>
      ))}
    </div>
  );

  const r16Offset = side === 'R' ? 4 : 0;
  const qfOffset  = side === 'R' ? 2 : 0;

  const r16 = (
    <div className="flex flex-col justify-around py-1" style={{ gap: '1.5rem' }}>
      {[0,1,2,3].map(i => (
        <ClickableMatchCard key={i} matchId={`R16-${i+1+r16Offset}`}
          label={`R16 M${i+1+r16Offset}`} {...sharedProps} />
      ))}
    </div>
  );

  const qf = (
    <div className="flex flex-col justify-around py-1" style={{ gap: '5.5rem' }}>
      {[0,1].map(i => (
        <ClickableMatchCard key={i} matchId={`QF-${i+1+qfOffset}`}
          label={`QF M${i+1+qfOffset}`} {...sharedProps} />
      ))}
    </div>
  );

  const sf = (
    <div className="flex items-center justify-center h-full">
      <ClickableMatchCard matchId={`SF-${side === 'R' ? 2 : 1}`}
        label={`SF M${side === 'R' ? 2 : 1}`} {...sharedProps} />
    </div>
  );

  const columns = side === 'L'
    ? [r32, connector(4,'c1'), r16, connector(2,'c2'), qf, connector(1,'c3'), sf]
    : [sf, connector(1,'c3'), qf, connector(2,'c2'), r16, connector(4,'c1'), r32];

  return <div className="flex items-stretch gap-0">{columns}</div>;
}



// ── News ──────────────────────────────────────────────────────────────
interface NewsArticle {
  title: string;
  description: string | null;
  image: string | null;
  url: string;
  source: string;
  published_at: string;
}

function formatRelativeDate(isoStr: string): string {
  try {
    const diffMs = Date.now() - new Date(isoStr).getTime();
    const diffM = Math.floor(diffMs / 60000);
    if (diffM < 2) return 'ahora';
    if (diffM < 60) return `hace ${diffM}m`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `hace ${diffH}h`;
    const diffD = Math.floor(diffH / 24);
    if (diffD === 1) return 'ayer';
    return `hace ${diffD} días`;
  } catch {
    return '';
  }
}

// Gradient backgrounds for articles without images
const CARD_GRADIENTS = [
  'from-blue-900/60 to-slate-900',
  'from-emerald-900/60 to-slate-900',
  'from-amber-900/60 to-slate-900',
  'from-purple-900/60 to-slate-900',
  'from-rose-900/60 to-slate-900',
];

function NewsCard({ article, index }: { article: NewsArticle; index: number }) {
  const [imgError, setImgError] = useState(false);
  const gradient = CARD_GRADIENTS[index % CARD_GRADIENTS.length];
  const showImg = article.image && !imgError;

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col overflow-hidden rounded-xl border border-slate-700/50
                 hover:border-yellow-500/40 hover:shadow-lg hover:shadow-yellow-400/5
                 transition-all group bg-slate-800/60"
    >
      {/* Image / gradient header */}
      <div className="relative w-full h-44 overflow-hidden flex-shrink-0">
        {showImg ? (
          <img
            src={article.image!}
            alt={article.title}
            loading="lazy"
            onError={() => setImgError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${gradient} flex items-center justify-center`}>
            <span className="text-5xl opacity-30">⚽</span>
          </div>
        )}
        {/* Source badge over image */}
        <span className="absolute top-2 left-2 bg-black/60 backdrop-blur-sm text-white text-[11px]
                         font-semibold px-2 py-0.5 rounded-full">
          {article.source}
        </span>
        {/* Date badge */}
        <span className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm text-slate-300 text-[11px]
                         px-2 py-0.5 rounded-full">
          {formatRelativeDate(article.published_at)}
        </span>
      </div>

      {/* Text content */}
      <div className="flex flex-col gap-2 p-4 flex-1">
        <h3 className="text-white font-semibold text-sm leading-snug line-clamp-2
                       group-hover:text-yellow-400 transition-colors">
          {article.title}
        </h3>
        {article.description && (
          <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
            {article.description}
          </p>
        )}
        <span className="mt-auto pt-2 text-xs text-yellow-500/70 font-medium group-hover:text-yellow-400 transition-colors">
          Leer más →
        </span>
      </div>
    </a>
  );
}

function NewsView() {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/wc2026/news`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((data: NewsArticle[]) => { setNews(data); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
      <div className="text-5xl animate-pulse">📰</div>
      <p className="text-sm">Cargando noticias del Mundial...</p>
    </div>
  );

  if (error || news.length === 0) return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
      <div className="text-5xl">📭</div>
      <p className="text-sm">No se pudieron cargar las noticias</p>
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-white font-bold text-lg">Noticias del Mundial 2026</h2>
        <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-full border border-slate-700">
          Fuente: Marca · actualizado cada hora
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {news.map((article, i) => (
          <NewsCard key={i} article={article} index={i} />
        ))}
      </div>
    </div>
  );
}

// ── Real Round of 32 view ─────────────────────────────────────────────

interface ThirdRow {
  group: string; team: string;
  pj: number; g: number; e: number; p: number;
  gf: number; gc: number; dg: number; pts: number;
  confirmed: boolean;
}

function RealR32View({ allMatches, loading }: { allMatches: Match[]; loading: boolean }) {
  if (loading) return (
    <div className="text-center py-16 text-slate-500">
      <div className="text-5xl mb-4 animate-pulse">⏳</div>
      <p>Cargando partidos...</p>
    </div>
  );

  // Separate group stage (before June 28) from knockout (June 28+)
  const groupStageMatches = allMatches.filter(m => m.date.split('T')[0] < WC_KNOCKOUT_START);
  const knockoutFromDB = allMatches
    .filter(m => m.date.split('T')[0] >= WC_KNOCKOUT_START)
    .sort((a, b) => a.date.localeCompare(b.date) || a.match_id - b.match_id);

  const gm = groupStageMatches as unknown as GroupMatch[];

  const allStandings: Record<string, TeamStanding[]> = {};
  for (const g of GROUPS) allStandings[g] = computeStandings(g, gm);

  const completedGroups = new Set<string>(
    GROUPS.filter(g => allStandings[g].every(t => t.pj >= 3))
  );

  // Rankings in real standings order (used by existing BracketHalf / resolveTeam)
  const realRankings: Record<string, string[]> = {};
  for (const g of GROUPS) realRankings[g] = allStandings[g].map(t => t.team);

  const thirds: ThirdRow[] = GROUPS.map(g => {
    const t = allStandings[g][2];
    if (!t || t.pj === 0) return null;
    return { group: g, team: t.team, pj: t.pj, g: t.g, e: t.e, p: t.p,
             gf: t.gf, gc: t.gc, dg: t.dg, pts: t.pts, confirmed: completedGroups.has(g) };
  }).filter(Boolean) as ThirdRow[];

  const sortedThirds = [...thirds].sort((a, b) =>
    b.pts !== a.pts ? b.pts - a.pts :
    b.dg  !== a.dg  ? b.dg  - a.dg  :
    b.gf  !== a.gf  ? b.gf  - a.gf  : 0
  );

  const allGroupsDone = completedGroups.size === 12;
  const confirmedPosMatches = R32_MATCHES.filter(m =>
    m.slotA.kind === 'pos' && completedGroups.has(m.slotA.group) &&
    m.slotB.kind === 'pos' && completedGroups.has(m.slotB.group)
  ).length;

  // Step 1: Derive third-place picks from actual DB knockout matches
  // (identifies the real third-place team by matching the pos-slot team)
  const dbThirdPicks: Record<number, string> = {};
  for (const m of knockoutFromDB) {
    for (const r32m of R32_MATCHES) {
      if (dbThirdPicks[r32m.num] !== undefined) continue;
      const pairs: [BracketSlot, BracketSlot][] = [
        [r32m.slotA, r32m.slotB],
        [r32m.slotB, r32m.slotA],
      ];
      for (const [slotPos, slotOther] of pairs) {
        if (slotPos.kind !== 'pos' || slotOther.kind !== 'third') continue;
        const posTeam = realRankings[slotPos.group]?.[slotPos.pos];
        if (!posTeam) continue;
        if (m.home_team !== posTeam && m.away_team !== posTeam) continue;
        const thirdTeam = m.home_team === posTeam ? m.away_team : m.home_team;
        for (const g of GROUPS) {
          if (realRankings[g]?.[2] === thirdTeam) { dbThirdPicks[r32m.num] = g; break; }
        }
        break;
      }
    }
  }

  // Step 2: Merge confirmed assignments (hardcoded from official bracket) and DB data.
  // DB data takes precedence to allow real-time corrections once matches are recorded.
  // Greedy fills only the 3 remaining unknown slots (M1, M2, M12).
  const qualifyingThirds = sortedThirds.filter(t => t.confirmed).slice(0, 8);
  const finalThirdPicks: Record<number, string> = { ...CONFIRMED_R32_THIRDS, ...dbThirdPicks };
  const usedGroups = new Set(Object.values(finalThirdPicks));

  for (const r32m of [...R32_MATCHES].sort((a, b) => a.num - b.num)) {
    if (finalThirdPicks[r32m.num] !== undefined) continue;
    const slot = (r32m.slotA.kind === 'third' ? r32m.slotA : r32m.slotB) as Extract<BracketSlot, { kind: 'third' }>;
    if (!slot || slot.kind !== 'third') continue;
    // Only pick from eligible groups (fromGroups) that haven't been assigned yet.
    // No ultimate fallback — wrong groups should not be assigned just to fill a slot.
    const pick = qualifyingThirds.find(t => slot.fromGroups.includes(t.group) && !usedGroups.has(t.group));
    if (pick) { finalThirdPicks[r32m.num] = pick.group; usedGroups.add(pick.group); }
  }

  // Compute real winners from completed R32 knockout matches in DB.
  // For draws decided by penalties, uses penalty_winner from DB (shootouts.csv).
  const realWinners: Record<string, string> = {};
  for (const m of knockoutFromDB) {
    if (!m.actual_result) continue;
    for (const r32m of R32_MATCHES) {
      const mid = `R32-${r32m.num}`;
      if (realWinners[mid]) continue;
      const teamA = resolveTeam(mid, 'a', realRankings, finalThirdPicks, {});
      const teamB = resolveTeam(mid, 'b', realRankings, finalThirdPicks, {});
      if (!teamA || !teamB) continue;
      const homeMatchesA = m.home_team === teamA && m.away_team === teamB;
      const homeMatchesB = m.home_team === teamB && m.away_team === teamA;
      if (!homeMatchesA && !homeMatchesB) continue;
      if (m.actual_result === 'H') realWinners[mid] = m.home_team;
      else if (m.actual_result === 'A') realWinners[mid] = m.away_team;
      else if (m.actual_result === 'D' && m.penalty_winner) realWinners[mid] = m.penalty_winner;
      break;
    }
  }

  // Shared bracket props — DB picks take priority, greedy fills the rest
  const bracketProps = {
    rankings: realRankings,
    thirdPicks: finalThirdPicks,
    winners: realWinners,
    onPickWinner: () => {},
  };

  const leftMatches  = R32_MATCHES.filter(m => m.side === 'L');
  const rightMatches = R32_MATCHES.filter(m => m.side === 'R');

  return (
    <div className="space-y-8">
      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { val: `${completedGroups.size}/12`, label: 'Grupos finalizados',   color: 'text-yellow-400' },
          { val: `${confirmedPosMatches}/16`,  label: 'Cruces confirmados',   color: 'text-green-400'  },
          { val: `${sortedThirds.length}/12`,  label: 'Terceros conocidos',   color: 'text-blue-400'   },
        ].map(({ val, label, color }) => (
          <div key={label} className="bg-slate-800 border border-slate-700 rounded-xl p-3 text-center">
            <p className={`text-xl sm:text-2xl font-black ${color}`}>{val}</p>
            <p className="text-xs text-slate-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Info note */}
      {!allGroupsDone && (
        <div className="flex items-center gap-2 bg-yellow-400/5 border border-yellow-400/20 rounded-xl px-4 py-3 text-xs text-yellow-300/80">
          <span>⚠️</span>
          <span>Los equipos de grupos que aún no han terminado sus 3 partidos aparecen en posición provisional basada en los resultados actuales.</span>
        </div>
      )}
      {allGroupsDone && knockoutFromDB.length === 0 && (
        <div className="flex items-center gap-2 bg-yellow-400/5 border border-yellow-400/20 rounded-xl px-4 py-3 text-xs text-yellow-300/80">
          <span>⚠️</span>
          <span>Fase de grupos completada. Los slots de terceros clasificados se actualizarán automáticamente cuando los partidos de octavos estén disponibles.</span>
        </div>
      )}
      {knockoutFromDB.length > 0 && (
        <div className="flex items-center gap-2 bg-green-400/5 border border-green-400/20 rounded-xl px-4 py-3 text-xs text-green-300/80">
          <span>✅</span>
          <span>Llave de octavos actualizada con datos reales — {knockoutFromDB.length} partido{knockoutFromDB.length !== 1 ? 's' : ''} registrado{knockoutFromDB.length !== 1 ? 's' : ''}.</span>
        </div>
      )}

      {/* Actual knockout match results (from DB) */}
      {knockoutFromDB.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-white font-bold text-lg">Dieciseisavos de Final</h2>
            <span className="text-xs text-yellow-400/80 bg-yellow-400/10 border border-yellow-400/20 px-2.5 py-1 rounded-full">
              🏆 Datos reales
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {knockoutFromDB.map(m => (
              <WCMatchCard key={m.match_id} match={m} group="R32" currentSearchParams="" />
            ))}
          </div>
        </div>
      )}

      {/* Bracket visual — reuses existing BracketHalf / ClickableMatchCard */}
      <div>
        <h2 className="text-white font-bold text-lg mb-3">Vista del Bracket — Dieciseisavos de Final</h2>
        {knockoutFromDB.length === 0 && (
          <p className="text-xs text-slate-500 mb-3">Los slots de terceros se completarán cuando los partidos estén disponibles en la base de datos.</p>
        )}
        <div className="overflow-x-auto pb-3">
          <div className="flex items-stretch gap-1 min-w-max">
            <BracketHalf matches={leftMatches} side="L" {...bracketProps} />

            {/* Final center */}
            <div className="flex flex-col items-center justify-center px-3 gap-3">
              <span className="text-4xl">🏆</span>
              <div className="text-center">
                <p className="text-yellow-400 font-black text-xs uppercase tracking-widest">FINAL</p>
                <p className="text-slate-500 text-xs">19 Jul · NY</p>
              </div>
              <ClickableMatchCard matchId="Final" label="FINAL" {...bracketProps} />
            </div>

            <BracketHalf matches={rightMatches} side="R" {...bracketProps} />
          </div>
        </div>
      </div>

      {/* Third-place ranking */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-white font-bold text-lg">Ranking de Terceros</h2>
          <span className="text-xs text-slate-400 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-full">
            Mejores 8 de 12 avanzan a octavos
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Criterio: Puntos → Diferencia de goles → Goles a favor
        </p>

        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          {/* Desktop header */}
          <div className="hidden sm:grid sm:grid-cols-[1.5rem_2rem_1fr_2rem_2.5rem_2.5rem_2.5rem_2.5rem_2.5rem_3.5rem]
                          gap-1 text-xs text-slate-400 font-semibold px-3 py-2.5
                          border-b border-slate-700 bg-slate-900/60 uppercase tracking-wide">
            <span>#</span><span></span><span>Equipo</span>
            <span className="text-center">Grp</span>
            <span className="text-center">PJ</span>
            <span className="text-center text-yellow-400">Pts</span>
            <span className="text-center">GF</span>
            <span className="text-center">GC</span>
            <span className="text-center">DG</span>
            <span className="text-center">Estado</span>
          </div>
          {/* Mobile header */}
          <div className="grid grid-cols-[1.5rem_2rem_1fr_2.5rem_2.5rem_2.5rem_3.5rem] sm:hidden
                          gap-1 text-xs text-slate-400 font-semibold px-3 py-2.5
                          border-b border-slate-700 bg-slate-900/60 uppercase tracking-wide">
            <span>#</span><span></span><span>Equipo</span>
            <span className="text-center text-yellow-400">Pts</span>
            <span className="text-center">GF</span>
            <span className="text-center">DG</span>
            <span className="text-center">Estado</span>
          </div>

          {sortedThirds.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">Sin datos aún</div>
          ) : sortedThirds.map((t, i) => {
            const qualifies = i < 8;
            const border = qualifies ? 'border-l-green-500 bg-green-500/5' : 'border-l-slate-700';
            return (
              <div key={t.group} className={`border-b border-slate-700/40 last:border-0 border-l-2 ${border}`}>
                {/* Desktop row */}
                <div className="hidden sm:grid sm:grid-cols-[1.5rem_2rem_1fr_2rem_2.5rem_2.5rem_2.5rem_2.5rem_2.5rem_3.5rem]
                                gap-1 px-3 py-2.5 items-center">
                  <span className={`text-xs font-bold ${qualifies ? 'text-green-400' : 'text-slate-600'}`}>{i + 1}</span>
                  <span className="text-base leading-none">{TEAM_FLAG[t.team] ?? '🏳'}</span>
                  <span className={`text-sm font-semibold truncate ${qualifies ? 'text-white' : 'text-slate-400'}`}>{t.team}</span>
                  <span className="text-center"><span className="bg-yellow-400/20 text-yellow-400 font-bold text-xs px-1 rounded">{t.group}</span></span>
                  <span className="text-center text-sm text-slate-300">{t.pj}</span>
                  <span className={`text-center text-sm font-black ${qualifies ? 'text-yellow-400' : 'text-slate-400'}`}>{t.pts}</span>
                  <span className="text-center text-sm text-slate-300">{t.gf}</span>
                  <span className="text-center text-sm text-slate-300">{t.gc}</span>
                  <span className={`text-center text-sm font-medium ${t.dg > 0 ? 'text-green-400' : t.dg < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                    {t.dg > 0 ? '+' : ''}{t.dg}
                  </span>
                  <div className="text-center">
                    {qualifies
                      ? <span className="text-[10px] font-bold text-green-400 bg-green-400/10 border border-green-400/20 px-1.5 py-0.5 rounded-full">CLASIFICA</span>
                      : <span className="text-[10px] text-slate-600 bg-slate-700/40 px-1.5 py-0.5 rounded-full">FUERA</span>
                    }
                  </div>
                </div>
                {/* Mobile row */}
                <div className="grid grid-cols-[1.5rem_2rem_1fr_2.5rem_2.5rem_2.5rem_3.5rem] sm:hidden
                                gap-1 px-3 py-2.5 items-center">
                  <span className={`text-xs font-bold ${qualifies ? 'text-green-400' : 'text-slate-600'}`}>{i + 1}</span>
                  <span className="text-base leading-none">{TEAM_FLAG[t.team] ?? '🏳'}</span>
                  <span className={`text-xs font-semibold truncate ${qualifies ? 'text-white' : 'text-slate-400'}`}>{t.team}</span>
                  <span className={`text-center text-sm font-black ${qualifies ? 'text-yellow-400' : 'text-slate-400'}`}>{t.pts}</span>
                  <span className="text-center text-sm text-slate-300">{t.gf}</span>
                  <span className={`text-center text-sm font-medium ${t.dg > 0 ? 'text-green-400' : t.dg < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                    {t.dg > 0 ? '+' : ''}{t.dg}
                  </span>
                  <div className="text-center">
                    {qualifies
                      ? <span className="text-[10px] font-bold text-green-400 bg-green-400/10 border border-green-400/20 px-1 py-0.5 rounded-full whitespace-nowrap">✓</span>
                      : <span className="text-[10px] text-slate-600 bg-slate-700/40 px-1 py-0.5 rounded-full">✗</span>
                    }
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-4 mt-3 text-xs text-slate-500">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block"></span>Top 8 — clasifica a octavos</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-600 inline-block"></span>No clasifica</span>
          {!allGroupsDone && <span className="text-yellow-500/70">Posiciones provisionales</span>}
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────
interface Props {
  initialGroup?: string | null;
}

export default function WorldCupDashboard({ initialGroup }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedGroup, setSelectedGroup] = useState<string | null>(() => {
    if (initialGroup && GROUPS.includes(initialGroup)) return initialGroup;
    const fromSearch = new URLSearchParams(window.location.search).get('group');
    return fromSearch && GROUPS.includes(fromSearch) ? fromSearch : null;
  });
  const [activeTab, setActiveTab] = useState<Tab>('today');
  const [allWcMatches, setAllWcMatches] = useState<Match[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(true);
  const [groupMatches, setGroupMatches] = useState<GroupMatch[]>([]);
  const [loadingStandings, setLoadingStandings] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/wc2026/all-matches`)
      .then(r => r.json())
      .then(data => { setAllWcMatches(data); setLoadingMatches(false); })
      .catch(() => setLoadingMatches(false));
  }, []);

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
    if (g === '16avos') return; // no persisted in URL
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (g) next.set('group', g);
      else next.delete('group');
      return next;
    });
  };

  const matchesByGroup: Record<string, Match[]> = {};
  for (const m of allWcMatches) {
    const g = getMatchGroup(m);
    if (!matchesByGroup[g]) matchesByGroup[g] = [];
    matchesByGroup[g].push(m);
  }

  const isR32View = activeTab === 'matches' && selectedGroup === '16avos';
  const groupsToShow = selectedGroup && selectedGroup !== '16avos'
    ? [selectedGroup]
    : GROUPS.filter(g => matchesByGroup[g]?.length);

  return (
    <div className="min-h-screen bg-slate-900 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <WorldCupBanner matchCount={allWcMatches.length || 72} />
        <TabNav active={activeTab} onChange={setActiveTab} />

        {activeTab !== 'bracket' && activeTab !== 'news' && activeTab !== 'stats' && activeTab !== 'today' && (
          <GroupSelector
            selected={selectedGroup}
            onSelect={handleSelectGroup}
            showR32={activeTab === 'matches'}
          />
        )}

        {activeTab === 'matches' && (
          isR32View ? (
            <RealR32View allMatches={allWcMatches} loading={loadingMatches} />
          ) : loadingMatches ? (
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

        {activeTab === 'today' && (() => {
          const now = new Date();
          const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
          const todayMatches = allWcMatches.filter(m => m.date.split('T')[0] === todayStr);
          if (loadingMatches) return (
            <div className="text-center py-16 text-slate-500">
              <div className="text-5xl mb-4">⏳</div>
              <p className="text-lg">Cargando partidos...</p>
            </div>
          );
          if (todayMatches.length === 0) return (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
              <div className="text-5xl">📅</div>
              <p className="text-base font-semibold text-slate-300">No hay partidos programados para hoy</p>
              <p className="text-sm text-slate-500">Revisa la pestaña Partidos para ver el calendario completo.</p>
            </div>
          );
          const byGroup: Record<string, Match[]> = {};
          const knockoutMatches: Match[] = [];
          for (const m of todayMatches) {
            if (m.date.split('T')[0] >= WC_KNOCKOUT_START) {
              knockoutMatches.push(m);
            } else {
              const g = getMatchGroup(m);
              if (!byGroup[g]) byGroup[g] = [];
              byGroup[g].push(m);
            }
          }
          return (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <h2 className="text-white font-bold text-lg">Partidos de Hoy</h2>
                <span className="text-xs text-slate-400 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-full">
                  {todayMatches.length} {todayMatches.length === 1 ? 'partido' : 'partidos'}
                </span>
              </div>
              {knockoutMatches.length > 0 && (
                <section>
                  <div className="flex items-center gap-2 px-1 mb-3">
                    <div className="w-1 h-5 bg-yellow-400 rounded-full" />
                    <h3 className="text-white font-bold text-base">Dieciseisavos de Final</h3>
                    <span className="text-xs text-yellow-400/70 bg-yellow-400/10 px-2 py-0.5 rounded-full">🏆 R32</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4">
                    {knockoutMatches.map(m => (
                      <WCMatchCard key={m.match_id} match={m} group="R32" currentSearchParams={searchParams.toString()} />
                    ))}
                  </div>
                </section>
              )}
              {GROUPS.filter(g => byGroup[g]).map(g => (
                <section key={g}>
                  <GroupHeader group={g} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4">
                    {byGroup[g].map(m => (
                      <WCMatchCard key={m.match_id} match={m} group={g} currentSearchParams={searchParams.toString()} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          );
        })()}

        {activeTab === 'bracket' && <RealR32View allMatches={allWcMatches} loading={loadingMatches} />}

        {activeTab === 'stats' && <WC2026StatsModule />}

        {activeTab === 'news' && <NewsView />}
      </div>
    </div>
  );
}
