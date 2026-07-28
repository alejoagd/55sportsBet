// src/LeagueSidebar.tsx
// Sidebar de ligas para desktop. No es dueño de la selección: al hacer click
// solo actualiza ?league= en la URL actual (via useSearchParams, que preserva
// el pathname), así funciona igual en "/" y en "/statistics" sin forzar
// navegación a otra ruta.
import { useSearchParams } from 'react-router-dom';
import { useActiveLeagues } from './Hooks/useActiveLeagues';

export default function LeagueSidebar() {
  const { leagues, loading } = useActiveLeagues();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentLeagueId = searchParams.get('league');

  const selectLeague = (id: number) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set('league', String(id));
      next.delete('group');
      return next;
    });
  };

  return (
    <aside className="w-64 shrink-0 border-r border-slate-700 bg-slate-900">
      <div className="sticky top-14 max-h-[calc(100vh-3.5rem)] overflow-y-auto py-3">
        <div className="px-4 pb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
          Ligas
        </div>
        {loading ? (
          <div className="px-4 py-3 text-sm text-slate-400">Cargando ligas...</div>
        ) : (
          <nav className="space-y-0.5 px-2">
            {leagues.map((league) => {
              const isActive = String(league.id) === currentLeagueId;
              return (
                <button
                  key={league.id}
                  onClick={() => selectLeague(league.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors
                    ${isActive
                      ? 'bg-blue-600/20 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                >
                  <span className="text-lg">{league.emoji}</span>
                  <span className="flex-1 truncate text-sm font-medium">{league.name}</span>
                  {league.upcomingCount > 0 && (
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px]
                      ${isActive ? 'bg-blue-500/30 text-blue-200' : 'bg-slate-700 text-slate-400'}`}>
                      {league.upcomingCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        )}
      </div>
    </aside>
  );
}
