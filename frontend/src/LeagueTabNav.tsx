import { useNavigate, useSearchParams } from 'react-router-dom';

// Menú de pestañas por liga, mismo patrón visual que TabNav de
// WorldCupDashboard.tsx, generalizado para cualquier liga/copa. "Bracket"
// solo aplica a competencias de eliminatoria (Libertadores/Sudamericana) —
// una liga regular no tiene bracket. "Estadísticas" no es una pestaña de
// contenido: navega a la página de Estadísticas ya existente.

export type LeagueTab = 'today' | 'matches' | 'standings' | 'bracket' | 'news';

const TAB_META: Record<LeagueTab, { label: string; icon: string }> = {
  today: { label: 'Hoy', icon: '📅' },
  matches: { label: 'Partidos', icon: '⚽' },
  standings: { label: 'Posiciones', icon: '📊' },
  bracket: { label: 'Bracket', icon: '🗺️' },
  news: { label: 'Noticias', icon: '📰' },
};

const VALID_TABS: LeagueTab[] = ['today', 'matches', 'standings', 'bracket', 'news'];

export function useLeagueTab(defaultTab: LeagueTab = 'matches'): [LeagueTab, (t: LeagueTab) => void] {
  const [searchParams, setSearchParams] = useSearchParams();
  const raw = searchParams.get('tab');
  const tab: LeagueTab = raw && (VALID_TABS as string[]).includes(raw) ? (raw as LeagueTab) : defaultTab;

  const setTab = (t: LeagueTab) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', t);
      return next;
    });
  };

  return [tab, setTab];
}

export default function LeagueTabNav({
  active,
  onChange,
  leagueId,
  showBracket,
}: {
  active: LeagueTab;
  onChange: (t: LeagueTab) => void;
  leagueId: number;
  showBracket: boolean;
}) {
  const navigate = useNavigate();
  const tabs: LeagueTab[] = showBracket
    ? ['today', 'matches', 'standings', 'bracket', 'news']
    : ['today', 'matches', 'standings', 'news'];

  const buttonClass = (isActive: boolean) =>
    `flex-shrink-0 flex items-center justify-center gap-1 sm:gap-1.5
     py-2 px-2.5 sm:py-2.5 sm:px-4 rounded-lg
     text-xs sm:text-sm font-semibold transition-all whitespace-nowrap
     ${isActive
       ? 'bg-yellow-400 text-slate-900 shadow-md shadow-yellow-400/20'
       : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
     }`;

  return (
    <div className="bg-slate-800/60 p-1 rounded-xl mb-4 sm:mb-6 border border-slate-700/50 overflow-x-auto scrollbar-hide">
      <div className="flex gap-0.5 sm:gap-1 min-w-max">
        {tabs.map((t) => (
          <button key={t} onClick={() => onChange(t)} className={buttonClass(active === t)}>
            <span>{TAB_META[t].icon}</span>
            <span>{TAB_META[t].label}</span>
          </button>
        ))}
        <button
          onClick={() => navigate(`/statistics?league=${leagueId}`)}
          className={buttonClass(false)}
        >
          <span>🏅</span>
          <span>Estadísticas</span>
        </button>
      </div>
    </div>
  );
}
