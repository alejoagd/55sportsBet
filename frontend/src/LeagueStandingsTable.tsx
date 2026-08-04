import { useEffect, useState } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Tabla de posiciones de la fase actual de la temporada (el backend ya
// resuelve cuál es "la actual" cuando la liga divide el año en Apertura/
// Clausura). Algunas ligas (Liga Argentina, Liga Betplay) además dividen
// esa fase en zonas/grupos reales — el backend devuelve `groups` en ese
// caso en vez de `standings`, y acá se renderiza una tabla por grupo.

interface Standing {
  team_id: number;
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
}

interface Group {
  group_name: string;
  standings: Standing[];
}

function Table({ standings, title }: { standings: Standing[]; title?: string }) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {title && (
        <div className="bg-slate-700/50 px-4 py-2 font-bold text-white">{title}</div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs">
              <th className="text-left px-3 py-2">#</th>
              <th className="text-left px-3 py-2">Equipo</th>
              <th className="px-2 py-2">PJ</th>
              <th className="px-2 py-2">G</th>
              <th className="px-2 py-2">E</th>
              <th className="px-2 py-2">P</th>
              <th className="px-2 py-2">GF</th>
              <th className="px-2 py-2">GC</th>
              <th className="px-2 py-2">DG</th>
              <th className="px-2 py-2 font-bold">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((t, i) => (
              <tr key={t.team_id} className={`border-t border-slate-700 ${i < 4 ? 'text-white' : 'text-slate-400'}`}>
                <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                <td className="px-3 py-2 whitespace-nowrap">{t.team}</td>
                <td className="text-center px-2 py-2">{t.played}</td>
                <td className="text-center px-2 py-2">{t.won}</td>
                <td className="text-center px-2 py-2">{t.drawn}</td>
                <td className="text-center px-2 py-2">{t.lost}</td>
                <td className="text-center px-2 py-2">{t.goals_for}</td>
                <td className="text-center px-2 py-2">{t.goals_against}</td>
                <td className="text-center px-2 py-2">{t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}</td>
                <td className="text-center px-2 py-2 font-bold">{t.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function LeagueStandingsTable({ seasonId }: { seasonId: number }) {
  const [standings, setStandings] = useState<Standing[] | null>(null);
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!seasonId) return;
    setLoading(true);
    setError(null);
    setStandings(null);
    setGroups(null);
    fetch(`${API_URL}/api/competitions/${seasonId}/standings`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => {
        if (data.groups) setGroups(data.groups);
        else setStandings(data.standings || []);
      })
      .catch(() => setError('No se pudo cargar la tabla de posiciones'))
      .finally(() => setLoading(false));
  }, [seasonId]);

  if (loading) {
    return <div className="text-center py-16 text-slate-400">Cargando posiciones...</div>;
  }
  if (error) {
    return <div className="text-center py-16 text-red-400">{error}</div>;
  }
  if ((!groups || groups.length === 0) && (!standings || standings.length === 0)) {
    return <div className="text-center py-16 text-slate-500">Todavía no hay partidos jugados esta temporada</div>;
  }

  if (groups) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {groups.map((g) => (
          <Table key={g.group_name} standings={g.standings} title={`Grupo ${g.group_name.replace(/^Group\s*/i, '')}`} />
        ))}
      </div>
    );
  }

  return <Table standings={standings!} />;
}
