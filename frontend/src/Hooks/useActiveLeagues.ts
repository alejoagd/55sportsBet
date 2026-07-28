// src/hooks/useActiveLeagues.ts
import { useState, useEffect } from 'react';

export interface League {
  id: number;
  name: string;
  emoji: string;
  seasonId: number;
  upcomingCount: number;
}

const FALLBACK_LEAGUES: League[] = [
  { id: 1, name: 'Premier League', emoji: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', seasonId: 7, upcomingCount: 10 },
  { id: 2, name: 'La Liga', emoji: '🇪🇸', seasonId: 2, upcomingCount: 9 },
  { id: 3, name: 'Serie A', emoji: '🇮🇹', seasonId: 15, upcomingCount: 10 },
  { id: 4, name: 'Bundesliga', emoji: '🇩🇪', seasonId: 20, upcomingCount: 8 },
];

export function useActiveLeagues() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/leagues/active`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: League[]) => setLeagues(data))
      .catch(() => {
        console.error('Error cargando ligas activas, usando fallback');
        setLeagues(FALLBACK_LEAGUES);
      })
      .finally(() => setLoading(false));
  }, []);

  return { leagues, loading };
}
