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

// ── Llaves (ida/vuelta) ───────────────────────────────────────────────────
// Octavos/cuartos/semis de Libertadores y Sudamericana son series de ida y
// vuelta (la Final es partido único). Para saber quién avanza hay que sumar
// el marcador de los 2 fixtures de la llave. Se agrupan por (stage, equipos
// sin importar orden) — a diferencia del bracket del Mundial, acá no hace
// falta adivinar nada: los fixtures reales ya vienen con los equipos
// correctos desde ESPN/API-Football.

interface Tie {
  key: string;
  stage: string;
  teamA: string;
  teamB: string;
  legs: BracketMatch[];
  aggA: number | null;
  aggB: number | null;
}

function groupIntoTies(matches: BracketMatch[]): Tie[] {
  const byKey = new Map<string, BracketMatch[]>();
  for (const m of matches) {
    const [a, b] = [m.home_team, m.away_team].sort();
    const key = `${m.stage}__${a}__${b}`;
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key)!.push(m);
  }

  return Array.from(byKey.values()).map((legs) => {
    const sorted = [...legs].sort((x, y) => x.date.localeCompare(y.date));
    const [teamA, teamB] = [sorted[0].home_team, sorted[0].away_team].sort();

    let aggA: number | null = 0;
    let aggB: number | null = 0;
    for (const leg of sorted) {
      if (leg.home_goals === null || leg.away_goals === null) {
        aggA = null;
        aggB = null;
        break;
      }
      if (leg.home_team === teamA) {
        aggA! += leg.home_goals;
        aggB! += leg.away_goals;
      } else {
        aggA! += leg.away_goals;
        aggB! += leg.home_goals;
      }
    }

    return {
      key: `${sorted[0].stage}__${teamA}__${teamB}`,
      stage: sorted[0].stage,
      teamA,
      teamB,
      legs: sorted,
      aggA,
      aggB,
    };
  });
}

function TieTeamRow({ name, isWinner, dim }: { name: string; isWinner: boolean; dim: boolean }) {
  return (
    <div className={`flex items-center justify-between px-2.5 py-1.5 ${isWinner ? 'bg-green-500/20' : ''} ${dim ? 'opacity-40' : ''}`}>
      <span className="text-xs font-semibold text-white truncate">{name}</span>
      {isWinner && <span className="text-green-400 text-xs flex-shrink-0">✓</span>}
    </div>
  );
}

function TieCard({ tie }: { tie: Tie }) {
  const complete = tie.aggA !== null && tie.aggB !== null;
  const decidedByPens = complete && tie.aggA === tie.aggB;
  const winner = complete && !decidedByPens
    ? (tie.aggA! > tie.aggB! ? tie.teamA : tie.teamB)
    : null;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden w-56 flex-shrink-0">
      <div className="px-2.5 py-1 bg-slate-900/60 border-b border-slate-700/50 text-[10px] text-slate-500 font-bold">
        {formatDate(tie.legs[0].date)}
        {tie.legs.length > 1 && ` – ${formatDate(tie.legs[tie.legs.length - 1].date)}`}
      </div>
      <TieTeamRow name={tie.teamA} isWinner={winner === tie.teamA} dim={!!winner && winner !== tie.teamA} />
      <div className="mx-2.5 h-px bg-slate-700" />
      <TieTeamRow name={tie.teamB} isWinner={winner === tie.teamB} dim={!!winner && winner !== tie.teamB} />
      <div className="px-2.5 py-1.5 border-t border-slate-700/50 space-y-0.5">
        {tie.legs.map((leg, i) => {
          const homeIsA = leg.home_team === tie.teamA;
          return (
            <div key={leg.match_id} className="flex items-center justify-between text-[11px] text-slate-400">
              <span>{tie.legs.length > 1 ? (i === 0 ? 'Ida' : 'Vuelta') : ''}</span>
              <ScoreOrDash
                home={homeIsA ? leg.home_goals : leg.away_goals}
                away={homeIsA ? leg.away_goals : leg.home_goals}
              />
            </div>
          );
        })}
        {complete && (
          <div className={`text-[11px] font-bold text-center pt-1 mt-1 border-t border-slate-700/30
            ${decidedByPens ? 'text-yellow-400' : 'text-green-400'}`}>
            Global {tie.aggA}-{tie.aggB}{decidedByPens ? ' (penales)' : ''}
          </div>
        )}
      </div>
    </div>
  );
}

function BracketColumn({ stage, ties }: { stage: string; ties: Tie[] }) {
  return (
    <div className="flex flex-col gap-4 flex-shrink-0">
      <h3 className="text-slate-300 font-bold text-sm text-center">
        {STAGE_LABEL[stage] || ties[0]?.legs[0]?.round_label || stage}
      </h3>
      <div className="flex flex-col justify-around gap-4 flex-1">
        {ties.map((tie) => (
          <TieCard key={tie.key} tie={tie} />
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

  const stageOrder = ['preliminary', 'round_of_32', 'round_of_16', 'quarterfinal', 'semifinal', 'third_place', 'final'];
  const ties = groupIntoTies(bracket);
  const tiesByStage = ties.reduce<Record<string, Tie[]>>((acc, t) => {
    (acc[t.stage] ||= []).push(t);
    return acc;
  }, {});
  const stagesPresent = stageOrder.filter((s) => tiesByStage[s]?.length);

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
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white">Eliminatoria</h2>
            <div className="flex gap-6 overflow-x-auto scrollbar-hide pb-2">
              {stagesPresent.map((s, i) => (
                <div key={s} className="flex items-center gap-6">
                  <BracketColumn stage={s} ties={tiesByStage[s]} />
                  {i < stagesPresent.length - 1 && (
                    <span className="text-slate-600 text-xl flex-shrink-0">➜</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {groups.length === 0 && bracket.length === 0 && (
          <div className="text-center py-16 text-slate-500">Todavía no hay partidos cargados para esta competencia</div>
        )}
      </div>
    </div>
  );
}
