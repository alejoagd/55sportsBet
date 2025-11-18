// App.tsx - Versión Responsive
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import PredictionsDashboard from "./predictionsDashboard";
import MetricsEvolutionChart from "./MetricsEvolutionChart";
import TeamStatistics from './Teamstatistics';
import ImprovedDashboard from './ImprovedDashboard';
import MatchDetail from './MatchDetail';
import BestBetsSection from './BestBetsSection';
import { ResponsiveWrapper, ResponsiveNav, useIsMobile } from './ResponsiveWrapper';
import './mobile-responsive.css';


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
    <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50 shadow-lg">
      <div className={`${isMobile ? 'nav-container' : 'max-w-7xl mx-auto px-4'}`}>
        <div className={`${isMobile ? 'flex flex-col' : 'flex items-center justify-between h-16'}`}>
          {/* Logo / Título */}
          <div className={`flex items-center justify-center space-x-2 ${isMobile ? 'py-3' : ''}`}>
            <span className="text-2xl">⚽</span>
            <h1 className={`${isMobile ? 'text-lg' : 'text-xl'} font-bold text-white`}>
              55sportsBet
            </h1>
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
          </ResponsiveNav>
        </div>
      </div>
    </nav>
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
              <Route path="/predictions" element={<PredictionsDashboard />} />
              <Route path="/best-bets" element={<BestBetsSection />} />
              <Route path="/evolution" element={<MetricsEvolutionChart />} />
              <Route path="/statistics" element={<TeamStatistics />} />
              <Route path="/match/:id" element={<MatchDetail />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ResponsiveWrapper>
  );
}

export default App;