// ============================================================================
// BestBetsSection.tsx - VERSIÓN CORREGIDA
// ============================================================================
//
// PROBLEMA IDENTIFICADO:
// - Llamaba a /history sin season_id (error 422)
// - No mostraba info de liga
//
// SOLUCIÓN:
// - Llamar sin season_id (multiliga automático)
// - Mostrar info de liga cuando esté disponible
// - Fallback si no hay datos de liga
//
// ============================================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminOnly } from './AdminButton';
import ScoreRangeEffectiveness from './Scorerangeeffectiveness';
import i18n, { localeTag } from './i18n';

interface H2HTopPick {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;
  home_team_logo?: string | null;
  away_team_logo?: string | null;
  league: string;
  stat: string;
  stat_label: string;
  prediction: string;
  line: number | null;
  score: number;
  h2h_valid_matches: number;
  historical_accuracy: number;
  historical_sample: number;
}

interface BestBet {
  id: number;
  match_id: number;
  season_id: number;
  date: string;
  home_team: string;
  away_team: string;
  home_team_logo?: string | null;
  away_team_logo?: string | null;
  league?: string;           // Opcional (puede no venir del backend)
  league_emoji?: string;     // Opcional
  country?: string;          // Opcional
  model: string;
  bet_type: string;
  prediction: string;
  confidence: number;
  historical_accuracy: number;
  combined_score: number;
  rank: number;
  odds?: number | null;
  hit?: boolean | null;
  profit_loss?: number | null;
}

