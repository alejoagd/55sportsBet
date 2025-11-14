// ============================================================================
// COMPONENTE: MatchH2HNarrative.tsx
// VERSIÓN FINAL CON RESUMEN DE RESULTADOS (G-E-P, BTTS, Over 2.5)
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

        {/* Narrativa principal (RESUMEN) */}
        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
          <h4 className="text-slate-300 font-semibold text-sm mb-2">RESUMEN DEL PARTIDO</h4>
          <p className="text-slate-300 text-sm leading-relaxed">
            {narrative.summary}
          </p>
        </div>
      </div>

      {/* Contenido expandible */}
      {expanded && (
        <div className="p-6 space-y-4">
          
          {/* 🏠 NARRATIVA DE LOCAL */}
          {narrative.home_venue_analysis && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-5">
              <h4 className="text-blue-400 font-semibold mb-3 flex items-center gap-2 text-base">
                🏠 Jugando de Local
              </h4>
              <div className="space-y-2">
                {narrative.home_venue_analysis.split('\n').map((line, idx) => {
                  if (!line.trim()) return null;
                  
                  // Detectar línea de resumen (G-E-P | BTTS | Over 2.5)
                  const isResultSummary = line.includes('G') && line.includes('-E') && line.includes('-P') && line.includes('|');
                  
                  // Detectar líneas con promedios
                  const isStatLine = line.includes('Promedio');
                  
                  // Línea de resumen con estilo especial
                  if (isResultSummary) {
                    return (
                      <div 
                        key={idx} 
                        className="bg-blue-500/20 border border-blue-400/40 rounded-lg p-3 mb-3"
                      >
                        <p className="text-white text-sm font-bold">
                          {highlightNumbers(line)}
                        </p>
                      </div>
                    );
                  }
                  
                  return (
                    <p 
                      key={idx} 
                      className={`text-sm leading-relaxed ${
                        isStatLine 
                          ? 'text-slate-200 font-medium pl-2 border-l-2 border-blue-400/50' 
                          : 'text-slate-300'
                      }`}
                    >
                      {highlightNumbers(line)}
                    </p>
                  );
                })}
              </div>
            </div>
          )}

          {/* ✈️ NARRATIVA DE VISITANTE */}
          {narrative.away_venue_analysis && (
            <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-5">
              <h4 className="text-orange-400 font-semibold mb-3 flex items-center gap-2 text-base">
                ✈️ Jugando de Visitante
              </h4>
              <div className="space-y-2">
                {narrative.away_venue_analysis.split('\n').map((line, idx) => {
                  if (!line.trim()) return null;
                  
                  // Detectar línea de resumen (G-E-P | BTTS | Over 2.5)
                  const isResultSummary = line.includes('G') && line.includes('-E') && line.includes('-P') && line.includes('|');
                  
                  const isStatLine = line.includes('Promedio');
                  
                  // Línea de resumen con estilo especial
                  if (isResultSummary) {
                    return (
                      <div 
                        key={idx} 
                        className="bg-orange-500/20 border border-orange-400/40 rounded-lg p-3 mb-3"
                      >
                        <p className="text-white text-sm font-bold">
                          {highlightNumbers(line)}
                        </p>
                      </div>
                    );
                  }
                  
                  return (
                    <p 
                      key={idx} 
                      className={`text-sm leading-relaxed ${
                        isStatLine 
                          ? 'text-slate-200 font-medium pl-2 border-l-2 border-orange-400/50' 
                          : 'text-slate-300'
                      }`}
                    >
                      {highlightNumbers(line)}
                    </p>
                  );
                })}
              </div>
            </div>
          )}

          {/* 🎯 PREDICCIÓN VS HISTÓRICO */}
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

          {/* 💡 CONCLUSIÓN */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-5">
            <h4 className="text-green-400 font-semibold mb-3 flex items-center gap-2 text-base">
              💡 Conclusión
            </h4>
            <p className="text-slate-300 text-sm leading-relaxed">
              {highlightNumbers(narrative.conclusion)}
            </p>
          </div>

          {/* HISTORIAL DE PARTIDOS */}
          {(data.h2h_home.length > 0 || data.h2h_away.length > 0) && (
            <div className="bg-slate-900/30 rounded-lg p-6 border border-slate-700">
              <h4 className="text-white font-semibold text-base mb-6 flex items-center gap-2">
                📋 Historial de Partidos
              </h4>

              {/* BLOQUE 1: Como local */}
              {data.h2h_home.length > 0 && (
                <div className="mb-8">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center">
                      <span className="text-white text-xs font-bold">🏠</span>
                    </div>
                    <p className="text-slate-300 text-sm font-semibold">
                      Como local ({data.h2h_home.length} partidos)
                    </p>
                  </div>
                  
                  <div className="bg-white/5 rounded-lg overflow-hidden border border-slate-700">
                    <div className="divide-y divide-slate-700">
                      {data.h2h_home.map((match: any, index: number) => (
                        <HistoricalMatchRow
                          key={match.id || index}
                          match={match}
                          venue="home"
                          homeTeam={data.home_team}
                          awayTeam={data.away_team}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* BLOQUE 2: Como visitante */}
              {data.h2h_away.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-6 h-6 bg-orange-500 rounded flex items-center justify-center">
                      <span className="text-white text-xs font-bold">✈️</span>
                    </div>
                    <p className="text-slate-300 text-sm font-semibold">
                      Como visitante ({data.h2h_away.length} partidos)
                    </p>
                  </div>
                  
                  <div className="bg-white/5 rounded-lg overflow-hidden border border-slate-700">
                    <div className="divide-y divide-slate-700">
                      {data.h2h_away.map((match: any, index: number) => (
                        <HistoricalMatchRow
                          key={match.id || index}
                          match={match}
                          venue="away"
                          homeTeam={data.home_team}
                          awayTeam={data.away_team}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Leyenda */}
              <div className="mt-6 pt-4 border-t border-slate-700">
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    <span>BTTS</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400">📈</span>
                    <span>Over 2.5</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">🚩</span>
                    <span>Corners</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
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
// COMPONENTE DE FILA HISTÓRICA
// ============================================================================

interface HistoricalMatchRowProps {
  match: any;
  venue: 'home' | 'away';
  homeTeam: string;
  awayTeam: string;
}

function HistoricalMatchRow({ match, venue, homeTeam, awayTeam }: HistoricalMatchRowProps) {
  
  // Formatear fecha SIN restar día
  const formatDate = (dateString: string) => {
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
    const date = new Date(year, month - 1, day);
    
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  // Posicionamiento correcto
  let leftTeam: string;
  let rightTeam: string;
  let leftGoals: number;
  let rightGoals: number;

  if (venue === 'home') {
    // BLOQUE 1: Como local - homeTeam a la IZQUIERDA
    leftTeam = homeTeam;
    rightTeam = awayTeam;
    leftGoals = match.home_goals;
    rightGoals = match.away_goals;
  } else {
    // BLOQUE 2: Como visitante - homeTeam a la DERECHA
    leftTeam = awayTeam;
    rightTeam = homeTeam;
    leftGoals = match.opponent_goals;
    rightGoals = match.team_goals;
  }

  // Determinar resultado
  const getResultClass = () => {
    if (venue === 'home') {
      if (leftGoals > rightGoals) return 'bg-green-500/20';
      if (leftGoals < rightGoals) return 'bg-red-500/20';
      return 'bg-yellow-500/20';
    } else {
      if (rightGoals > leftGoals) return 'bg-green-500/20';
      if (rightGoals < leftGoals) return 'bg-red-500/20';
      return 'bg-yellow-500/20';
    }
  };

  return (
    <div className={`flex items-center justify-between px-4 py-3 hover:bg-slate-700/30 transition-colors ${getResultClass()}`}>
      {/* Fecha */}
      <div className="flex items-center gap-4 min-w-[140px]">
        <span className="text-slate-400 text-xs font-mono">
          {formatDate(match.date)}
        </span>
        <span className="text-slate-500 text-xs">
          {match.season}
        </span>
      </div>

      {/* Equipos y Marcador */}
      <div className="flex items-center gap-6 flex-1 justify-center">
        <div className="flex items-center gap-3 min-w-[160px] justify-end">
          <span className="text-white text-sm font-medium text-right">
            {leftTeam}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-white text-lg font-bold font-mono bg-slate-800 px-4 py-1 rounded">
            {leftGoals} - {rightGoals}
          </span>
        </div>

        <div className="flex items-center gap-3 min-w-[160px]">
          <span className="text-white text-sm font-medium">
            {rightTeam}
          </span>
        </div>
      </div>

      {/* Competición e Indicadores */}
      <div className="flex items-center gap-4 min-w-[120px] justify-end">
        <span className="text-slate-400 text-xs font-semibold">
          {match.competition || 'EPL'}
        </span>
        
        <div className="flex items-center gap-2">
          {match.btts && (
            <span className="text-green-400 text-sm" title="BTTS">✓</span>
          )}
          {match.over25 && (
            <span className="text-blue-400 text-sm" title="Over 2.5">📈</span>
          )}
          {match.total_corners && (
            <span className="text-slate-500 text-xs" title="Corners">
              🚩 {match.total_corners}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}