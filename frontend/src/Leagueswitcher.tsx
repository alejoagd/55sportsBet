import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

interface League {
  id: number;
  name: string;
  emoji: string;
  seasonId: number;
  upcomingCount: number;
}

interface LeagueSwitcherProps {
  currentLeagueId: number;
  onLeagueChange: (leagueId: number) => void;
  className?: string;
}

const LeagueSwitcher: React.FC<LeagueSwitcherProps> = ({ 
  currentLeagueId, 
  onLeagueChange,
  className = ''
}) => {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/leagues/active');
        const data = await response.json();
        setLeagues(data);
      } catch (error) {
        console.error('Error cargando ligas:', error);
        // ACTUALIZADO: Fallback con las 4 ligas
        setLeagues([
          { id: 1, name: 'Premier League', emoji: '🏴', seasonId: 7, upcomingCount: 10 },
          { id: 2, name: 'La Liga', emoji: '🇪🇸', seasonId: 2, upcomingCount: 9 },
          { id: 3, name: 'Serie A', emoji: '🇮🇹', seasonId: 15, upcomingCount: 10 },
          { id: 4, name: 'Bundesliga', emoji: '🇩🇪', seasonId: 20, upcomingCount: 8 },
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchLeagues();
  }, []);

  const currentLeague = leagues.find(l => l.id === currentLeagueId);

  if (!isMobile) {
    return (
      <div className={`bg-slate-900 border-b border-slate-700 ${className}`}>
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
            {loading ? (
              <div className="py-4 text-slate-400 text-sm">Cargando ligas...</div>
            ) : (
              leagues.map((league) => {
                const isActive = league.id === currentLeagueId;
                return (
                  <button
                    key={league.id}
                    onClick={() => onLeagueChange(league.id)}
                    className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap border-b-2 transition-all duration-200
                      ${isActive 
                        ? 'border-blue-500 text-white font-semibold bg-slate-800/50' 
                        : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
                      }`}
                  >
                    <span className="text-xl">{league.emoji}</span>
                    <span className="text-sm">{league.name}</span>
                    {league.upcomingCount > 0 && (
                      <span className={`text-xs px-2 py-0.5 rounded-full
                        ${isActive ? 'bg-blue-500/20 text-blue-300' : 'bg-slate-700 text-slate-400'}`}>
                        {league.upcomingCount}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative px-4 py-3 bg-slate-900 border-b border-slate-700 ${className}`}>
      <button onClick={() => setIsDropdownOpen(!isDropdownOpen)} disabled={loading}
        className="w-full flex items-center justify-between bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 transition-all duration-200 disabled:opacity-50">
        {loading ? <span className="text-slate-400 text-sm">Cargando...</span> : (
          <>
            <div className="flex items-center gap-3">
              <span className="text-2xl">{currentLeague?.emoji}</span>
              <div className="text-left">
                <div className="text-white font-semibold text-sm">{currentLeague?.name}</div>
                <div className="text-slate-400 text-xs">{currentLeague?.upcomingCount} próximos</div>
              </div>
            </div>
            <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </>
        )}
      </button>

      {isDropdownOpen && !loading && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setIsDropdownOpen(false)} />
          <div className="absolute left-4 right-4 mt-2 bg-slate-800 border border-slate-700 rounded-lg shadow-2xl z-50">
            {leagues.map((league, index) => {
              const isActive = league.id === currentLeagueId;
              return (
                <button key={league.id}
                  onClick={() => { onLeagueChange(league.id); setIsDropdownOpen(false); }}
                  className={`w-full flex items-center justify-between px-4 py-3 transition-all duration-200
                    ${index !== leagues.length - 1 ? 'border-b border-slate-700' : ''}
                    ${isActive ? 'bg-blue-500/10 text-white' : 'text-slate-300 hover:bg-slate-700/50'}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{league.emoji}</span>
                    <div className="text-left">
                      <div className="font-medium text-sm">{league.name}</div>
                      <div className="text-xs text-slate-400">{league.upcomingCount} partidos</div>
                    </div>
                  </div>
                  {isActive && <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default LeagueSwitcher;