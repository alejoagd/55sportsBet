import { useState, useEffect } from 'react';
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
  home_possession: number;
  away_possession: number;
  
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

export default function MatchDetail() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const [match, setMatch] = useState<MatchStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMatchDetails();
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

  const safeNumber = (value: any, defaultValue: number = 0): number => {
    if (value === null || value === undefined || isNaN(value)) {
      return defaultValue;
    }
    return Number(value);
  };

  const getResultLabel = (result: string) => {
    if (result === 'H' || result === '1') return '1';
    if (result === 'A' || result === '2') return '2';
    return 'X';
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
            {new Date(match.date).toLocaleDateString('es-ES', {
              weekday: 'long',
              day: '2-digit',
              month: 'long',
              year: 'numeric'
            })}
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
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold">Stat</th>
                  <th className="text-right py-3 px-4 text-blue-400 font-semibold">{match.home_team}</th>
                  <th className="text-right py-3 px-4 text-orange-400 font-semibold">{match.away_team}</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold">Edge</th>
                </tr>
              </thead>
              <tbody>
                {/* Tiros */}
                <StatPredictionRow
                  label="Shots"
                  homeValue={safeNumber(match.home_shots)}
                  awayValue={safeNumber(match.away_shots)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
                
                {/* Tiros a puerta */}
                <StatPredictionRow
                  label="Shots OT"
                  homeValue={safeNumber(match.home_shots_on_target)}
                  awayValue={safeNumber(match.away_shots_on_target)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
                
                {/* Faltas */}
                <StatPredictionRow
                  label="Fouls"
                  homeValue={safeNumber(match.home_fouls)}
                  awayValue={safeNumber(match.away_fouls)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
                
                {/* Tarjetas */}
                <StatPredictionRow
                  label="Cards"
                  homeValue={safeNumber(match.home_yellow_cards)}
                  awayValue={safeNumber(match.away_yellow_cards)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
                
                {/* Corners */}
                <StatPredictionRow
                  label="Corners"
                  homeValue={safeNumber(match.home_corners)}
                  awayValue={safeNumber(match.away_corners)}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
                
                {/* Win Corners */}
                <tr className="border-b border-slate-700/50">
                  <td className="py-3 px-4 text-slate-300">Win Corners</td>
                  <td className="py-3 px-4 text-right" colSpan={2}></td>
                  <td className="py-3 px-4 text-right">
                    <span className={`px-3 py-1 rounded text-xs font-bold ${
                      safeNumber(match.home_corners) > safeNumber(match.away_corners)
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-orange-500/20 text-orange-400'
                    }`}>
                      {safeNumber(match.home_corners) > safeNumber(match.away_corners)
                        ? 'HOME'
                        : 'AWAY'}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Estadísticas del Partido (solo para partidos finalizados) */}
        {isFinished && (
          <div className="bg-slate-800 rounded-lg p-6 shadow-xl border border-slate-700">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              📊 Estadísticas del Partido
            </h2>

            <div className="space-y-4">
              {/* Posesión */}
              <div>
                <div className="flex justify-between text-sm text-slate-400 mb-2">
                  <span>{match.home_team}</span>
                  <span className="font-bold">Posesión</span>
                  <span>{match.away_team}</span>
                </div>
                <div className="flex gap-2">
                  <div className="flex-1 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold"
                       style={{ width: `${safeNumber(match.home_possession)}%` }}>
                    {safeNumber(match.home_possession)}%
                  </div>
                  <div className="flex-1 h-8 bg-orange-600 rounded flex items-center justify-center text-white font-bold"
                       style={{ width: `${safeNumber(match.away_possession)}%` }}>
                    {safeNumber(match.away_possession)}%
                  </div>
                </div>
              </div>

              {/* Grid de estadísticas */}
              <div className="grid grid-cols-3 gap-4 mt-6">
                {/* Tiros */}
                <StatRow
                  label="Tiros"
                  homeValue={safeNumber(match.home_shots)}
                  awayValue={safeNumber(match.away_shots)}
                />

                {/* Tiros a puerta */}
                <StatRow
                  label="Tiros a puerta"
                  homeValue={safeNumber(match.home_shots_on_target)}
                  awayValue={safeNumber(match.away_shots_on_target)}
                />

                {/* Faltas */}
                <StatRow
                  label="Faltas"
                  homeValue={safeNumber(match.home_fouls)}
                  awayValue={safeNumber(match.away_fouls)}
                />

                {/* Corners */}
                <StatRow
                  label="Corners"
                  homeValue={safeNumber(match.home_corners)}
                  awayValue={safeNumber(match.away_corners)}
                />

                {/* Tarjetas amarillas */}
                <StatRow
                  label="Tarjetas amarillas"
                  homeValue={safeNumber(match.home_yellow_cards)}
                  awayValue={safeNumber(match.away_yellow_cards)}
                  color="yellow"
                />

                {/* Tarjetas rojas */}
                <StatRow
                  label="Tarjetas rojas"
                  homeValue={safeNumber(match.home_red_cards)}
                  awayValue={safeNumber(match.away_red_cards)}
                  color="red"
                />
              </div>
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

// Componente auxiliar para filas de predicciones de estadísticas
interface StatPredictionRowProps {
  label: string;
  homeValue: number;
  awayValue: number;
  homeTeam: string;
  awayTeam: string;
}

function StatPredictionRow({ label, homeValue, awayValue, homeTeam, awayTeam }: StatPredictionRowProps) {
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
    </tr>
  );
}