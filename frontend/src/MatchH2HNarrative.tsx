// ============================================================================
// COMPONENTE: MatchH2HNarrative.tsx
// VERSIÓN FINAL CON RESUMEN DE RESULTADOS (G-E-P, BTTS, Over 2.5)
// ============================================================================

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface VenueStatItem {
  label: string;
  icon: string;
  home_value: number;
  away_value: number;
}

interface VenueStats {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  btts_count: number;
  over25_count: number;
  avg_goals_home: number;
  avg_goals_away: number;
  items: VenueStatItem[];
}

interface H2HAnalysisData {
  match_id: number;
  home_team: string;
  away_team: string;
  date: string;
  h2h_home: any[];
  h2h_away: any[];
  stats: {
    total_matches: number;
    has_data: boolean;
    avg_total_goals: number;
    avg_total_corners: number;
    avg_total_cards: number;
    btts_percentage: number;
    over25_percentage: number;
    home_venue?: any;
    away_venue?: any;
  };
  narrative: {
    summary: string;
    home_venue_analysis: string;
    away_venue_analysis: string;
    home_venue_stats: VenueStats | null;
    away_venue_stats: VenueStats | null;
    prediction_analysis: string;
    conclusion: string;
    full_narrative: string;
  };
  predictions: any;
}

interface MatchH2HNarrativeProps {
  matchId: number;
}

