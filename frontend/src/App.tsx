// App.tsx - Con Sistema de Permisos Administrativos
import { Fragment, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import LanguageSwitcher from './LanguageSwitcher';
import MetricsEvolutionChart from "./MetricsEvolutionChart";
import ImprovedDashboard from './ImprovedDashboard';
import MatchDetail from './MatchDetail';
import BestBetsSection from './BestBetsSection';
import { ResponsiveWrapper } from './ResponsiveWrapper';
import SubscribeModal from './SubscribeModal';
import PrivacyPolicy from './PrivacyPolicy';
import LegalFooter from './LegalFooter';
import LeagueSidebar from './LeagueSidebar';
import LeagueMobilePanel from './LeagueMobilePanel';
import { useIsMobile } from './Hooks/useIsMobile';
import './mobile-responsive.css';

// 🔐 Imports del sistema administrativo
//import { useAdminMode } from './hooks/useAdminMode';
import { AdminBadge } from './AdminButton';
import AdminLogin from './AdminLogin';
import { useAdminMode } from './Hooks/useAdminMode';

// Si usas TypeScript estricto, puedes exportar estos tipos también
export interface AppFilters {
  season_id: number;
  date_from: string;
  date_to: string;
}

// "Estadísticas" no vive acá: cada liga ya tiene su propio tab de
// Estadísticas (LeagueTabNav) con los datos de esa liga específica. Este
// nav genérico apuntaba siempre a /statistics, que muestra las del Mundial
// sin importar qué liga estuviera seleccionada — confuso, así que se sacó.
const NAV_ITEMS = [
  { path: '/',            icon: '📊', labelKey: 'nav.home'      },
  { path: '/best-bets',  icon: '🎯', labelKey: 'nav.bets'      },
  { path: '/evolution',  icon: '📈', labelKey: 'nav.evolution' },
];

// Barra superior: logo siempre visible; los links de navegación solo se
// muestran en desktop (en mobile se mueven a la barra inferior fija).
function TopBar({ isMobile, onSubscribe }: { isMobile: boolean; onSubscribe: () => void }) {
  const { t } = useTranslation();
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
              <img src="/55sports2.svg" alt="55sports Stats Logo" className="w-7 h-7 sm:w-8 sm:h-8" />
              <h1 className="text-sm sm:text-xl font-bold text-white whitespace-nowrap">
                55sports Stats
              </h1>
              {!isAdmin && (
                <button
                  onClick={toggleAdminLogin}
                  className="text-slate-600 hover:text-slate-400 text-xs ml-0.5 leading-none"
                  title={t('nav.adminAccess')}
                >🔐</button>
              )}
            </div>

            {/* Links de navegación — solo en desktop, en mobile viven en la barra inferior */}
            {!isMobile && (
              <>
                <div className="w-px h-5 bg-slate-700 flex-shrink-0 hidden sm:block" />
                <div className="flex-1 overflow-x-auto scrollbar-hide">
                  <div className="flex items-center gap-1 min-w-max sm:justify-end">
                    {NAV_ITEMS.map(({ path, icon, labelKey }) => (
                      <Link key={path} to={path} className={linkClass(path)}>
                        <span>{icon}</span>
                        <span>{t(labelKey)}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Badge de admin dentro del header (no fixed) para que no flote sobre el contenido */}
            <div className="ml-auto flex items-center gap-2 flex-shrink-0">
              <AdminBadge />
              <LanguageSwitcher />
              {/* En mobile la suscripción vive acá en vez de en un botón flotante que tapa contenido */}
              {isMobile && (
                <button
                  onClick={onSubscribe}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-yellow-400 hover:bg-yellow-300 text-slate-900 text-sm"
                  title={t('nav.subscribeTooltip')}
                  aria-label={t('nav.subscribe')}
                >🔔</button>
              )}
            </div>
          </div>
        </div>
      </nav>

      <AdminLogin isVisible={showAdminLogin} onLogin={loginAsAdmin} onClose={toggleAdminLogin} />
    </>
  );
}

// Barra inferior fija (solo mobile): mismas secciones que el nav de desktop
// + un botón "Ligas" que abre el panel de selección de liga.
function BottomTabBar({ onOpenLeagues }: { onOpenLeagues: () => void }) {
  const { t } = useTranslation();
  const location = useLocation();
  // Viendo una liga (/?league=X) se marca "Ligas" en vez de "Inicio", que
  // queda solo para "Partidos de hoy" (/ sin liga).
  const isLeagueView =
    location.pathname === '/' && new URLSearchParams(location.search).has('league');
  const isActive = (path: string) =>
    location.pathname === path && !(path === '/' && isLeagueView);

  const itemClass = (active: boolean) =>
    `flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium
     ${active ? 'text-blue-400' : 'text-slate-400'}`;

  return (
    <nav
      className="fixed bottom-0 inset-x-0 z-50 flex border-t border-slate-700 bg-slate-900"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {NAV_ITEMS.map(({ path, icon, labelKey }) => (
        <Link key={path} to={path} className={itemClass(isActive(path))}>
          <span className="text-lg leading-none">{icon}</span>
          <span>{t(labelKey)}</span>
        </Link>
      ))}
      <button onClick={onOpenLeagues} className={itemClass(isLeagueView)}>
        <span className="text-lg leading-none">🏆</span>
        <span>{t('nav.leagues')}</span>
      </button>
    </nav>
  );
}

// Al cambiar de liga (?league=) la lista debe partir desde arriba, en
// cualquier tab. En mobile el scroll vive en <main> (overflow-y-auto) y en
// desktop en la ventana; el contenido se reemplaza sin remontar el
// contenedor, así que el scroll anterior se heredaba (ej. quedaba abajo,
// en el aviso legal, de la liga previa).
// Solo cuenta un cambio de liga estando ya en "/": volver a "/" desde el
// detalle de un partido no debe resetear la posición de la lista.
function ScrollToTopOnLeagueChange({ scrollRef }: { scrollRef: React.RefObject<HTMLElement | null> }) {
  const { pathname, search } = useLocation();
  const league = new URLSearchParams(search).get('league');
  const prev = useRef({ pathname, league });

  useEffect(() => {
    const before = prev.current;
    prev.current = { pathname, league };
    if (before.pathname === '/' && pathname === '/' && before.league !== league) {
      scrollRef.current?.scrollTo({ top: 0 });
      window.scrollTo({ top: 0 });
    }
  }, [pathname, league, scrollRef]);

  return null;
}

// Componente principal de la aplicación
function App() {
  const { t, i18n } = useTranslation();
  const [showSubscribe, setShowSubscribe] = useState(false);
  const [showLeaguePanel, setShowLeaguePanel] = useState(false);
  const isMobile = useIsMobile();
  const mainRef = useRef<HTMLElement>(null);

  const routesElement = (
    <Routes>
      <Route path="/" element={<ImprovedDashboard />} />
      <Route path="/best-bets" element={<BestBetsSection />} />
      <Route path="/evolution" element={<MetricsEvolutionChart />} />

      <Route path="/match/:matchId" element={<MatchDetail />} />
      {/* /privacidad es la URL registrada en Play Console; /privacy es el alias en inglés */}
      <Route path="/privacidad" element={<PrivacyPolicy />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />

      {/* Ruta 404 */}
      <Route path="*" element={
        <div className="flex flex-col items-center justify-center h-96 text-slate-400">
          <div className="text-6xl mb-4">404</div>
          <div className="text-xl">{t('nav.notFound')}</div>
          <Link to="/" className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {t('nav.backToDashboard')}
          </Link>
        </div>
      } />
    </Routes>
  );

  return (
    <ResponsiveWrapper>
      <Router>
        <div className={isMobile ? 'h-[100dvh] flex flex-col overflow-hidden bg-slate-900' : 'min-h-screen bg-slate-900'}>
          <TopBar isMobile={isMobile} onSubscribe={() => setShowSubscribe(true)} />

          <div className={isMobile ? 'flex-1 flex overflow-hidden' : 'flex'}>
            {!isMobile && <LeagueSidebar />}
            <ScrollToTopOnLeagueChange scrollRef={mainRef} />
            <main
              ref={mainRef}
              className={isMobile ? 'flex-1 overflow-y-auto' : 'flex-1 min-w-0 pb-24'}
              style={isMobile ? { paddingBottom: 'calc(4.5rem + env(safe-area-inset-bottom))' } : undefined}
            >
              {/* key: al cambiar de idioma se remonta el contenido, así los textos que se
                  calculan al renderizar se recalculan todos (el estado de datos se recarga). */}
              <Fragment key={i18n.language}>
                {routesElement}
                <LegalFooter />
              </Fragment>
            </main>
          </div>

          {isMobile && <BottomTabBar onOpenLeagues={() => setShowLeaguePanel(true)} />}
          {isMobile && <LeagueMobilePanel isOpen={showLeaguePanel} onClose={() => setShowLeaguePanel(false)} />}

          {/* Botón flotante de suscripción — solo desktop; en mobile está en el TopBar */}
          {!isMobile && (
            <button
              onClick={() => setShowSubscribe(true)}
              className="fixed right-6 bottom-6 z-40 flex items-center gap-2
                         bg-yellow-400 hover:bg-yellow-300 text-slate-900
                         font-bold text-sm px-4 py-3 rounded-full shadow-lg
                         shadow-yellow-400/30 hover:shadow-yellow-400/50
                         transition-all hover:scale-105 active:scale-95"
              title={t('nav.subscribeTooltip')}
            >
              <span className="text-base">🔔</span>
              <span>{t('nav.subscribe')}</span>
            </button>
          )}

          <SubscribeModal isOpen={showSubscribe} onClose={() => setShowSubscribe(false)} />
        </div>
      </Router>
    </ResponsiveWrapper>
  );
}

export default App;
