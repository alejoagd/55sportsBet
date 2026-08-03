// App.tsx - Con Sistema de Permisos Administrativos
import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import PredictionsDashboard from "./predictionsDashboard";
import MetricsEvolutionChart from "./MetricsEvolutionChart";
import TeamStatistics from './Teamstatistics';
import ImprovedDashboard from './ImprovedDashboard';
import MatchDetail from './MatchDetail';
import BestBetsSection from './BestBetsSection';
import { ResponsiveWrapper } from './ResponsiveWrapper';
import SubscribeModal from './SubscribeModal';
import LeagueSidebar from './LeagueSidebar';
import LeagueMobilePanel from './LeagueMobilePanel';
import { useIsMobile } from './Hooks/useIsMobile';
import './mobile-responsive.css';

// 🔐 Imports del sistema administrativo
//import { useAdminMode } from './hooks/useAdminMode';
import { AdminOnly, AdminBadge } from './AdminButton';
import AdminLogin from './AdminLogin';
import { useAdminMode } from './Hooks/useAdminMode';

// Si usas TypeScript estricto, puedes exportar estos tipos también
export interface AppFilters {
  season_id: number;
  date_from: string;
  date_to: string;
}

const NAV_ITEMS = [
  { path: '/',            icon: '📊', label: 'Dashboard'    },
  { path: '/best-bets',  icon: '🎯', label: 'Apuestas'     },
  { path: '/evolution',  icon: '📈', label: 'Evolución'     },
  { path: '/statistics', icon: '📋', label: 'Estadísticas'  },
];