export default function MatchH2HNarrative({ matchId }: MatchH2HNarrativeProps) {
  const [data, setData] = useState<H2HAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchH2HAnalysis();
  }, [matchId]);

  const fetchH2HAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/matches/${matchId}/h2h-analysis`
      );

      if (!response.ok) {
        throw new Error('Error al cargar análisis H2H');
      }

      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-3/4 mb-3"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  if (!data.stats.has_data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <p className="text-slate-400 text-sm">
          No hay datos históricos disponibles para este enfrentamiento.
        </p>
      </div>
    );
  }

  const { stats, narrative } = data;

  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-purple-500/20 overflow-hidden">
      {/* Header con resumen ejecutivo */}
      <div className="p-4 sm:p-6 border-b border-slate-700">
        <div className="mb-4">
          <h3 className="text-lg sm:text-xl font-bold text-purple-400 mb-2">
            📊 Análisis de Enfrentamientos Directos
          </h3>
          <p className="text-slate-400 text-xs sm:text-sm">
            Basado en los últimos {stats.total_matches} partidos entre estos equipos
          </p>
        </div>

        {/* Estadísticas clave en cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <StatCard
            label="Goles/Partido"
            value={stats.avg_total_goals.toFixed(1)}
            icon="⚽"
            trend={stats.avg_total_goals >= 2.5 ? 'up' : 'down'}
          />
          <StatCard
            label="Corners/Partido"
            value={stats.avg_total_corners.toFixed(1)}
            icon="🚩"
          />
          <StatCard
            label="BTTS"
            value={`${stats.btts_percentage.toFixed(0)}%`}
            icon="🎯"
            trend={stats.btts_percentage >= 50 ? 'up' : 'down'}
          />
          <StatCard
            label="Over 2.5"
            value={`${stats.over25_percentage.toFixed(0)}%`}
            icon="📈"
            trend={stats.over25_percentage >= 50 ? 'up' : 'down'}
          />
        </div>

        {/* Narrativa principal (RESUMEN) */}
        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
          <h4 className="text-slate-300 font-semibold text-sm mb-2">RESUMEN DEL PARTIDO</h4>
          <p className="text-slate-300 text-sm leading-relaxed">
            {narrative.summary}
          </p>
        </div>
      </div>

      {/* HISTORIAL DE PARTIDOS — siempre visible, no depende de "Ver más" */}
      {(data.h2h_home.length > 0 || data.h2h_away.length > 0) && (
        <div className="p-4 sm:p-6 border-b border-slate-700">
          <h4 className="text-white font-semibold text-sm sm:text-base mb-3 flex items-center gap-2">
            📋 Historial de Partidos
          </h4>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
            {data.h2h_home.length > 0 && (
              <div>
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1.5">
                  🏠 Como local <span className="text-slate-500 normal-case font-normal">({data.h2h_home.length})</span>
                </p>
                <div>
                  {data.h2h_home.map((match: any, index: number) => (
                    <H2HRow
                      key={match.id || index}
                      match={match}
                      venue="home"
                      homeTeam={data.home_team}
                      awayTeam={data.away_team}
                    />
                  ))}
                </div>
              </div>
            )}

            {data.h2h_away.length > 0 && (
              <div>
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1.5">
                  ✈️ Como visitante <span className="text-slate-500 normal-case font-normal">({data.h2h_away.length})</span>
                </p>
                <div>
                  {data.h2h_away.map((match: any, index: number) => (
                    <H2HRow
                      key={match.id || index}
                      match={match}
                      venue="away"
                      homeTeam={data.home_team}
                      awayTeam={data.away_team}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-700/50 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
            <span className="flex items-center gap-1"><span className="text-green-400">✓</span> BTTS</span>
            <span className="flex items-center gap-1"><span className="text-blue-400">📈</span> Over 2.5</span>
          </div>
        </div>
      )}

      {/* 🏠 JUGANDO DE LOCAL / ✈️ JUGANDO DE VISITANTE — siempre visibles,
          no dependen del botón "Ver más" (antes quedaban ocultas ahí). */}
      {(narrative.home_venue_stats || narrative.away_venue_stats) && (
        <div className="p-4 sm:p-6 space-y-4 border-b border-slate-700">
          {narrative.home_venue_stats && (
            <VenueCard
              icon="🏠"
              title="Jugando de Local"
              theme="blue"
              homeTeam={data.home_team}
              awayTeam={data.away_team}
              stats={narrative.home_venue_stats}
            />
          )}

          {narrative.away_venue_stats && (
            <VenueCard
              icon="✈️"
              title="Jugando de Visitante"
              theme="orange"
              homeTeam={data.home_team}
              awayTeam={data.away_team}
              stats={narrative.away_venue_stats}
            />
          )}
        </div>
      )}

      {/* 🎯 PREDICCIÓN VS HISTÓRICO / 💡 CONCLUSIÓN — siempre visibles */}
      <div className="p-6 space-y-4">
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-5">
          <h4 className="text-purple-400 font-semibold mb-3 flex items-center gap-2 text-base">
            🎯 Predicción vs. Histórico
          </h4>
          <div className="space-y-2">
            {narrative.prediction_analysis.split('\n').map((line, idx) => {
              if (!line.trim()) return null;

              return (
                <p key={idx} className="text-slate-300 text-sm leading-relaxed">
                  {highlightNumbers(line)}
                </p>
              );
            })}
          </div>
        </div>

        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-5">
          <h4 className="text-green-400 font-semibold mb-3 flex items-center gap-2 text-base">
            💡 Conclusión
          </h4>
          <p className="text-slate-300 text-sm leading-relaxed">
            {highlightNumbers(narrative.conclusion)}
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HELPER: Destacar números en texto
// ============================================================================

function highlightNumbers(text: string) {
  if (!text) return text;
  
  // Regex para encontrar números decimales o enteros
  const parts = text.split(/(\d+\.?\d*)/g);
  
  return parts.map((part, idx) => {
    if (/^\d+\.?\d*$/.test(part)) {
      return (
        <span key={idx} className="text-white font-bold">
          {part}
        </span>
      );
    }
    return part;
  });
}

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

interface StatCardProps {
  label: string;
  value: string;
  icon: string;
  trend?: 'up' | 'down';
}

function StatCard({ label, value, icon, trend }: StatCardProps) {
  return (
    <div className="bg-slate-900/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-2xl">{icon}</span>
        {trend && (
          trend === 'up' ? (
            <TrendingUp className="w-4 h-4 text-green-400" />
          ) : (
            <TrendingDown className="w-4 h-4 text-red-400" />
          )
        )}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

// ============================================================================
// COMPONENTE: TARJETA DE ESTADÍSTICAS LOCAL/VISITANTE
// ============================================================================

function VenueCard({
  icon,
  title,
  theme,
  homeTeam,
  awayTeam,
  stats,
}: {
  icon: string;
  title: string;
  theme: 'blue' | 'orange';
  homeTeam: string;
  awayTeam: string;
  stats: VenueStats;
}) {
  const accent = theme === 'blue'
    ? { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', pill: 'bg-blue-500/20 text-blue-300' }
    : { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-400', pill: 'bg-orange-500/20 text-orange-300' };

  return (
    <div className={`${accent.bg} border ${accent.border} rounded-lg p-4 sm:p-5`}>
      <h4 className={`${accent.text} font-semibold mb-3 flex items-center gap-2 text-sm sm:text-base`}>
        {icon} {title} <span className="text-slate-400 font-normal text-xs">({stats.matches} partidos)</span>
      </h4>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className={`text-[11px] font-bold px-2 py-1 rounded-full ${accent.pill}`}>
          {homeTeam}: G{stats.wins}-E{stats.draws}-P{stats.losses}
        </span>
        <span className="text-[11px] font-semibold px-2 py-1 rounded-full bg-slate-700/60 text-slate-300">
          BTTS {stats.btts_count}/{stats.matches}
        </span>
        <span className="text-[11px] font-semibold px-2 py-1 rounded-full bg-slate-700/60 text-slate-300">
          Over 2.5 {stats.over25_count}/{stats.matches}
        </span>
      </div>

      <div className="space-y-0.5">
        <StatRow icon="⚽" label="Goles" homeValue={stats.avg_goals_home} awayValue={stats.avg_goals_away} />
        {stats.items.map((item) => (
          <StatRow key={item.label} icon={item.icon} label={item.label} homeValue={item.home_value} awayValue={item.away_value} />
        ))}
      </div>

      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-700/40 text-[10px] text-slate-500">
        <span className="truncate max-w-[45%]">{homeTeam}</span>
        <span className="truncate max-w-[45%] text-right">{awayTeam}</span>
      </div>
    </div>
  );
}

function StatRow({ icon, label, homeValue, awayValue }: { icon: string; label: string; homeValue: number; awayValue: number }) {
  return (
    <div className="flex items-center justify-between text-xs sm:text-sm py-1 border-b border-slate-700/30 last:border-0">
      <span className="text-blue-300 font-bold tabular-nums w-10 text-right">{homeValue}</span>
      <span className="text-slate-400 flex items-center gap-1.5 flex-1 justify-center truncate px-1">
        <span>{icon}</span>{label}
      </span>
      <span className="text-orange-300 font-bold tabular-nums w-10 text-left">{awayValue}</span>
    </div>
  );
}

// ============================================================================
// COMPONENTE DE FILA HISTÓRICA (compacto, estilo TeamFormSection)
// ============================================================================

interface HistoricalMatchRowProps {
  match: any;
  venue: 'home' | 'away';
  homeTeam: string;
  awayTeam: string;
}

function formatH2HDate(dateString: string): { top: string; bottom: string } {
  const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
  return {
    top: `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}`,
    bottom: String(year),
  };
}

function H2HRow({ match, venue, homeTeam, awayTeam }: HistoricalMatchRowProps) {
  let leftTeam: string;
  let rightTeam: string;
  let leftGoals: number;
  let rightGoals: number;

  if (venue === 'home') {
    leftTeam = homeTeam;
    rightTeam = awayTeam;
    leftGoals = match.home_goals;
    rightGoals = match.away_goals;
  } else {
    leftTeam = awayTeam;
    rightTeam = homeTeam;
    leftGoals = match.opponent_goals;
    rightGoals = match.team_goals;
  }

  // El color del marcador siempre refleja el resultado desde la
  // perspectiva de homeTeam (el equipo que juega hoy de local).
  const homeGoalsToday = venue === 'home' ? leftGoals : rightGoals;
  const awayGoalsToday = venue === 'home' ? rightGoals : leftGoals;
  const resultClass = homeGoalsToday === awayGoalsToday
    ? 'bg-yellow-500 text-black'
    : homeGoalsToday > awayGoalsToday
      ? 'bg-green-600 text-white'
      : 'bg-red-600 text-white';

  const { top, bottom } = formatH2HDate(match.date);

  return (
    <div className="flex items-center gap-2 text-xs py-1.5 px-1 rounded hover:bg-slate-700/30 transition-colors">
      <div className="w-10 flex-shrink-0 text-center leading-tight">
        <div className="text-slate-300 font-medium tabular-nums">{top}</div>
        <div className="text-slate-500 tabular-nums text-[10px]">{bottom}</div>
      </div>

      <span className="flex-1 text-right truncate text-slate-300">{leftTeam}</span>

      <span className={`flex-shrink-0 px-2 py-0.5 rounded font-bold tabular-nums ${resultClass}`}>
        {leftGoals}-{rightGoals}
      </span>

      <span className="flex-1 text-left truncate text-slate-300">{rightTeam}</span>

      <div className="w-9 flex-shrink-0 flex items-center justify-end gap-1">
        {match.btts && <span className="text-green-400 text-[11px]" title="BTTS">✓</span>}
        {match.over25 && <span className="text-blue-400 text-[11px]" title="Over 2.5">📈</span>}
      </div>
    </div>
  );
}