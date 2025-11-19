// App.tsx - Con Sistema de Permisos Administrativos
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import PredictionsDashboard from "./predictionsDashboard";
import MetricsEvolutionChart from "./MetricsEvolutionChart";
import TeamStatistics from './Teamstatistics';
import ImprovedDashboard from './ImprovedDashboard';
import MatchDetail from './MatchDetail';
import BestBetsSection from './BestBetsSection';
import { ResponsiveWrapper, ResponsiveNav, useIsMobile } from './ResponsiveWrapper';
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
  const isMobile = useIsMobile();
  const { isAdmin, showAdminLogin, loginAsAdmin, toggleAdminLogin } = useAdminMode();
  
  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const navItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/best-bets', icon: '🎯', label: isMobile ? 'Apuestas' : 'Mejores Apuestas' },
    { path: '/evolution', icon: '📈', label: isMobile ? 'Evolución' : 'Evolución' },
    { path: '/statistics', icon: '📋', label: isMobile ? 'Stats' : 'Estadísticas' }
  ];

  return (
    <>
      <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50 shadow-lg">
        <div className={`${isMobile ? 'nav-container' : 'max-w-7xl mx-auto px-4'}`}>
          <div className={`${isMobile ? 'flex flex-col' : 'flex items-center justify-between h-16'}`}>
            {/* Logo / Título */}
            <div className={`flex items-center justify-center space-x-2 ${isMobile ? 'py-3' : ''}`}>
              <span className="text-2xl">⚽</span>
              <h1 className={`${isMobile ? 'text-lg' : 'text-xl'} font-bold text-white`}>
                55sportsBet
              </h1>
              
              {/* 🔐 Botón para activar login admin (solo si no está logueado) */}
              {!isAdmin && (
                <button
                  onClick={toggleAdminLogin}
                  className="text-xs text-slate-500 hover:text-slate-300 ml-2"
                  title="Acceso administrativo"
                >
                  🔐
                </button>
              )}
            </div>

            {/* Links de Navegación */}
            <ResponsiveNav className={isMobile ? 'nav-links' : ''}>
              {navItems.map(({ path, icon, label }) => (
                <Link
                  key={path}
                  to={path}
                  className={`nav-link ${
                    isActive(path) 
                      ? 'bg-blue-600 text-white shadow-lg' 
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                  } ${isMobile ? 'rounded-md' : 'px-6 py-2 rounded-lg font-medium transition-all'}`}
                >
                  <span className="mr-2">{icon}</span>
                  {label}
                </Link>
              ))}
              
              {/* 🔐 Stats 2 - Solo visible para admins */}
              <AdminOnly hideCompletely={true}>
                <Link
                  to="/statistics2"
                  className={`nav-link ${
                    isActive('/statistics2') 
                      ? 'bg-blue-600 text-white shadow-lg' 
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                  } ${isMobile ? 'rounded-md' : 'px-6 py-2 rounded-lg font-medium transition-all'}`}
                >
                  <span className="mr-2">📊</span>
                  Stats 2
                </Link>
              </AdminOnly>
            </ResponsiveNav>
          </div>
        </div>
      </nav>

      {/* 🔐 Modal de login administrativo */}
      <AdminLogin
        isVisible={showAdminLogin}
        onLogin={loginAsAdmin}
        onClose={toggleAdminLogin}
      />

      {/* 🔐 Badge indicador de modo admin */}
      <AdminBadge />
    </>
  );
}

// Componente principal de la aplicación
function App() {
  return (
    <ResponsiveWrapper>
      <Router>
        <div className="min-h-screen bg-slate-900">
          <Navigation />
          
          <main className={`main-container`}>
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
        </div>
      </Router>
    </ResponsiveWrapper>
  );
}

export default App;