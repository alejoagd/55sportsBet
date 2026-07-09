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

// Componente de Navegación Responsive
function Navigation() {
  const location = useLocation();
  const { isAdmin, showAdminLogin, loginAsAdmin, toggleAdminLogin } = useAdminMode();

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/',            icon: '📊', label: 'Dashboard'    },
    { path: '/best-bets',  icon: '🎯', label: 'Apuestas'     },
    { path: '/evolution',  icon: '📈', label: 'Evolución'     },
    { path: '/statistics', icon: '📋', label: 'Estadísticas'  },
  ];

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

            {/* Separador */}
            <div className="w-px h-5 bg-slate-700 flex-shrink-0 hidden sm:block" />

            {/* Links — scrollan horizontalmente en móvil */}
            <div className="flex-1 overflow-x-auto scrollbar-hide">
              <div className="flex items-center gap-1 min-w-max sm:justify-end">
                {navItems.map(({ path, icon, label }) => (
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
          </div>
        </div>
      </nav>

      <AdminLogin isVisible={showAdminLogin} onLogin={loginAsAdmin} onClose={toggleAdminLogin} />
      <AdminBadge />
    </>
  );
}

// Componente principal de la aplicación
function App() {
  const [showSubscribe, setShowSubscribe] = useState(false);

  return (
    <ResponsiveWrapper>
      <Router>
        <div className="min-h-screen bg-slate-900">
          <Navigation />

          <main>
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
          </main>

          {/* Botón flotante de suscripción */}
          <button
            onClick={() => setShowSubscribe(true)}
            className="fixed bottom-6 right-6 z-40 flex items-center gap-2
                       bg-yellow-400 hover:bg-yellow-300 text-slate-900
                       font-bold text-sm px-4 py-3 rounded-full shadow-lg
                       shadow-yellow-400/30 hover:shadow-yellow-400/50
                       transition-all hover:scale-105 active:scale-95"
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