function TeamLogo({ url, alt }: { url?: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return (
      <span className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-slate-700/60 flex items-center justify-center shrink-0 text-xs">
        ⚽
      </span>
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      className="w-6 h-6 sm:w-7 sm:h-7 object-contain shrink-0"
      onError={() => setFailed(true)}
    />
  );
}

// Etiqueta traducida del stat de cada pick H2H (el backend la manda en español).
const PICK_STAT_KEYS: Record<string, string> = {
  goles: 'bestBets.goles',
  tiros: 'bestBets.tiros',
  tiros_al_arco: 'bestBets.tirosAPuerta',
  faltas: 'bestBets.faltas',
  tarjetas: 'bestBets.tarjetas',
  corners: 'bestBets.corners',
};

export default function BestBetsSection() {
  const navigate = useNavigate();
  const [topBets, setTopBets] = useState<BestBet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [h2hPicks, setH2hPicks] = useState<H2HTopPick[]>([]);
  const [h2hPicksLoading, setH2hPicksLoading] = useState(true);
  const [h2hPicksError, setH2hPicksError] = useState<string | null>(null);

  useEffect(() => {
    fetchBestBets();
    fetchTopH2hPicks();
  }, []);

  const fetchTopH2hPicks = async () => {
    setH2hPicksLoading(true);
    setH2hPicksError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/h2h-score/top-upcoming-picks?min_sample=10&limit=4`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error ${response.status}: ${errorText}`);
      }
      const data = await response.json();
      setH2hPicks(data.picks || []);
    } catch (error) {
      console.error('❌ Error fetching top H2H picks:', error);
      setH2hPicksError(error instanceof Error ? error.message : i18n.t('bestBets.errorDesconocido'));
    } finally {
      setH2hPicksLoading(false);
    }
  };

  const fetchBestBets = async () => {
    setLoading(true);
    setError(null);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // Sin season_id para obtener MULTILIGA
      const response = await fetch(
        `${API_URL}/api/best-bets/history?limit=4&validated=false`
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Error ${response.status}: ${errorText}`);
      }
      
      const data: BestBet[] = await response.json();

      console.log('✅ Best bets recibidas:', data);

      // Ordenar por combined_score DESC (mayor score primero)
      // El backend ya debería ordenar correctamente, pero esto es una doble verificación
      const sorted = data.sort((a, b) => b.combined_score - a.combined_score);
      setTopBets(sorted);
      
    } catch (error) {
      console.error('❌ Error fetching best bets:', error);
      setError(error instanceof Error ? error.message : i18n.t('bestBets.errorDesconocido'));
    } finally {
      setLoading(false);
    }
  };

  // Función para refrescar análisis (solo admin)
  const refreshAnalysis = async () => {
    setRefreshing(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const today = new Date();
      const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
      
      const dateFrom = today.toISOString().split('T')[0];
      const dateTo = nextWeek.toISOString().split('T')[0];
      
      const response = await fetch(
        `${API_URL}/api/best-bets/analysis-multiliga?date_from=${dateFrom}&date_to=${dateTo}&top_n=4`
      );
      
      if (response.ok) {
        setTimeout(() => {
          fetchBestBets();
          setRefreshing(false);
        }, 1000);
      } else {
        throw new Error(i18n.t('bestBets.errorAlActualizar'));
      }
    } catch (error) {
      console.error('Error:', error);
      alert(i18n.t('bestBets.errorAlActualizarAnalisisAsegurate'));
      setRefreshing(false);
    }
  };

  const formatMatchDate = (dateString: string): string => {
    if (!dateString) return '';
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString(localeTag(), {
      weekday: 'short',
      day: '2-digit',
      month: 'short'
    });
  };

  const getScoreColor = (score: number): string => {
    if (score >= 50) return 'text-green-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getScoreBgColor = (score: number): string => {
    if (score >= 50) return 'bg-green-500/20 border-green-500/30';
    if (score >= 40) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-orange-500/20 border-orange-500/30';
  };

  const formatBetType = (betType: string): string => {
    const types: Record<string, string> = {
      '1X2': '1X2',
      'OVER_25': 'Over/Under 2.5',
      'Over/Under': 'Over/Under 2.5',
      'BTTS': 'BTTS',
      'CORNERS': i18n.t('bestBets.corners'),
      'SHOTS': i18n.t('bestBets.tiros'),
      'SHOTS_ON_TARGET': i18n.t('bestBets.tirosAPuerta'),
      'CARDS': i18n.t('bestBets.tarjetas'),
      'FOULS': i18n.t('bestBets.faltas')
    };
    return types[betType] || betType;
  };

  const getLeagueStats = () => {
    const leagueCount: Record<string, number> = {};
    topBets.forEach(bet => {
      if (bet.league) {
        leagueCount[bet.league] = (leagueCount[bet.league] || 0) + 1;
      }
    });
    return leagueCount;
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="text-center text-slate-400">{i18n.t('bestBets.cargandoMejoresApuestas')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-red-500/30">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ {error}</div>
          <button
            onClick={fetchBestBets}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            {i18n.t('bestBets.reintentar')}</button>
        </div>
      </div>
    );
  }

  if (topBets.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="text-center text-slate-400">
          <div className="text-6xl mb-4">🎯</div>
          <div className="text-xl font-bold text-white mb-2">{i18n.t('bestBets.noHayApuestasRecomendadasAun')}</div>
        </div>
      </div>
    );
  }

  const leagueStats = getLeagueStats();

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg p-4 sm:p-6 border border-green-500/30">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 mb-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="text-3xl sm:text-4xl">🎯</span>
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-white">
                {i18n.t('bestBets.top4')}
                {Object.keys(leagueStats).length > 1 && (
                  <span className="ml-2 text-xs sm:text-sm font-normal text-green-400">{i18n.t('bestBets.multiliga')}</span>
                )}
              </h2>
              <p className="text-slate-400 text-xs sm:text-sm">
                {Object.keys(leagueStats).length > 1
                  ? i18n.t('bestBets.analisisDeTodasLasLigas')
                  : i18n.t('bestBets.mejoresApuestasDeLaSemana')}
              </p>
            </div>
          </div>

          <AdminOnly hideCompletely={true}>
            <button
              onClick={refreshAnalysis}
              disabled={refreshing}
              className="w-full sm:w-auto px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded-lg transition-colors text-sm font-semibold"
            >
              {refreshing ? i18n.t('bestBets.actualizando') : i18n.t('bestBets.actualizar')}
            </button>
          </AdminOnly>
        </div>

        {/* Estadísticas de ligas */}
        {Object.keys(leagueStats).length > 0 && (
          <div className="flex gap-2 sm:gap-3 flex-wrap">
            <div className="text-slate-400 text-xs sm:text-sm font-semibold">{i18n.t('bestBets.ligas')}</div>
            {Object.entries(leagueStats).map(([league, count]) => (
              <div key={league} className="bg-slate-800/50 rounded-full px-2 sm:px-3 py-1 text-xs sm:text-sm">
                <span className="text-white font-semibold">{league || i18n.t('bestBets.liga')}</span>
                <span className="text-slate-400 ml-1">({count})</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ScoreRangeEffectiveness */}
      <ScoreRangeEffectiveness seasonId={topBets[0]?.season_id || 2} />

      {/* Top 4 Apuestas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {topBets.map((bet) => (
          <div
            key={bet.id}
            onClick={() => navigate(`/match/${bet.match_id}`, { state: { returnPath: '/best-bets' } })}
            className={`relative bg-slate-800 rounded-lg p-4 sm:p-6 border-2 cursor-pointer hover:scale-[1.02] transition-transform ${getScoreBgColor(bet.combined_score)}`}
          >
            {/* Badge de ranking */}
            <div className="absolute -top-3 -left-3 w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center shadow-lg">
              <span className="text-slate-900 font-bold text-lg sm:text-xl">#{bet.rank}</span>
            </div>

            {/* Info de liga (si existe) */}
            {bet.league && (
              <div className="absolute -top-2 -right-2 bg-slate-900 border border-slate-700 rounded-full px-2 sm:px-3 py-1 text-xs font-bold shadow-lg flex items-center gap-1">
                {bet.league_emoji && <span>{bet.league_emoji}</span>}
                <span className="text-white text-xs">{bet.league}</span>
              </div>
            )}

            {/* Fecha */}
            <div className="text-right text-slate-400 text-xs sm:text-sm mb-3 mt-2">
              {formatMatchDate(bet.date)}
            </div>

            {/* Equipos */}
            <div className="flex items-center justify-center gap-2 sm:gap-3 mb-4">
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <TeamLogo url={bet.home_team_logo} alt={bet.home_team} />
                <span className="text-base sm:text-lg md:text-xl font-bold text-white line-clamp-2 break-words leading-tight">{bet.home_team}</span>
              </div>
              <span className="text-slate-500 text-sm sm:text-base shrink-0">vs</span>
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <TeamLogo url={bet.away_team_logo} alt={bet.away_team} />
                <span className="text-base sm:text-lg md:text-xl font-bold text-white line-clamp-2 break-words leading-tight">{bet.away_team}</span>
              </div>
            </div>

            {/* Predicción */}
            <div className="bg-slate-900/50 rounded-lg p-3 sm:p-4 mb-4">
              <div className="text-center">
                <div className="text-slate-400 text-xs sm:text-sm mb-1">{i18n.t('bestBets.apuestaRecomendada')}</div>
                <div className="text-xl sm:text-2xl font-bold text-green-400 mb-2">
                  {bet.prediction}
                </div>
                <div className="text-slate-400 text-xs">
                  {formatBetType(bet.bet_type)}
                </div>
              </div>
            </div>

            {/* Métricas */}
            <div className="grid grid-cols-3 gap-2 sm:gap-3">
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">Score</div>
                <div className={`text-xl font-bold ${getScoreColor(bet.combined_score)}`}>
                  {bet.combined_score.toFixed(1)}
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">{i18n.t('bestBets.confianza')}</div>
                <div className="text-xl font-bold text-blue-400">
                  {bet.confidence.toFixed(0)}%
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-slate-400 text-xs mb-1">{i18n.t('bestBets.historico')}</div>
                <div className="text-xl font-bold text-purple-400">
                  {bet.historical_accuracy.toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Modelo */}
            <div className="mt-4 pt-4 border-t border-slate-700 text-center">
              <span className={`text-sm font-semibold capitalize ${
                bet.model === 'poisson' ? 'text-blue-400' : 'text-orange-400'
              }`}>
                {i18n.t('bestBets.modelValue', { model: bet.model })}
              </span>
            </div>

            {/* Indicadores */}
            {bet.combined_score >= 50 && (
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg whitespace-nowrap">
                {i18n.t('bestBets.altaConfianza')}</div>
            )}

            {bet.hit !== null && (
              <div className={`absolute top-2 left-2 px-2 py-1 rounded text-xs font-bold ${
                bet.hit ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 
                'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {bet.hit ? i18n.t('bestBets.acerto') : i18n.t('bestBets.fallo')}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Explicación */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="text-slate-300 text-sm space-y-2">
          <div className="font-semibold text-white mb-2">{i18n.t('bestBets.comoFunciona')}</div>
          
          <div className="mb-3">
            <span className="text-green-400 font-mono">Score</span> = 
            <span className="text-blue-400 font-mono"> {i18n.t('bestBets.confianza')}</span> × 
            <span className="text-purple-400 font-mono"> {i18n.t('bestBets.historico')}</span>
          </div>
          
          <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
            <li>
              <strong className="text-blue-400">{i18n.t('bestBets.confianza2')}</strong> {i18n.t('bestBets.probabilidadQueAsignaElModelo')}</li>
            <li>
              <strong className="text-purple-400">{i18n.t('bestBets.historico2')}</strong> {i18n.t('bestBets.deAciertosDelModelo')}</li>
            <li>
              <strong className="text-green-400">Score:</strong> {i18n.t('bestBets.mayorScoreMayorProbabilidad')}</li>
            {Object.keys(leagueStats).length > 1 && (
              <li>
                <strong className="text-yellow-400">{i18n.t('bestBets.multiliga2')}</strong> {i18n.t('bestBets.seAnalizanTodasLasLigas')}</li>
            )}
          </ul>
        </div>
      </div>

      {/* Top 4 pronósticos H2H más confiables (próximos partidos) */}
      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 rounded-lg p-4 sm:p-6 border border-purple-500/30">
        <div className="flex items-center gap-2 sm:gap-3 mb-1">
          <span className="text-3xl sm:text-4xl">🔬</span>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">{i18n.t('bestBets.pronosticosH2hConMayorRespaldo')}</h2>
            <p className="text-slate-400 text-xs sm:text-sm">
              {i18n.t('bestBets.los4PronosticosConMayor')}</p>
          </div>
        </div>

        {h2hPicksLoading ? (
          <div className="text-center text-slate-400 py-8">{i18n.t('bestBets.calculandoPuntuacionesH2hEnVivo')}</div>
        ) : h2hPicksError ? (
          <div className="text-center text-red-400 py-8">❌ {h2hPicksError}</div>
        ) : h2hPicks.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            {i18n.t('bestBets.noHayPronosticosProximosCon')}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {h2hPicks.map((pick, i) => {
              const isOver = pick.prediction.startsWith('OVER');
              return (
                <div
                  key={`${pick.match_id}-${pick.stat}`}
                  onClick={() => navigate(`/match/${pick.match_id}`, { state: { returnPath: '/best-bets' } })}
                  className="relative bg-slate-800 rounded-lg p-4 border-2 border-purple-500/30 cursor-pointer hover:scale-[1.02] transition-transform"
                >
                  <div className="absolute -top-3 -left-3 w-9 h-9 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                    <span className="text-white font-bold text-sm">#{i + 1}</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400 text-xs mb-2 mt-1">
                    <span>{pick.league}</span>
                    <span>{formatMatchDate(pick.date)}</span>
                  </div>

                  <div className="flex items-center justify-center gap-2 mb-3">
                    <TeamLogo url={pick.home_team_logo} alt={pick.home_team} />
                    <span className="text-white font-bold text-sm line-clamp-2 break-words leading-tight">{pick.home_team}</span>
                    <span className="text-slate-500 text-xs shrink-0">vs</span>
                    <TeamLogo url={pick.away_team_logo} alt={pick.away_team} />
                    <span className="text-white font-bold text-sm line-clamp-2 break-words leading-tight">{pick.away_team}</span>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-3 mb-3 text-center">
                    <div className="text-slate-400 text-xs mb-1">{i18n.t('bestBets.pronosticoH2h')}</div>
                    <div className="text-lg font-bold text-purple-300">
                      {isOver ? i18n.t('bestBets.masDe') : i18n.t('bestBets.menosDe')} {pick.line} {PICK_STAT_KEYS[pick.stat] ? i18n.t(PICK_STAT_KEYS[pick.stat]) : pick.stat_label}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
                      <div className="text-slate-400 text-xs mb-1">{i18n.t('bestBets.puntuacionH2h')}</div>
                      <div className="text-lg font-bold text-white">{pick.score}/{pick.h2h_valid_matches}</div>
                    </div>
                    <div className="bg-green-500/20 rounded-lg p-2.5 text-center">
                      <div className="text-slate-400 text-xs mb-1">{i18n.t('bestBets.aciertoRealHistorico')}</div>
                      <div className="text-lg font-bold text-green-400">{pick.historical_accuracy.toFixed(0)}%</div>
                    </div>
                  </div>
                  <div className="text-center text-slate-500 text-[11px] mt-2">
                    {i18n.t('bestBets.basedOnPast', { n: pick.historical_sample, league: pick.league })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}