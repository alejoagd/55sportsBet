// ============================================================================
// COMPONENTE: MatchH2HNarrative.tsx
// Muestra análisis de enfrentamientos directos con narrativa
// ============================================================================

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown } from 'lucide-react';

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
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchH2HAnalysis();
  }, [matchId]);

  const fetchH2HAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `http://localhost:8000/api/matches/${matchId}/h2h-analysis`
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
    return null; // No mostrar nada si no hay datos
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
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-bold text-purple-400 mb-2">
              📊 Análisis de Enfrentamientos Directos
            </h3>
            <p className="text-slate-400 text-sm">
              Basado en los últimos {stats.total_matches} partidos entre estos equipos
            </p>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
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

        {/* Narrativa principal */}
        <div className="bg-slate-900/50 rounded-lg p-4">
          <p className="text-slate-300 text-sm leading-relaxed">
            {narrative.summary}
          </p>
        </div>
      </div>

      {/* Contenido expandible */}
      {expanded && (
        <div className="p-6 space-y-6">
          {/* Análisis por venue */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Local */}
            {narrative.home_venue_analysis && (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                <h4 className="text-blue-400 font-semibold mb-3 flex items-center gap-2">
                  🏠 Jugando de Local
                </h4>
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-sans">
                  {narrative.home_venue_analysis}
                </pre>
              </div>
            )}

            {/* Visitante */}
            {narrative.away_venue_analysis && (
              <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4">
                <h4 className="text-orange-400 font-semibold mb-3 flex items-center gap-2">
                  ✈️ Jugando de Visitante
                </h4>
                <pre className="text-slate-300 text-xs whitespace-pre-wrap font-sans">
                  {narrative.away_venue_analysis}
                </pre>
              </div>
            )}
          </div>

          {/* Comparación con predicción */}
          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
            <h4 className="text-purple-400 font-semibold mb-3 flex items-center gap-2">
              🎯 Predicción vs. Histórico
            </h4>
            <pre className="text-slate-300 text-xs whitespace-pre-wrap font-sans">
              {narrative.prediction_analysis}
            </pre>
          </div>

          {/* Conclusión */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <h4 className="text-green-400 font-semibold mb-3 flex items-center gap-2">
              💡 Conclusión
            </h4>
            <p className="text-slate-300 text-sm">
              {narrative.conclusion}
            </p>
          </div>

          {/* Lista de partidos históricos */}
          {(data.h2h_home.length > 0 || data.h2h_away.length > 0) && (
            <div className="space-y-4">
              <h4 className="text-slate-400 font-semibold">
                📋 Historial de Partidos
              </h4>

              {data.h2h_home.length > 0 && (
                <div>
                  <p className="text-slate-500 text-xs mb-2">
                    🏠 Como local ({data.h2h_home.length} partidos)
                  </p>
                  <div className="space-y-2">
                    {data.h2h_home.map((match: any) => (
                      <HistoricalMatchRow key={match.id} match={match} venue="home" />
                    ))}
                  </div>
                </div>
              )}

              {data.h2h_away.length > 0 && (
                <div className="mt-4">
                  <p className="text-slate-500 text-xs mb-2">
                    ✈️ Como visitante ({data.h2h_away.length} partidos)
                  </p>
                  <div className="space-y-2">
                    {data.h2h_away.map((match: any) => (
                      <HistoricalMatchRow key={match.id} match={match} venue="away" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
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

interface HistoricalMatchRowProps {
  match: any;
  venue: 'home' | 'away';
}

function HistoricalMatchRow({ match, venue }: HistoricalMatchRowProps) {
  const goals = venue === 'home' 
    ? `${match.home_goals}-${match.away_goals}`
    : `${match.team_goals}-${match.opponent_goals}`;
  
  const date = new Date(match.date).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });

  return (
    <div className="bg-slate-800/50 rounded-lg p-3 flex items-center justify-between text-xs">
      <div className="flex items-center gap-3">
        <span className="text-slate-500 font-mono">{date}</span>
        <span className="text-slate-400">{match.season}</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-white font-bold font-mono">{goals}</span>
        <div className="flex gap-2">
          {match.btts && <span className="text-green-400" title="BTTS">✓</span>}
          {match.over25 && <span className="text-blue-400" title="Over 2.5">📈</span>}
        </div>
        <span className="text-slate-500" title="Corners">
          🚩 {match.total_corners}
        </span>
      </div>
    </div>
  );
}