// Barra superior: logo siempre visible; los links de navegación solo se
// muestran en desktop (en mobile se mueven a la barra inferior fija).
function TopBar({ isMobile }: { isMobile: boolean }) {
  const location = useLocation();
  const { isAdmin, showAdminLogin, loginAsAdmin, toggleAdminLogin } = useAdminMode();

  const isActive = (path: string) => location.pathname === path;

  const linkClass = (path: string) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium
     transition-all whitespace-nowrap flex-shrink-0
     ${isActive(path)
       ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
       : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`;

  return (
    <>
      <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-3 sm:px-4">
          <div className="flex items-center h-12 sm:h-14 gap-2 sm:gap-4">
            {/* Logo — no encoge nunca */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <img src="/55sports2.svg" alt="55sportsBet Logo" className="w-7 h-7 sm:w-8 sm:h-8" />
              <h1 className="text-sm sm:text-xl font-bold text-white whitespace-nowrap">
                55sportsBet
              </h1>
              {!isAdmin && (
                <button
                  onClick={toggleAdminLogin}
                  className="text-slate-600 hover:text-slate-400 text-xs ml-0.5 leading-none"
                  title="Acceso administrativo"
                >🔐</button>
              )}
            </div>

            {/* Links de navegación — solo en desktop, en mobile viven en la barra inferior */}
            {!isMobile && (
              <>
                <div className="w-px h-5 bg-slate-700 flex-shrink-0 hidden sm:block" />
                <div className="flex-1 overflow-x-auto scrollbar-hide">
                  <div className="flex items-center gap-1 min-w-max sm:justify-end">
                    {NAV_ITEMS.map(({ path, icon, label }) => (
                      <Link key={path} to={path} className={linkClass(path)}>
                        <span>{icon}</span>
                        <span>{label}</span>
                      </Link>
                    ))}
                    <AdminOnly hideCompletely={true}>
                      <Link to="/statistics2" className={linkClass('/statistics2')}>
                        <span>📊</span>
                        <span>Stats 2</span>
                      </Link>
                    </AdminOnly>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </nav>

      <AdminLogin isVisible={showAdminLogin} onLogin={loginAsAdmin} onClose={toggleAdminLogin} />
      <AdminBadge />
    </>
  );
}

// Barra inferior fija (solo mobile): mismas secciones que el nav de desktop
// + un botón "Ligas" que abre el panel de selección de liga.
function BottomTabBar({ onOpenLeagues }: { onOpenLeagues: () => void }) {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  const itemClass = (active: boolean) =>
    `flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium
     ${active ? 'text-blue-400' : 'text-slate-400'}`;

  return (
    <nav
      className="fixed bottom-0 inset-x-0 z-50 flex border-t border-slate-700 bg-slate-900"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {NAV_ITEMS.map(({ path, icon, label }) => (
        <Link key={path} to={path} className={itemClass(isActive(path))}>
          <span className="text-lg leading-none">{icon}</span>
          <span>{label}</span>
        </Link>
      ))}
      <button onClick={onOpenLeagues} className={itemClass(false)}>
        <span className="text-lg leading-none">🏆</span>
        <span>Ligas</span>
      </button>
    </nav>
  );
}

// Componente principal de la aplicación
function App() {
  const [showSubscribe, setShowSubscribe] = useState(false);
  const [showLeaguePanel, setShowLeaguePanel] = useState(false);
  const isMobile = useIsMobile();

  const routesElement = (
    <Routes>
      <Route path="/" element={<ImprovedDashboard />} />
      <Route path="/best-bets" element={<BestBetsSection />} />
      <Route path="/evolution" element={<MetricsEvolutionChart />} />
      <Route path="/statistics" element={<TeamStatistics />} />

      {/* 🔐 Ruta protegida - Stats 2 solo para admins */}
      <Route
        path="/statistics2"
        element={
          <AdminOnly
            fallback={
              <div className="flex items-center justify-center h-96 text-slate-400">
                <div className="text-center">
                  <div className="text-6xl mb-4">🔐</div>
                  <div className="text-xl">Acceso Restringido</div>
                  <div className="text-sm mt-2">Esta sección es solo para administradores</div>
                </div>
              </div>
            }
            hideCompletely={false}
          >
            <PredictionsDashboard />
          </AdminOnly>
        }
      />

      <Route path="/match/:matchId" element={<MatchDetail />} />

      {/* Ruta 404 */}
      <Route path="*" element={
        <div className="flex flex-col items-center justify-center h-96 text-slate-400">
          <div className="text-6xl mb-4">404</div>
          <div className="text-xl">Página no encontrada</div>
          <Link to="/" className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Volver al Dashboard
          </Link>
        </div>
      } />
    </Routes>
  );

  return (
    <ResponsiveWrapper>
      <Router>
        <div className={isMobile ? 'h-[100dvh] flex flex-col overflow-hidden bg-slate-900' : 'min-h-screen bg-slate-900'}>
          <TopBar isMobile={isMobile} />

          <div className={isMobile ? 'flex-1 flex overflow-hidden' : 'flex'}>
            {!isMobile && <LeagueSidebar />}
            <main
              className={isMobile ? 'flex-1 overflow-y-auto' : 'flex-1 min-w-0'}
              style={isMobile ? { paddingBottom: 'calc(4.5rem + env(safe-area-inset-bottom))' } : undefined}
            >
              {routesElement}
            </main>
          </div>

          {isMobile && <BottomTabBar onOpenLeagues={() => setShowLeaguePanel(true)} />}
          {isMobile && <LeagueMobilePanel isOpen={showLeaguePanel} onClose={() => setShowLeaguePanel(false)} />}

          {/* Botón flotante de suscripción — sube en mobile para no tapar la barra inferior */}
          <button
            onClick={() => setShowSubscribe(true)}
            className={`fixed right-6 z-40 flex items-center gap-2
                       bg-yellow-400 hover:bg-yellow-300 text-slate-900
                       font-bold text-sm px-4 py-3 rounded-full shadow-lg
                       shadow-yellow-400/30 hover:shadow-yellow-400/50
                       transition-all hover:scale-105 active:scale-95
                       ${isMobile ? 'bottom-20' : 'bottom-6'}`}
            title="Suscríbete para recibir noticias del Mundial"
          >
            <span className="text-base">🔔</span>
            <span className="hidden sm:inline">Suscríbete</span>
          </button>

          <SubscribeModal isOpen={showSubscribe} onClose={() => setShowSubscribe(false)} />
        </div>
      </Router>
    </ResponsiveWrapper>
  );
}

export default App;
