// src/LeagueSidebar.tsx
// Sidebar de ligas para desktop/tablet. En "/" (única página que lee
// ?league=) solo actualiza el query param sobre la URL actual, sin forzar
// navegación, para no perder el resto del estado de esa vista. En cualquier
// otra ruta (detalle de partido, apuestas, evolución, etc. — que no leen
// ?league= y por eso el click no tenía ningún efecto visible) navega al
// dashboard con la liga elegida.
//
// Colapsable: en pantallas angostas (tablet) el sidebar fijo de 256px no
// dejaba espacio para la tabla de partidos, que quedaba recortada sin poder
// scrollear (overflow-hidden sin scroll horizontal — ver CompactMatchList).
// Colapsado a una franja de solo íconos, el usuario recupera ese espacio
// cuando lo necesita sin perder el acceso a las ligas. Arranca colapsado en
// pantallas angostas y expandido en desktop grande; el usuario puede
// invertirlo con el botón, y esa elección se recuerda.
import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useActiveLeagues } from './Hooks/useActiveLeagues';

const LEAGUE_AWARE_PATHS = ['/'];
const STORAGE_KEY = 'leagueSidebarCollapsed';
const AUTO_COLLAPSE_WIDTH = 1024;

function getInitialCollapsed(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored !== null) return stored === '1';
  return window.innerWidth < AUTO_COLLAPSE_WIDTH;
}

export default function LeagueSidebar() {
  const { leagues, loading } = useActiveLeagues();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const currentLeagueId = searchParams.get('league');
  const [collapsed, setCollapsed] = useState(getInitialCollapsed);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
  }, [collapsed]);

  const selectLeague = (id: number) => {
    if (!LEAGUE_AWARE_PATHS.includes(location.pathname)) {
      navigate(`/?league=${id}`);
      return;
    }
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set('league', String(id));
      next.delete('group');
      return next;
    });
  };

  return (
    <aside className={`${collapsed ? 'w-14' : 'w-64'} shrink-0 border-r border-slate-700 bg-slate-900 transition-[width] duration-200`}>
      <div className="sticky top-14 max-h-[calc(100vh-3.5rem)] overflow-y-auto overflow-x-hidden py-3">
        <div className={`flex items-center pb-2 ${collapsed ? 'justify-center px-1' : 'justify-between px-4'}`}>
          {!collapsed && (
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Ligas</span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center w-6 h-6 rounded text-slate-500 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
            aria-label={collapsed ? 'Expandir menú de ligas' : 'Contraer menú de ligas'}
            title={collapsed ? 'Expandir' : 'Contraer'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
        {loading ? (
          !collapsed && <div className="px-4 py-3 text-sm text-slate-400">Cargando ligas...</div>
        ) : (
          <nav className={`space-y-0.5 ${collapsed ? 'px-1.5' : 'px-2'}`}>
            {leagues.map((league) => {
              const isActive = String(league.id) === currentLeagueId;
              return (
                <button
                  key={league.id}
                  onClick={() => selectLeague(league.id)}
                  title={collapsed ? league.name : undefined}
                  className={`flex w-full items-center rounded-lg text-left transition-colors
                    ${collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5'}
                    ${isActive
                      ? 'bg-blue-600/20 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                >
                  <span className="text-lg shrink-0">{league.emoji}</span>
                  {!collapsed && (
                    <>
                      <span className="flex-1 truncate text-sm font-medium">{league.name}</span>
                      {league.upcomingCount > 0 && (
                        <span className={`rounded-full px-1.5 py-0.5 text-[11px]
                          ${isActive ? 'bg-blue-500/30 text-blue-200' : 'bg-slate-700 text-slate-400'}`}>
                          {league.upcomingCount}
                        </span>
                      )}
                    </>
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
