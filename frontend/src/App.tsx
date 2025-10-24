// frontend/src/App.tsx
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import PredictionsDashboard from "./predictionsDashboard";
import MetricsEvolutionChart from "./MetricsEvolutionChart";
import TeamStatistics from './Teamstatistics';
import ImprovedDashboard from './ImprovedDashboard';
import MatchDetail from './MatchDetail';


// Si usas TypeScript estricto, puedes exportar estos tipos también
export interface AppFilters {
  season_id: number;
  date_from: string;
  date_to: string;
}

// Componente de Navegación
function Navigation() {
  const location = useLocation();
  
  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo / Título */}
          <div className="flex items-center space-x-2">
            <span className="text-2xl">⚽</span>
            <h1 className="text-xl font-bold text-white">55sportsBet</h1>
          </div>

          {/* Links de Navegación */}
          <div className="flex gap-2">
            <Link
              to="/"
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                isActive('/') 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
              }`}
            >
              📊 Dashboard
            </Link>
            <Link
              to="/evolution"
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                isActive('/evolution') 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
              }`}
            >
              📈 Evolución
            </Link>
            <Link 
              to="/statistics">
              <button className="px-4 py-2 bg-slate-700 text-white rounded-lg">
              📊 Estadísticas
              </button>
            </Link>
            <Link 
              to="/statistics2">
              <button className="px-4 py-2 bg-slate-700 text-white rounded-lg">
              📊 Estadísticas 2
              </button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

// Componente Principal
export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950">
        {/* Navegación */}
        <Navigation />
        
        {/* Contenido - Rutas */}
        <Routes>
          <Route path="/" element={<ImprovedDashboard />} />
          <Route path="/evolution" element={<MetricsEvolutionChart />} />
          <Route path="/statistics" element={<TeamStatistics />} />
          <Route path="/statistics2" element={<PredictionsDashboard />} />
          <Route path="/" element={<ImprovedDashboard />} />
          <Route path="/match/:matchId" element={<MatchDetail />} />

          
          {/* Ruta 404 - Opcional */}
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
      </div>
    </Router>
  );
}