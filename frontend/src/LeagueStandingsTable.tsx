import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Tabla de posiciones de la fase actual de la temporada (el backend ya
// resuelve cuál es "la actual" cuando la liga divide el año en Apertura/
// Clausura). Algunas ligas (Liga Argentina, Liga Betplay) además dividen
// esa fase en zonas/grupos reales — el backend devuelve `groups` en ese
// caso en vez de `standings`, y acá se renderiza una tabla por grupo.

interface Standing {
  team_id: number;
  team: string;
  logo_url?: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
}

// Mismo patrón que CompactMatchList: si no hay logo (equipo sin escudo
// todavía) o la imagen falla al cargar, cae a un placeholder circular.
function TeamLogo({ url, alt }: { url?: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return (
      <span className="w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-slate-700/60 flex items-center justify-center shrink-0 text-[10px] sm:text-xs">
        ⚽
      </span>
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      className="w-4 h-4 sm:w-5 sm:h-5 object-contain shrink-0"
      onError={() => setFailed(true)}
    />
  );
}

interface Group {
  group_name: string;
  standings: Standing[];
}

// En móvil la tabla debe verse COMPLETA sin scroll lateral: table-fixed con
// columnas numéricas angostas, el equipo se recorta con "…" y GF/GC se
// fusionan en una sola columna "GF:GC" (como Flashscore). Desde sm (≥640px)
// vuelve al diseño amplio con GF y GC por separado.
function Table({ standings, title }: { standings: Standing[]; title?: string }) {
  const { t: tr } = useTranslation();
  const num = 'px-0.5 sm:px-2 py-2.5 text-center';
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {title && (
        <div className="bg-slate-700/50 px-3 sm:px-4 py-2 font-bold text-white">{title}</div>
      )}
      <table className="w-full table-fixed text-xs sm:text-sm">
        <colgroup>
          <col className="w-5 sm:w-10" />
          <col />
          <col className="w-5 sm:w-12" />
          <col className="w-5 sm:w-12" />
          <col className="w-5 sm:w-12" />
          <col className="w-5 sm:w-12" />
          <col className="hidden sm:table-column sm:w-12" />
          <col className="hidden sm:table-column sm:w-12" />
          <col className="w-[42px] sm:hidden" />
          <col className="w-[30px] sm:w-12" />
          <col className="w-7 sm:w-14" />
        </colgroup>
        <thead>
          <tr className="text-slate-400 text-[11px] sm:text-xs">
            <th className="pl-1.5 pr-0 sm:px-3 py-2 text-left">#</th>
            <th className="px-1 sm:px-3 py-2 text-left">{tr('standings.team')}</th>
            <th className={num}>{tr('standings.played')}</th>
            <th className={num}>{tr('standings.won')}</th>
            <th className={num}>{tr('standings.drawn')}</th>
            <th className={num}>{tr('standings.lost')}</th>
            <th className={`${num} hidden sm:table-cell`}>{tr('standings.gf')}</th>
            <th className={`${num} hidden sm:table-cell`}>{tr('standings.ga')}</th>
            <th className={`${num} sm:hidden`}>{tr('standings.gf')}:{tr('standings.ga')}</th>
            <th className={num}>{tr('standings.gd')}</th>
            <th className={`${num} pr-1.5 sm:pr-2 font-bold`}>{tr('standings.pts')}</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((t, i) => (
            <tr key={t.team_id} className={`border-t border-slate-700 ${i < 4 ? 'text-white' : 'text-slate-400'}`}>
              <td className="pl-1.5 pr-0 sm:px-3 py-2.5 text-slate-500 tabular-nums">{i + 1}</td>
              <td className="px-1 sm:px-3 py-2.5">
                <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
                  <TeamLogo url={t.logo_url} alt={t.team} />
                  <span className="truncate" title={t.team}>{t.team}</span>
                </div>
              </td>
              <td className={`${num} tabular-nums`}>{t.played}</td>
              <td className={`${num} tabular-nums`}>{t.won}</td>
              <td className={`${num} tabular-nums`}>{t.drawn}</td>
              <td className={`${num} tabular-nums`}>{t.lost}</td>
              <td className={`${num} hidden sm:table-cell tabular-nums`}>{t.goals_for}</td>
              <td className={`${num} hidden sm:table-cell tabular-nums`}>{t.goals_against}</td>
              <td className={`${num} sm:hidden tabular-nums`}>{t.goals_for}:{t.goals_against}</td>
              <td className={`${num} tabular-nums`}>{t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}</td>
              <td className={`${num} pr-1.5 sm:pr-2 font-bold tabular-nums`}>{t.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function LeagueStandingsTable({ seasonId }: { seasonId: number }) {
  const { t } = useTranslation();
  const [standings, setStandings] = useState<Standing[] | null>(null);
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!seasonId) return;
    setLoading(true);
    setError(false);
    setStandings(null);
    setGroups(null);
    fetch(`${API_URL}/api/competitions/${seasonId}/standings`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => {
        if (data.groups) setGroups(data.groups);
        else setStandings(data.standings || []);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [seasonId]);

  if (loading) {
    return <div className="text-center py-16 text-slate-400">{t('standings.loading')}</div>;
  }
  if (error) {
    return <div className="text-center py-16 text-red-400">{t('standings.error')}</div>;
  }
  if ((!groups || groups.length === 0) && (!standings || standings.length === 0)) {
    return <div className="text-center py-16 text-slate-500">{t('standings.empty')}</div>;
  }

  if (groups) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {groups.map((g) => (
          <Table key={g.group_name} standings={g.standings} title={t('standings.group', { name: g.group_name.replace(/^Group\s*/i, '') })} />
        ))}
      </div>
    );
  }

  return <Table standings={standings!} />;
}
