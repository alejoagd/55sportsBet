// src/LeagueMobilePanel.tsx
// Panel de ligas para mobile, abierto desde el botón "Ligas" de la barra
// inferior. Mismo comportamiento que LeagueSidebar: en "/" (única página que
// lee ?league=) actualiza el query param en la ruta actual; en cualquier
// otra (detalle de partido, apuestas, evolución, etc.) navega al dashboard
// con la liga elegida, para que el click siempre tenga efecto.
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import { useActiveLeagues } from './Hooks/useActiveLeagues';

const LEAGUE_AWARE_PATHS = ['/'];

export default function LeagueMobilePanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { leagues, loading } = useActiveLeagues();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const currentLeagueId = searchParams.get('league');

  if (!isOpen) return null;

  const selectLeague = (id: number) => {
    if (!LEAGUE_AWARE_PATHS.includes(location.pathname)) {
      navigate(`/?league=${id}`);
      onClose();
      return;
    }
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set('league', String(id));
      next.delete('group');
      return next;
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-slate-950">
      <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
        <h2 className="text-base font-bold text-white">Ligas</h2>
        <button onClick={onClose} className="rounded-full p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        {loading ? (
          <div className="px-2 py-3 text-sm text-slate-400">Cargando ligas...</div>
        ) : (
          leagues.map((league) => {
            const isActive = String(league.id) === currentLeagueId;
            return (
              <button
                key={league.id}
                onClick={() => selectLeague(league.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors
                  ${isActive ? 'bg-blue-600/20 text-white' : 'text-slate-300 active:bg-slate-800'}`}
              >
                <span className="text-xl">{league.emoji}</span>
                <span className="flex-1 text-sm font-medium">{league.name}</span>
                {league.upcomingCount > 0 && (
                  <span className={`rounded-full px-2 py-0.5 text-xs
                    ${isActive ? 'bg-blue-500/30 text-blue-200' : 'bg-slate-700 text-slate-400'}`}>
                    {league.upcomingCount}
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
