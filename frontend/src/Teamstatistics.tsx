import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Trans } from 'react-i18next';
import i18n from './i18n';

interface TeamStats {
  team_id: number;
  team_name: string;
  home_matches: number;
  away_matches: number;
  total_matches: number;
  home_avg_goals_scored: number;
  away_avg_goals_scored: number;
  home_total_goals_scored: number;
  away_total_goals_scored: number;
  home_avg_goals_conceded: number;
  away_avg_goals_conceded: number;
  home_total_goals_conceded: number;
  away_total_goals_conceded: number;
  home_avg_goals_1h: number | null;
  away_avg_goals_1h: number | null;
  home_avg_goals_2h: number | null;
  away_avg_goals_2h: number | null;
  home_matches_ht: number;
  away_matches_ht: number;
  home_avg_corners: number;
  away_avg_corners: number;
  home_total_corners: number;
  away_total_corners: number;
  home_avg_shots: number;
  away_avg_shots: number;
  home_total_shots: number;
  away_total_shots: number;
  home_avg_shots_target: number;
  away_avg_shots_target: number;
  home_total_shots_target: number;
  away_total_shots_target: number;
  home_avg_fouls: number;
  away_avg_fouls: number;
  home_total_fouls: number;
  away_total_fouls: number;
  home_avg_cards: number;
  away_avg_cards: number;
  home_total_cards: number;
  away_total_cards: number;
}

interface RefereeStats {
  referee: string;
  matches_officiated: number;
  avg_fouls_per_match: number;
  total_fouls: number;
  avg_cards_per_match: number;
  total_cards: number;
}

interface StatsResponse {
  season_id: number;
  round_label: string | null;
  date_from: string | null;
  date_to: string | null;
  has_match_stats: boolean;
  has_halftime_data: boolean;
  teams: TeamStats[];
  referees: RefereeStats[];
}

interface AttackQualityTeam {
  team_id: number;
  team_name: string;
  matches_used: number;
  aqi: number | null;
  volume_idx?: number;
  finishing_idx?: number;
  precision_pct?: number | null;
  avg_shots_on_target?: number;
  avg_goals?: number;
  expected_goals?: number;
}

interface AttackQualityResponse {
  has_match_stats: boolean;
  window: number;
  teams: AttackQualityTeam[];
}

