import { useState, useEffect } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Tablas de grupo + bracket de eliminatoria, 100% dirigido por los datos que
// devuelve el backend (stage/round_label/group_name en `matches`) — a
// diferencia de WorldCupDashboard.tsx, acá no hay diccionarios hardcodeados
// de equipo/grupo/bracket: cualquier competencia con esa forma de datos
// (Copa Libertadores, Copa Sudamericana, futuras) se renderiza igual.

interface GroupMatch {
  match_id: number;
  group_name: string;
  date: string;
  home_team: string;
  home_goals: number | null;
  away_team: string;
  away_goals: number | null;
}

interface GroupStanding {
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
  standings: GroupStanding[];
  matches: GroupMatch[];
}

interface BracketMatch {
  match_id: number;
  stage: string;
  round_label: string | null;
  date: string;
  home_team: string;
  home_goals: number | null;
  away_team: string;
  away_goals: number | null;
}

const STAGE_LABEL: Record<string, string> = {
  preliminary: 'Rondas previas',
  round_of_32: 'Dieciseisavos',
  round_of_16: 'Octavos de final',
  quarterfinal: 'Cuartos de final',
  semifinal: 'Semifinal',
  third_place: 'Tercer puesto',
  final: 'Final',
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
  } catch {
    return iso;
  }
}

function ScoreOrDash({ home, away }: { home: number | null; away: number | null }) {
  if (home === null || away === null) {
    return <span className="text-slate-500">vs</span>;
  }
  return <span className="font-bold text-white">{home} - {away}</span>;
}

function GroupTable({ group }: { group: Group }) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="bg-slate-700/50 px-4 py-2 font-bold text-white">
        Grupo {group.group_name}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs">
              <th className="text-left px-3 py-2">Equipo</th>
              <th className="px-2 py-2">PJ</th>
              <th className="px-2 py-2">G</th>
              <th className="px-2 py-2">E</th>
              <th className="px-2 py-2">P</th>
              <th className="px-2 py-2">DG</th>
              <th className="px-2 py-2 font-bold">Pts</th>
            </tr>
          </thead>
          <tbody>
            {group.standings.map((t, i) => (
              <tr key={t.team_id} className={`border-t border-slate-700 ${i < 2 ? 'text-white' : 'text-slate-400'}`}>
                <td className="px-3 py-2">{t.team}</td>
                <td className="text-center px-2 py-2">{t.played}</td>
                <td className="text-center px-2 py-2">{t.won}</td>
                <td className="text-center px-2 py-2">{t.drawn}</td>
                <td className="text-center px-2 py-2">{t.lost}</td>
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

function BracketRound({ stage, matches }: { stage: string; matches: BracketMatch[] }) {
  return (
    <div>
      <h3 className="text-slate-300 font-bold mb-2">{STAGE_LABEL[stage] || matches[0]?.round_label || stage}</h3>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {matches.map((m) => (
          <div key={m.match_id} className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3">
            <div className="text-xs text-slate-500 mb-1">{formatDate(m.date)}</div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-200">{m.home_team}</span>
              <ScoreOrDash home={m.home_goals} away={m.away_goals} />
              <span className="text-slate-200 text-right">{m.away_team}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CompetitionDashboard({ seasonId }: { seasonId: number }) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [bracket, setBracket] = useState<BracketMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!seasonId) return;
    setLoading(true);
    setError(null);

    Promise.all([
      fetch(`${API_URL}/api/competitions/${seasonId}/groups`).then((r) => r.json()),
      fetch(`${API_URL}/api/competitions/${seasonId}/bracket`).then((r) => r.json()),
    ])
      .then(([groupsData, bracketData]) => {
        setGroups(groupsData.groups || []);
        setBracket(bracketData.matches || []);
      })
      .catch(() => setError('No se pudo cargar la información de la competencia'))
      .finally(() => setLoading(false));
  }, [seasonId]);

  if (loading) {
    return <div className="text-center py-16 text-slate-400">Cargando competencia...</div>;
  }
  if (error) {
    return <div className="text-center py-16 text-red-400">{error}</div>;
  }

  const bracketByStage = bracket.reduce<Record<string, BracketMatch[]>>((acc, m) => {
    (acc[m.stage] ||= []).push(m);
    return acc;
  }, {});
  const stageOrder = ['preliminary', 'round_of_32', 'round_of_16', 'quarterfinal', 'semifinal', 'third_place', 'final'];

  return (
    <div className="min-h-screen bg-slate-900 p-6 space-y-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {groups.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white">Fase de grupos</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {groups.map((g) => (
                <GroupTable key={g.group_name} group={g} />
              ))}
            </div>
          </section>
        )}

        {bracket.length > 0 && (
          <section className="space-y-6">
            <h2 className="text-xl font-bold text-white">Eliminatoria</h2>
            {stageOrder
              .filter((s) => bracketByStage[s]?.length)
              .map((s) => (
                <BracketRound key={s} stage={s} matches={bracketByStage[s]} />
              ))}
          </section>
        )}

        {groups.length === 0 && bracket.length === 0 && (
          <div className="text-center py-16 text-slate-500">Todavía no hay partidos cargados para esta competencia</div>
        )}
      </div>
    </div>
  );
}
