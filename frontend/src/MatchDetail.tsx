import { useState, useEffect, type JSX } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

interface MatchStats {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  referee: string;
  
  // Estadísticas detalladas
  home_shots: number;
  away_shots: number;
  home_shots_on_target: number;
  away_shots_on_target: number;
  home_fouls: number;
  away_fouls: number;
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
  
  // Predicciones de Weinston (estadísticas predichas)
  weinston_shots_home?: number;
  weinston_shots_away?: number;
  weinston_shots_on_target_home?: number;
  weinston_shots_on_target_away?: number;
  weinston_fouls_home?: number;
  weinston_fouls_away?: number;
  weinston_corners_home?: number;
  weinston_corners_away?: number;
  weinston_cards_home?: number;
  weinston_cards_away?: number;
  
  // Totales del partido (de match_stats)
  total_shots?: number;
  total_shots_on_target?: number;
  total_corners?: number;
  total_fouls?: number;
  total_cards?: number;
  has_real_stats?: boolean;
  
  // Predicciones
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
}

// 🎯 INTERFACES PARA BETTING LINES
interface BettingLine {
  prediction: string;
  line: number;
  confidence: number;
  predicted_total: number;
  actual_total: number | null;
  hit: boolean | null;
}

interface BettingLinesData {
  match_id: number;
  shots: BettingLine;
  shots_on_target: BettingLine;
  corners: BettingLine;
  cards: BettingLine;
  fouls: BettingLine;
}