export default function TeamStatistics({ embedded = false }: { embedded?: boolean } = {}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const leagueParam = searchParams.get('league');
  const [currentLeagueId, setCurrentLeagueId] = useState<number | null>(
    leagueParam ? parseInt(leagueParam, 10) : null
  );

  const [seasonId, setSeasonId] = useState<number | null>(null);
  const [leagueName, setLeagueName] = useState<string>('');
  const [leagueEmoji, setLeagueEmoji] = useState<string>('⚽');

  const [data, setData] = useState<StatsResponse | null>(null);
  const [attackQuality, setAttackQuality] = useState<AttackQualityResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Sin ?league= en la URL: tomar la primera liga activa (igual que ImprovedDashboard)
  useEffect(() => {
    if (currentLeagueId !== null) return;
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/leagues/active`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((leagues: { id: number }[]) => {
        if (leagues.length > 0) {
          setCurrentLeagueId(leagues[0].id);
          setSearchParams(prev => {
            const next = new URLSearchParams(prev);
            next.set('league', String(leagues[0].id));
            return next;
          }, { replace: true });
        }
      })
      .catch(() => setCurrentLeagueId(1));
  }, []);

  // ?league= cambió (via LeagueSidebar/LeagueMobilePanel) → sincronizar
  useEffect(() => {
    const param = searchParams.get('league');
    if (!param) return;
    const leagueFromUrl = parseInt(param, 10);
    if (leagueFromUrl !== currentLeagueId) {
      setCurrentLeagueId(leagueFromUrl);
    }
  }, [searchParams]);

  // Resolver season_id/nombre/emoji reales desde el backend
  useEffect(() => {
    if (currentLeagueId === null) return;
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/leagues/${currentLeagueId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((leagueData: { seasonId: number; name: string; emoji: string }) => {
        setSeasonId(leagueData.seasonId);
        setLeagueName(leagueData.name || '');
        setLeagueEmoji(leagueData.emoji || '⚽');
      })
      .catch((error) => console.error('❌ Error obteniendo season_id:', error));
  }, [currentLeagueId]);

  // Función de fetch con useCallback
  const fetchStatistics = useCallback(async (seasonId: number) => {
    setLoading(true);
    setData(null); // Limpiar datos anteriores IMPORTANTE

    try {
      const today = new Date().toISOString().split('T')[0];

      const params = new URLSearchParams({
        season_id: seasonId.toString(),
        date_from: '2024-08-01',
        date_to: today
      });

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${API_URL}/api/team-statistics?${params}`;
      
      console.log('🔗 URL:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      console.log('✅ Data loaded:');
      console.log('   Teams:', result.teams?.length || 0);
      console.log('   Referees:', result.referees?.length || 0);
      console.log('   Season ID in response:', result.season_id);
      
      // Verificar que el season_id de la respuesta coincide
      if (result.season_id !== seasonId) {
        console.warn('⚠️  MISMATCH: Expected season_id', seasonId, 'but got', result.season_id);
      }
      
      setData(result);
      
    } catch (error) {
      console.error('❌ Error fetching statistics:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch cuando cambia seasonId
  useEffect(() => {
    if (seasonId && seasonId > 0) {
      fetchStatistics(seasonId);
    }
  }, [seasonId, fetchStatistics]);

  // Índice de Calidad de Ataque: independiente de /api/team-statistics, así que
  // si falla solo se oculta su sección y el resto de la vista sigue igual.
  useEffect(() => {
    if (!seasonId || seasonId <= 0) return;
    setAttackQuality(null);
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/team-attack-quality?season_id=${seasonId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((result: AttackQualityResponse) => setAttackQuality(result))
      .catch(() => setAttackQuality(null));
  }, [seasonId]);

  // Funciones para obtener rankings
  const getTopTeams = (key: keyof TeamStats, limit: number = 5, ascending: boolean = false) => {
    if (!data || !data.teams) return [];
    return [...data.teams]
      .sort((a, b) => ascending ? (a[key] as number) - (b[key] as number) : (b[key] as number) - (a[key] as number))
      .slice(0, limit);
  };

  const renderRankingTable = (
    title: string,
    teams: TeamStats[],
    valueKey: keyof TeamStats,
    color: string,
    matchesKey?: keyof TeamStats
  ) => (
    <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
      <h3 className={`text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight ${color}`}>{title}</h3>
      {teams.length === 0 ? (
        <div className="text-slate-500 text-center py-4 text-xs sm:text-base">{i18n.t('teamStats.noHayDatos')}</div>
      ) : (
        <div className="space-y-1.5 sm:space-y-2">
          {teams.map((team, idx) => {
            // Cuántos partidos (de local o visitante, según qué lado mide
            // valueKey) respaldan este promedio — con muy pocos partidos
            // (ej. 1 en las primeras fechas) el número es real pero todavía
            // no representa un promedio estable, así que se muestra para
            // que se pueda juzgar con contexto en vez de leerse como dato
            // definitivo.
            const sideMatches = matchesKey
              ? (team[matchesKey] as number)
              : (valueKey as string).startsWith('home_') ? team.home_matches : team.away_matches;
            const lowSample = sideMatches < 3;
            return (
              <div
                key={team.team_id}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0"
              >
                <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                  <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                  <span className="text-white font-medium text-xs sm:text-base truncate">{team.team_name}</span>
                </div>
                <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0 flex-wrap sm:flex-nowrap">
                  <span className={`font-bold text-xs sm:text-base whitespace-nowrap ${color}`}>
                    {typeof team[valueKey] === 'number' ? team[valueKey].toFixed(2) : team[valueKey]}
                  </span>
                  <span
                    className={`text-[9px] sm:text-[11px] font-medium px-1 rounded shrink-0 whitespace-nowrap ${lowSample ? 'text-amber-400 bg-amber-500/10' : 'text-slate-500'}`}
                    title={i18n.t('teamStats.partidosJugadosQueRespaldanEste')}
                  >
                    {i18n.t('teamStats.sample', { n: sideMatches })}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  if (loading) {
    const inner = (
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-slate-400">{leagueName ? i18n.t('teamStats.loadingStatsLeague', { league: leagueName }) : i18n.t('teamStats.loadingStats')}</p>
      </div>
    );
    return embedded
      ? <div className="flex items-center justify-center py-16">{inner}</div>
      : <div className="min-h-screen bg-slate-950 flex items-center justify-center h-96">{inner}</div>;
  }

  if (!data || !data.teams || data.teams.length === 0) {
    const inner = (
      <>
        <div className="text-6xl mb-4">{leagueEmoji}</div>
        <div className="text-slate-400 text-xl">{i18n.t('teamStats.noDataFor', { league: leagueName })}</div>
        <button
          onClick={() => seasonId && fetchStatistics(seasonId)}
          className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          {i18n.t('teamStats.reintentar')}</button>
      </>
    );
    return embedded
      ? <div className="text-center py-16">{inner}</div>
      : <div className="min-h-screen bg-slate-950 p-6 text-center">{inner}</div>;
  }

  const topHomeOffense = getTopTeams('home_avg_goals_scored', 5);
  const bottomHomeOffense = getTopTeams('home_avg_goals_scored', 5, true);
  const topAwayOffense = getTopTeams('away_avg_goals_scored', 5);
  const bottomAwayOffense = getTopTeams('away_avg_goals_scored', 5, true);

  const topHomeDefense = getTopTeams('home_avg_goals_conceded', 5, true);
  const bottomHomeDefense = getTopTeams('home_avg_goals_conceded', 5);
  const topAwayDefense = getTopTeams('away_avg_goals_conceded', 5, true);
  const bottomAwayDefense = getTopTeams('away_avg_goals_conceded', 5);

  const topHomeGoals1h = getTopTeams('home_avg_goals_1h', 5);
  const topAwayGoals1h = getTopTeams('away_avg_goals_1h', 5);
  const topHomeGoals2h = getTopTeams('home_avg_goals_2h', 5);
  const topAwayGoals2h = getTopTeams('away_avg_goals_2h', 5);

  const topHomeCorners = getTopTeams('home_avg_corners', 5);
  const bottomHomeCorners = getTopTeams('home_avg_corners', 5, true);
  const topAwayCorners = getTopTeams('away_avg_corners', 5);
  const bottomAwayCorners = getTopTeams('away_avg_corners', 5, true);

  const topHomeShots = getTopTeams('home_avg_shots', 5);
  const bottomHomeShots = getTopTeams('home_avg_shots', 5, true);
  const topAwayShots = getTopTeams('away_avg_shots', 5);
  const bottomAwayShots = getTopTeams('away_avg_shots', 5, true);

  const topHomeShotsTarget = getTopTeams('home_avg_shots_target', 5);
  const bottomHomeShotsTarget = getTopTeams('home_avg_shots_target', 5, true);
  const topAwayShotsTarget = getTopTeams('away_avg_shots_target', 5);
  const bottomAwayShotsTarget = getTopTeams('away_avg_shots_target', 5, true);

  const topHomeFouls = getTopTeams('home_avg_fouls', 5);
  const bottomHomeFouls = getTopTeams('home_avg_fouls', 5, true);
  const topAwayFouls = getTopTeams('away_avg_fouls', 5);
  const bottomAwayFouls = getTopTeams('away_avg_fouls', 5, true);

  const topHomeCards = getTopTeams('home_avg_cards', 5);
  const bottomHomeCards = getTopTeams('home_avg_cards', 5, true);
  const topAwayCards = getTopTeams('away_avg_cards', 5);
  const bottomAwayCards = getTopTeams('away_avg_cards', 5, true);

  // "Sin arbitro" es el valor de relleno de la carga de datos cuando la liga no trae
  // árbitro (ej. La Liga): no es un árbitro real, no debe entrar al ranking ni al conteo.
  const realReferees = (data.referees ?? []).filter(r => r.referee.trim().toLowerCase() !== 'sin arbitro');

  const topRefereesFouls = realReferees.length
    ? [...realReferees].sort((a, b) => b.avg_fouls_per_match - a.avg_fouls_per_match).slice(0, 5)
    : [];

  const topRefereesCards = realReferees.length
    ? [...realReferees].sort((a, b) => b.avg_cards_per_match - a.avg_cards_per_match).slice(0, 5)
    : [];

  const Wrapper = embedded
    ? ({ children }: { children: ReactNode }) => <div className="space-y-6">{children}</div>
    : ({ children }: { children: ReactNode }) => (
        <div className="min-h-screen bg-slate-950">
          <div className="w-full max-w-[1600px] mx-auto p-6 space-y-6">{children}</div>
        </div>
      );

  return (
    <Wrapper>
        {/* Header — compacto: los datos son el protagonista, no el título */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-3 sm:p-6 shadow-xl">
          <div className="flex items-center gap-1.5 sm:gap-3 mb-1 sm:mb-2">
            <span className="text-base sm:text-4xl shrink-0">{leagueEmoji}</span>
            <h1 className="text-sm sm:text-3xl font-bold text-white truncate">
              {i18n.t('teamStats.analisisEstadistico')}</h1>
          </div>
          <p className="text-slate-300 text-xs sm:text-base">
            {leagueName} · {data.round_label ? data.round_label : i18n.t('teamStats.season', { id: seasonId })}
          </p>
          <p className="text-slate-500 text-[11px] sm:text-sm mt-0.5 sm:mt-1">
            {i18n.t('teamStats.teamsRefs', { teams: data.teams.length, refs: realReferees.length })}
          </p>
          <p className="text-slate-500 text-[10px] sm:text-xs mt-1.5 sm:mt-2 italic">
            {i18n.t('teamStats.losValoresDeCadaModulo')}</p>
        </div>

        {/* 1. OFENSIVA */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.ofensivaGolesAnotados')}</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable(i18n.t('teamStats.mejorOfensivaLocal'), topHomeOffense, 'home_avg_goals_scored', 'text-green-400')}
            {renderRankingTable(i18n.t('teamStats.peorOfensivaLocal'), bottomHomeOffense, 'home_avg_goals_scored', 'text-red-400')}
            {renderRankingTable(i18n.t('teamStats.mejorOfensivaVisitante'), topAwayOffense, 'away_avg_goals_scored', 'text-green-400')}
            {renderRankingTable(i18n.t('teamStats.peorOfensivaVisitante'), bottomAwayOffense, 'away_avg_goals_scored', 'text-red-400')}
          </div>
        </div>

        {/* 2. DEFENSA */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.defensaGolesRecibidos')}</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            {renderRankingTable(i18n.t('teamStats.mejorDefensaLocal'), topHomeDefense, 'home_avg_goals_conceded', 'text-green-400')}
            {renderRankingTable(i18n.t('teamStats.peorDefensaLocal'), bottomHomeDefense, 'home_avg_goals_conceded', 'text-red-400')}
            {renderRankingTable(i18n.t('teamStats.mejorDefensaVisitante'), topAwayDefense, 'away_avg_goals_conceded', 'text-green-400')}
            {renderRankingTable(i18n.t('teamStats.peorDefensaVisitante'), bottomAwayDefense, 'away_avg_goals_conceded', 'text-red-400')}
          </div>
        </div>

        {/* GOLES POR TIEMPO - depende de halftime_homegoal/halftime_awaygoal
            (HTHG/HTAG de football-data.co.uk), que hoy sólo tienen las 4
            ligas europeas - se oculta si la liga actual no trae ese dato. */}
        {data.has_halftime_data && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.golesPorTiempo')}</h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
              {renderRankingTable(i18n.t('teamStats.masGoles1erTiempoLocal'), topHomeGoals1h, 'home_avg_goals_1h', 'text-cyan-400', 'home_matches_ht')}
              {renderRankingTable(i18n.t('teamStats.masGoles1erTiempoVisitante'), topAwayGoals1h, 'away_avg_goals_1h', 'text-cyan-400', 'away_matches_ht')}
              {renderRankingTable(i18n.t('teamStats.masGoles2doTiempoLocal'), topHomeGoals2h, 'home_avg_goals_2h', 'text-pink-400', 'home_matches_ht')}
              {renderRankingTable(i18n.t('teamStats.masGoles2doTiempoVisitante'), topAwayGoals2h, 'away_avg_goals_2h', 'text-pink-400', 'away_matches_ht')}
            </div>
          </div>
        )}

        {/* 3-7. CORNERS / TIROS / TIROS A PUERTA / FALTAS / TARJETAS
            Estas 5 categorías dependen de match_stats, que algunas ligas
            (torneos sudamericanos) no tienen cargado en absoluto - sin esa
            fuente no hay dato real que mostrar, así que se ocultan en vez
            de aparentar un 0.00 real. */}
        {data.has_match_stats && (
          <>
            {/* 2b. CALIDAD DE ATAQUE (AQI) */}
            {attackQuality?.has_match_stats && attackQuality.teams.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.calidadDeAtaque')}</h2>
                <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 sm:p-4 text-xs sm:text-sm text-slate-300 space-y-3">
                  <p>
                    <Trans i18nKey="teamStats.aqiWhat" values={{ n: attackQuality.window }} components={{ b: <span className="text-white font-semibold" /> }} />
                  </p>
                  <ul className="space-y-1.5">
                    <li><Trans i18nKey="teamStats.aqiIndex" components={{ b: <span className="text-white font-semibold" /> }} /></li>
                    <li><Trans i18nKey="teamStats.aqiShots" components={{ b: <span className="text-white font-semibold" /> }} /></li>
                    <li><Trans i18nKey="teamStats.aqiFinish" components={{ b: <span className="text-white font-semibold" /> }} /></li>
                    <li><Trans i18nKey="teamStats.aqiAccuracy" components={{ b: <span className="text-white font-semibold" /> }} /></li>
                    <li><Trans i18nKey="teamStats.aqiPerGame" components={{ b: <span className="text-white font-semibold" /> }} /></li>
                  </ul>
                  {attackQuality.teams[0]?.aqi != null && (
                    <p className="bg-slate-900/60 rounded px-3 py-2">
                      <Trans
                        i18nKey={attackQuality.teams[0].aqi >= 100 ? 'teamStats.aqiExampleMore' : 'teamStats.aqiExampleLess'}
                        values={{
                          team: attackQuality.teams[0].team_name,
                          aqi: attackQuality.teams[0].aqi.toFixed(0),
                          pct: Math.abs(attackQuality.teams[0].aqi - 100).toFixed(0),
                        }}
                        components={{ b: <span className="text-white font-semibold" /> }}
                      />
                    </p>
                  )}
                  <p className="text-slate-500">
                    {i18n.t('teamStats.esUnIndicadorDeTendencia')}</p>
                </div>
                <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 overflow-x-auto">
                  <table className="w-full text-xs sm:text-sm">
                    <thead>
                      <tr className="text-slate-400 text-left border-b border-slate-700">
                        <th className="py-2 pr-2">#</th>
                        <th className="py-2 pr-2">{i18n.t('teamStats.equipo')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.indiceDeCalidadDeAtaque')}>{i18n.t('teamStats.indice')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.rematesAPuertaVsEl')}>{i18n.t('teamStats.rematesAPuerta')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.queTanBienConvierteSus')}>{i18n.t('teamStats.finalizacion')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.deCada100RematesCuantos')}>{i18n.t('teamStats.precision')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.tirosAPuertaPorPartido')}>{i18n.t('teamStats.aPuertaP')}</th>
                        <th className="py-2 pr-2 text-right" title={i18n.t('teamStats.golesPorPartido')}>{i18n.t('teamStats.golesP')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attackQuality.teams.map((t, idx) => (
                        <tr key={t.team_id} className="border-b border-slate-700/50 last:border-0">
                          <td className="py-1.5 pr-2 text-slate-400">{t.aqi === null ? '–' : idx + 1}</td>
                          <td className="py-1.5 pr-2 text-white font-medium whitespace-nowrap">{t.team_name}</td>
                          {t.aqi === null ? (
                            <td colSpan={6} className="py-1.5 text-right text-slate-500">
                              {i18n.t('teamStats.fewMatches', { n: t.matches_used })}
                            </td>
                          ) : (
                            <>
                              <td className={`py-1.5 pr-2 text-right font-bold ${t.aqi >= 110 ? 'text-green-400' : t.aqi <= 90 ? 'text-red-400' : 'text-slate-200'}`}>
                                {t.aqi.toFixed(0)}
                              </td>
                              <td className="py-1.5 pr-2 text-right text-slate-300">{t.volume_idx?.toFixed(0)}</td>
                              <td className="py-1.5 pr-2 text-right text-slate-300">{t.finishing_idx?.toFixed(0)}</td>
                              <td className="py-1.5 pr-2 text-right text-slate-300">{t.precision_pct != null ? `${t.precision_pct.toFixed(0)}%` : '–'}</td>
                              <td className="py-1.5 pr-2 text-right text-slate-300">{t.avg_shots_on_target?.toFixed(1)}</td>
                              <td className="py-1.5 pr-2 text-right text-slate-300">{t.avg_goals?.toFixed(1)}</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 3. CORNERS */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.corners')}</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                {renderRankingTable(i18n.t('teamStats.masCornersLocal'), topHomeCorners, 'home_avg_corners', 'text-yellow-400')}
                {renderRankingTable(i18n.t('teamStats.menosCornersLocal'), bottomHomeCorners, 'home_avg_corners', 'text-slate-400')}
                {renderRankingTable(i18n.t('teamStats.masCornersVisitante'), topAwayCorners, 'away_avg_corners', 'text-yellow-400')}
                {renderRankingTable(i18n.t('teamStats.menosCornersVisitante'), bottomAwayCorners, 'away_avg_corners', 'text-slate-400')}
              </div>
            </div>

            {/* 4. TIROS */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.tiros')}</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                {renderRankingTable(i18n.t('teamStats.masTirosLocal'), topHomeShots, 'home_avg_shots', 'text-blue-400')}
                {renderRankingTable(i18n.t('teamStats.menosTirosLocal'), bottomHomeShots, 'home_avg_shots', 'text-slate-400')}
                {renderRankingTable(i18n.t('teamStats.masTirosVisitante'), topAwayShots, 'away_avg_shots', 'text-blue-400')}
                {renderRankingTable(i18n.t('teamStats.menosTirosVisitante'), bottomAwayShots, 'away_avg_shots', 'text-slate-400')}
              </div>
            </div>

            {/* 5. TIROS A PUERTA */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.tirosAPuerta')}</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                {renderRankingTable(i18n.t('teamStats.masTirosAPuertaLocal'), topHomeShotsTarget, 'home_avg_shots_target', 'text-purple-400')}
                {renderRankingTable(i18n.t('teamStats.menosTirosAPuertaLocal'), bottomHomeShotsTarget, 'home_avg_shots_target', 'text-slate-400')}
                {renderRankingTable(i18n.t('teamStats.masTirosAPuertaVisitante'), topAwayShotsTarget, 'away_avg_shots_target', 'text-purple-400')}
                {renderRankingTable(i18n.t('teamStats.menosTirosAPuertaVisitante'), bottomAwayShotsTarget, 'away_avg_shots_target', 'text-slate-400')}
              </div>
            </div>

            {/* 6. FALTAS */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.faltas')}</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                {renderRankingTable(i18n.t('teamStats.masFaltasLocal'), topHomeFouls, 'home_avg_fouls', 'text-orange-400')}
                {renderRankingTable(i18n.t('teamStats.menosFaltasLocal'), bottomHomeFouls, 'home_avg_fouls', 'text-slate-400')}
                {renderRankingTable(i18n.t('teamStats.masFaltasVisitante'), topAwayFouls, 'away_avg_fouls', 'text-orange-400')}
                {renderRankingTable(i18n.t('teamStats.menosFaltasVisitante'), bottomAwayFouls, 'away_avg_fouls', 'text-slate-400')}
              </div>
            </div>

            {/* 7. TARJETAS */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.tarjetas')}</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                {renderRankingTable(i18n.t('teamStats.masTarjetasLocal'), topHomeCards, 'home_avg_cards', 'text-yellow-400')}
                {renderRankingTable(i18n.t('teamStats.menosTarjetasLocal'), bottomHomeCards, 'home_avg_cards', 'text-slate-400')}
                {renderRankingTable(i18n.t('teamStats.masTarjetasVisitante'), topAwayCards, 'away_avg_cards', 'text-yellow-400')}
                {renderRankingTable(i18n.t('teamStats.menosTarjetasVisitante'), bottomAwayCards, 'away_avg_cards', 'text-slate-400')}
              </div>
            </div>
          </>
        )}

        {/* 8. ÁRBITROS */}
        {realReferees.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-white">{i18n.t('teamStats.arbitros')}</h2>
            <div className="grid grid-cols-2 gap-2 sm:gap-4">

              {/* Árbitros con más faltas */}
              <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
                <h3 className="text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight text-orange-400">{i18n.t('teamStats.masFaltasPorPartido')}</h3>
                <div className="space-y-1.5 sm:space-y-2">
                  {topRefereesFouls.map((ref, idx) => (
                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0">
                      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                        <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                        <span className="text-white font-medium text-xs sm:text-base truncate">{ref.referee}</span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0">
                        <span className="font-bold text-xs sm:text-base text-orange-400">{ref.avg_fouls_per_match.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Árbitros con más tarjetas */}
              <div className="bg-slate-800 rounded-lg p-2.5 sm:p-4 min-w-0">
                <h3 className="text-xs sm:text-lg font-bold mb-2 sm:mb-3 leading-tight text-yellow-400">{i18n.t('teamStats.masTarjetasPorPartido')}</h3>
                <div className="space-y-1.5 sm:space-y-2">
                  {topRefereesCards.map((ref, idx) => (
                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-0.5 sm:gap-2 bg-slate-700/50 rounded px-2 sm:px-3 py-1.5 sm:py-2 min-w-0">
                      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
                        <span className="text-slate-400 font-bold w-4 sm:w-6 text-xs sm:text-base shrink-0">{idx + 1}</span>
                        <span className="text-white font-medium text-xs sm:text-base truncate">{ref.referee}</span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-2 pl-[22px] sm:pl-0 shrink-0">
                        <span className="font-bold text-xs sm:text-base text-yellow-400">{ref.avg_cards_per_match.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
    </Wrapper>
  );
}