export default function MatchDetail() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const [match, setMatch] = useState<MatchStats | null>(null);
  const [bettingLines, setBettingLines] = useState<BettingLinesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMatchDetails();
    fetchBettingLines();
  }, [matchId]);

  const fetchMatchDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `http://localhost:8000/api/matches/${matchId}/details`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar detalles del partido');
      }
      
      const data = await response.json();
      setMatch(data);
    } catch (error) {
      console.error('Error:', error);
      setError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // 🎯 FETCH BETTING LINES
  const fetchBettingLines = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/betting-lines/match/${matchId}?model=weinston`
      );
      
      if (response.ok) {
        const data = await response.json();
        
        if (data) {
          // Transformar datos a formato más fácil de usar
          setBettingLines({
            match_id: data.match_id,
            shots: {
              prediction: data.shots_prediction,
              line: data.shots_line,
              confidence: data.shots_confidence,
              predicted_total: data.predicted_total_shots,
              actual_total: data.actual_total_shots,
              hit: data.shots_hit
            },
            shots_on_target: {
              prediction: data.shots_on_target_prediction,
              line: data.shots_on_target_line,
              confidence: data.shots_on_target_confidence,
              predicted_total: data.predicted_total_shots_on_target,
              actual_total: data.actual_total_shots_on_target,
              hit: data.shots_on_target_hit
            },
            corners: {
              prediction: data.corners_prediction,
              line: data.corners_line,
              confidence: data.corners_confidence,
              predicted_total: data.predicted_total_corners,
              actual_total: data.actual_total_corners,
              hit: data.corners_hit
            },
            cards: {
              prediction: data.cards_prediction,
              line: data.cards_line,
              confidence: data.cards_confidence,
              predicted_total: data.predicted_total_cards,
              actual_total: data.actual_total_cards,
              hit: data.cards_hit
            },
            fouls: {
              prediction: data.fouls_prediction,
              line: data.fouls_line,
              confidence: data.fouls_confidence,
              predicted_total: data.predicted_total_fouls,
              actual_total: data.actual_total_fouls,
              hit: data.fouls_hit
            }
          });
        }
      }
    } catch (error) {
      console.error('Error fetching betting lines:', error);
      // No es crítico, simplemente no se mostrarán
    }
  };

  const safeNumber = (value: any, defaultValue: number = 0): number => {
    if (value === null || value === undefined || isNaN(value)) {
      return defaultValue;
    }
    return Number(value);
  };

  // Función para formatear fecha sin problemas de zona horaria
  const formatMatchDate = (dateString: string): string => {
    if (!dateString) return '';
    
    // Parsear manualmente la fecha (YYYY-MM-DD) sin conversión de timezone
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
    const date = new Date(year, month - 1, day); // month - 1 porque JavaScript usa 0-11
    
    return date.toLocaleDateString('es-ES', {
      weekday: 'long',
      day: '2-digit',
      month: 'long',
      year: 'numeric'
    });
  };

  const getResultLabel = (result: string) => {
    if (result === 'H' || result === '1') return '1';
    if (result === 'A' || result === '2') return '2';
    return 'X';
  };

  // 🎯 FUNCIÓN PARA RENDERIZAR BETTING LINE
  const renderBettingLine = (line: BettingLine | undefined) => {
    if (!line) {
      return <span className="text-slate-500 text-xs">-</span>;
    }

    const isFinished = line.actual_total !== null;
    
    if (isFinished) {
      // Partido ya jugado - mostrar si acertó
      return (
        <div className="flex flex-col items-center gap-1">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">
              {line.prediction.toUpperCase()} {line.line}
            </span>
            {line.hit ? (
              <span className="text-green-500 text-lg">✅</span>
            ) : (
              <span className="text-red-500 text-lg">❌</span>
            )}
          </div>
          <span className="text-[10px] text-slate-500">
            Real: {line.actual_total}
          </span>
        </div>
      );
    } else {
      // Partido no jugado - mostrar predicción con confianza
      const confidencePercent = Math.round(line.confidence * 100);
      const confidenceColor = 
        confidencePercent >= 70 ? 'text-green-400' :
        confidencePercent >= 40 ? 'text-yellow-400' :
        confidencePercent >= 20 ? 'text-orange-400' :
        'text-slate-500';
      
      const confidenceEmoji =
        confidencePercent >= 70 ? '🔥' :
        confidencePercent >= 40 ? '🟢' :
        confidencePercent >= 20 ? '🟡' :
        '⚪';
      
      return (
        <div className="flex flex-col items-center gap-1">
          <span className={`font-semibold text-sm ${
            line.prediction === 'over' ? 'text-green-400' : 'text-blue-400'
          }`}>
            {line.prediction.toUpperCase()} {line.line}
          </span>
          <span className={`text-[10px] ${confidenceColor} flex items-center gap-1`}>
            {confidenceEmoji} {confidencePercent}%
          </span>
        </div>
      );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-slate-400 text-xl">⏳ Cargando detalles...</div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-900">
        <div className="text-red-400 text-xl mb-4">❌ {error || 'Partido no encontrado'}</div>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          ← Volver al Dashboard
        </button>
      </div>
    );
  }

  const isFinished = match.home_goals !== null && match.home_goals !== undefined;

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header con botón volver */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors"
          >
            ← Volver al Dashboard
          </button>
          <span className="text-slate-400 text-sm">
            {formatMatchDate(match.date)}
          </span>
        </div>

        {/* Marcador Principal */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-lg p-8 shadow-xl border border-slate-600">
          <div className="grid grid-cols-[1fr_auto_1fr] gap-8 items-center">
            {/* Equipo Local */}
            <div className="text-right">
              <div className="text-3xl font-bold text-white mb-2">{match.home_team}</div>
              {isFinished && (
                <div className="text-6xl font-bold text-blue-400">{match.home_goals}</div>
              )}
            </div>

            {/* Separador / Marcador */}
            <div className="flex flex-col items-center gap-2">
              {isFinished ? (
                <>
                  <div className="text-4xl font-bold text-white">-</div>
                  <div className="text-xs px-3 py-1 bg-green-500/20 text-green-400 rounded font-bold">
                    FINALIZADO
                  </div>
                </>
              ) : (
                <div className="text-slate-400 text-lg font-semibold">vs</div>
              )}
            </div>

            {/* Equipo Visitante */}
            <div className="text-left">
              <div className="text-3xl font-bold text-white mb-2">{match.away_team}</div>
              {isFinished && (
                <div className="text-6xl font-bold text-orange-400">{match.away_goals}</div>
              )}
            </div>
          </div>

          {/* Árbitro */}
          {match.referee && (
            <div className="mt-6 pt-6 border-t border-slate-600 text-center text-slate-400">
              👨‍⚖️ Árbitro: {match.referee}
            </div>
          )}
        </div>

        {/* Predicciones de Estadísticas de Weinston */}
        <div className="bg-slate-800 rounded-lg p-6 shadow-xl border border-slate-700">
          <h2 className="text-2xl font-bold text-orange-400 mb-6 flex items-center gap-2">
            📊 Predicciones de Estadísticas (Weinston)
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="py-3 px-4 text-left text-slate-400 font-medium">Stat</th>
                  <th className="py-3 px-4 text-right text-blue-400 font-medium">{match.home_team}</th>
                  <th className="py-3 px-4 text-right text-orange-400 font-medium">{match.away_team}</th>
                  <th className="py-3 px-4 text-right text-slate-400 font-medium">Edge</th>
                  <th className="py-3 px-4 text-center text-purple-400 font-medium">🎯 Betting Line</th>
                </tr>
              </thead>
              <tbody>
                <StatPredictionRowWithBetting
                  label="Shots"
                  homeValue={safeNumber(match.weinston_shots_home)}
                  awayValue={safeNumber(match.weinston_shots_away)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  bettingLine={bettingLines?.shots}
                  renderBettingLine={renderBettingLine}
                />
                <StatPredictionRowWithBetting
                  label="Shots OT"
                  homeValue={safeNumber(match.weinston_shots_on_target_home)}
                  awayValue={safeNumber(match.weinston_shots_on_target_away)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  bettingLine={bettingLines?.shots_on_target}
                  renderBettingLine={renderBettingLine}
                />
                <StatPredictionRowWithBetting
                  label="Fouls"
                  homeValue={safeNumber(match.weinston_fouls_home)}
                  awayValue={safeNumber(match.weinston_fouls_away)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  bettingLine={bettingLines?.fouls}
                  renderBettingLine={renderBettingLine}
                />
                <StatPredictionRowWithBetting
                  label="Cards"
                  homeValue={safeNumber(match.weinston_cards_home)}
                  awayValue={safeNumber(match.weinston_cards_away)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  bettingLine={bettingLines?.cards}
                  renderBettingLine={renderBettingLine}
                />
                <StatPredictionRowWithBetting
                  label="Corners"
                  homeValue={safeNumber(match.weinston_corners_home)}
                  awayValue={safeNumber(match.weinston_corners_away)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  bettingLine={bettingLines?.corners}
                  renderBettingLine={renderBettingLine}
                />
              </tbody>
            </table>
          </div>

          {/* Leyenda de Betting Lines */}
          {!isFinished && bettingLines && (
            <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
              <p className="text-slate-300 text-sm font-semibold mb-3">🎯 Leyenda de Betting Lines:</p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-green-400">🔥 70-100%</span>
                  <span className="text-slate-400">= Alta confianza (apostar)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-yellow-400">🟢 40-70%</span>
                  <span className="text-slate-400">= Buena confianza</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-orange-400">🟡 20-40%</span>
                  <span className="text-slate-400">= Media confianza</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-500">⚪ 0-20%</span>
                  <span className="text-slate-400">= Baja confianza (no apostar)</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Estadísticas Reales (si el partido está finalizado) */}
        {isFinished && match.has_real_stats && (
          <div className="bg-slate-800 rounded-lg p-6 shadow-xl border border-green-500/20">
            <h2 className="text-2xl font-bold text-green-400 mb-6">📈 Estadísticas Reales del Partido</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-3">
                <StatRow 
                  label="Tiros"
                  homeValue={match.home_shots}
                  awayValue={match.away_shots}
                />
                <StatRow 
                  label="Tiros a Puerta"
                  homeValue={match.home_shots_on_target}
                  awayValue={match.away_shots_on_target}
                />
                <StatRow 
                  label="Faltas"
                  homeValue={match.home_fouls}
                  awayValue={match.away_fouls}
                />
              </div>
              <div className="space-y-3">
                <StatRow 
                  label="Corners"
                  homeValue={match.home_corners}
                  awayValue={match.away_corners}
                />
                <StatRow 
                  label="Tarjetas Amarillas"
                  homeValue={match.home_yellow_cards}
                  awayValue={match.away_yellow_cards}
                  color="yellow"
                />
                <StatRow 
                  label="Tarjetas Rojas"
                  homeValue={match.home_red_cards}
                  awayValue={match.away_red_cards}
                  color="red"
                />
              </div>

              {/* Totales del partido */}
              {(match.total_shots || match.total_corners || match.total_fouls || match.total_cards) && (
                <div className="col-span-2 mt-4 pt-4 border-t border-slate-700">
                  <h3 className="text-slate-400 text-sm font-semibold mb-3">Totales del Partido</h3>
                  <div className="grid grid-cols-4 gap-3">
                    {match.total_shots && (
                      <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                        <div className="text-slate-400 text-xs mb-1">Tiros Totales</div>
                        <div className="text-2xl font-bold text-white">{match.total_shots}</div>
                      </div>
                    )}
                    {match.total_corners && (
                      <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                        <div className="text-slate-400 text-xs mb-1">Corners Totales</div>
                        <div className="text-2xl font-bold text-white">{match.total_corners}</div>
                      </div>
                    )}
                    {match.total_fouls && (
                      <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                        <div className="text-slate-400 text-xs mb-1">Faltas Totales</div>
                        <div className="text-2xl font-bold text-white">{match.total_fouls}</div>
                      </div>
                    )}
                    {match.total_cards && (
                      <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                        <div className="text-slate-400 text-xs mb-1">Tarjetas Totales</div>
                        <div className="text-2xl font-bold text-yellow-400">{match.total_cards}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Predicciones */}
        <div className="grid grid-cols-2 gap-6">
          {/* Poisson */}
          <div className="bg-slate-800 rounded-lg p-6 border border-blue-500/20">
            <h3 className="text-xl font-bold text-blue-400 mb-4">Predicción Poisson</h3>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Marcador esperado:</span>
                <span className="text-white font-mono text-lg">
                  {safeNumber(match.poisson_home_goals).toFixed(1)} - {safeNumber(match.poisson_away_goals).toFixed(1)}
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Victoria Local (1):</span>
                  <span className="text-blue-300 font-mono">{(safeNumber(match.poisson_prob_home) * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Empate (X):</span>
                  <span className="text-slate-300 font-mono">{(safeNumber(match.poisson_prob_draw) * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Victoria Visitante (2):</span>
                  <span className="text-orange-300 font-mono">{(safeNumber(match.poisson_prob_away) * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-700 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Over/Under 2.5:</span>
                  <span className={`font-mono text-sm font-bold ${
                    safeNumber(match.poisson_over_25) > 0.5 ? 'text-green-400' : 'text-orange-400'
                  }`}>
                    {safeNumber(match.poisson_over_25) > 0.5
                      ? `OVER ${(safeNumber(match.poisson_over_25) * 100).toFixed(0)}%`
                      : `UNDER ${((1 - safeNumber(match.poisson_over_25)) * 100).toFixed(0)}%`
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">BTTS:</span>
                  <span className={`font-mono text-sm font-bold ${
                    safeNumber(match.poisson_btts) > 0.5 ? 'text-green-400' : 'text-orange-400'
                  }`}>
                    {safeNumber(match.poisson_btts) > 0.5
                      ? `YES ${(safeNumber(match.poisson_btts) * 100).toFixed(0)}%`
                      : `NO ${((1 - safeNumber(match.poisson_btts)) * 100).toFixed(0)}%`
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Weinston */}
          <div className="bg-slate-800 rounded-lg p-6 border border-orange-500/20">
            <h3 className="text-xl font-bold text-orange-400 mb-4">Predicción Weinston</h3>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Marcador esperado:</span>
                <span className="text-white font-mono text-lg">
                  {safeNumber(match.weinston_home_goals).toFixed(1)} - {safeNumber(match.weinston_away_goals).toFixed(1)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">Resultado predicho:</span>
                <span className="text-orange-300 font-mono text-lg font-bold">
                  {getResultLabel(match.weinston_result)}
                </span>
              </div>

              <div className="pt-3 border-t border-slate-700 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Over/Under 2.5:</span>
                  <span className={`font-mono text-sm font-bold ${
                    safeNumber(match.weinston_over_25) > 0.5 ? 'text-green-400' : 'text-orange-400'
                  }`}>
                    {safeNumber(match.weinston_over_25) > 0.5 
                      ? `OVER ${(safeNumber(match.weinston_over_25) * 100).toFixed(0)}%`
                      : `UNDER ${((1 - safeNumber(match.weinston_over_25)) * 100).toFixed(0)}%`
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">BTTS:</span>
                  <span className={`font-mono text-sm font-bold ${
                    safeNumber(match.weinston_btts) > 0.5 ? 'text-green-400' : 'text-orange-400'
                  }`}>
                    {safeNumber(match.weinston_btts) > 0.5
                      ? `YES ${(safeNumber(match.weinston_btts) * 100).toFixed(0)}%`
                      : `NO ${((1 - safeNumber(match.weinston_btts)) * 100).toFixed(0)}%`
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Componente auxiliar para filas de estadísticas
interface StatRowProps {
  label: string;
  homeValue: number;
  awayValue: number;
  color?: 'blue' | 'yellow' | 'red';
}

function StatRow({ label, homeValue, awayValue, color = 'blue' }: StatRowProps) {
  const total = homeValue + awayValue || 1;
  const homePercentage = (homeValue / total) * 100;
  const awayPercentage = (awayValue / total) * 100;

  const getColorClass = () => {
    if (color === 'yellow') return 'bg-yellow-600';
    if (color === 'red') return 'bg-red-600';
    return 'bg-blue-600';
  };

  const getColorClassAway = () => {
    if (color === 'yellow') return 'bg-yellow-500';
    if (color === 'red') return 'bg-red-500';
    return 'bg-orange-600';
  };

  return (
    <div className="bg-slate-700/50 rounded p-3">
      <div className="text-center text-slate-300 text-sm font-semibold mb-2">
        {label}
      </div>
      <div className="flex justify-between text-white font-bold mb-2">
        <span>{homeValue}</span>
        <span>{awayValue}</span>
      </div>
      <div className="flex gap-1 h-2 rounded overflow-hidden">
        <div className={`${getColorClass()} transition-all`} style={{ width: `${homePercentage}%` }} />
        <div className={`${getColorClassAway()} transition-all`} style={{ width: `${awayPercentage}%` }} />
      </div>
    </div>
  );
}

// 🎯 COMPONENTE MEJORADO CON BETTING LINE
interface StatPredictionRowWithBettingProps {
  label: string;
  homeValue: number;
  awayValue: number;
  homeTeam: string;
  awayTeam: string;
  bettingLine?: BettingLine;
  renderBettingLine: (line: BettingLine | undefined) => JSX.Element;
}

function StatPredictionRowWithBetting({ 
  label, 
  homeValue, 
  awayValue, 
  homeTeam, 
  awayTeam,
  bettingLine,
  renderBettingLine
}: StatPredictionRowWithBettingProps) {
  const getEdge = () => {
    if (homeValue > awayValue) return homeTeam;
    if (awayValue > homeValue) return awayTeam;
    return '-';
  };

  const edge = getEdge();

  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
      <td className="py-3 px-4 text-slate-300 font-medium">{label}</td>
      <td className="py-3 px-4 text-right text-blue-300 font-mono">
        {homeValue > 0 ? homeValue.toFixed(2) : '0.00'}
      </td>
      <td className="py-3 px-4 text-right text-orange-300 font-mono">
        {awayValue > 0 ? awayValue.toFixed(2) : '0.00'}
      </td>
      <td className="py-3 px-4 text-right">
        {edge !== '-' ? (
          <span className={`px-3 py-1 rounded text-xs font-bold ${
            edge === homeTeam 
              ? 'bg-blue-500/20 text-blue-400' 
              : 'bg-orange-500/20 text-orange-400'
          }`}>
            {edge}
          </span>
        ) : (
          <span className="text-slate-500">-</span>
        )}
      </td>
      {/* 🎯 NUEVA COLUMNA DE BETTING LINE */}
      <td className="py-3 px-4 text-center">
        {renderBettingLine(bettingLine)}
      </td>
    </tr>
  );
}