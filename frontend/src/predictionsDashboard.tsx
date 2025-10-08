import React, { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { CalendarDays, RefreshCw, Search } from "lucide-react";
import Metrics from "./Metrics";

type Row = {
  match_id: number;
  date: string;
  home_team: string;
  away_team: string;

  expected_home_goals: number | null;
  expected_away_goals: number | null;
  prob_home_win: number | null;
  prob_draw: number | null;
  prob_away_win: number | null;
  poisson_over_2: number | null;
  poisson_under_2: number | null;
  poisson_both_score: number | null;
  poisson_both_noscore: number | null;

  local_goals: number | null;
  away_goals: number | null;
  result_1x2: number | null;
  wein_over_2: string | null;
  wein_both_score: string | null;

  shots_home: number | null;
  shots_away: number | null;
  shots_target_home: number | null;
  shots_target_away: number | null;
  fouls_home: number | null;
  fouls_away: number | null;
  cards_home: number | null;
  cards_away: number | null;
  corners_home: number | null;
  corners_away: number | null;
  win_corners: string | null;
};

function pct(n?: number | null) {
  if (n == null) return "—";
  return (n * 100).toFixed(1) + "%";
}
function num(n?: number | null, d = 2) {
  if (n == null) return "—";
  return Number(n).toFixed(d);
}

const Pill: React.FC<{ children: React.ReactNode; tone?: "green" | "blue" | "gray" | "amber" }>=
({ children, tone = "gray" }) => {
  const toneMap: Record<string, string> = {
    green: "bg-green-100 text-green-800",
    blue: "bg-blue-100 text-blue-800",
    gray: "bg-gray-100 text-gray-800",
    amber: "bg-amber-100 text-amber-900",
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${toneMap[tone]}`}>{children}</span>;
};

const ProbBar: React.FC<{ label: string; value: number | null; tone?: string }> = ({ label, value }) => {
  const width = value ? Math.max(2, Math.min(100, value * 100)) : 0;
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{label}</span>
        <span>{pct(value)}</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded">
        <div className="h-2 bg-gray-800 rounded" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
};

export default function PredictionsDashboard() {
  const [apiBase, setApiBase] = useState("http://localhost:8000");
  const [seasonId, setSeasonId] = useState<number>(2);
  const [from, setFrom] = useState<string>("2025-08-15");
  const [to, setTo] = useState<string>("2025-08-31");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);

  const url = useMemo(() => {
    const u = new URL("/api/predictions", apiBase);
    u.searchParams.set("season_id", String(seasonId));
    if (from) u.searchParams.set("date_from", from);
    if (to) u.searchParams.set("date_to", to);
    return u.toString();
  }, [apiBase, seasonId, from, to]);

  async function fetchData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = (await res.json()) as Row[];
      setRows(data);
    } catch (e: any) {
      setError(e?.message || "Error al cargar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

return (
  <div className="min-h-screen bg-gray-50">
    {/* Header */}
    <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
        <CalendarDays className="w-5 h-5 text-gray-700" />
        <h1 className="text-lg font-semibold">Predicciones — Dashboard</h1>

        <div className="ml-auto flex items-center gap-2">
          <input
            className="border rounded px-2 py-1 text-sm w-36"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            title="API base URL"
          />
          <button
            onClick={fetchData}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded bg-black text-white text-sm hover:opacity-90"
            disabled={loading}
          >
            <RefreshCw className="w-4 h-4" />
            {loading ? "Cargando..." : "Refrescar"}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-6xl mx-auto px-4 pb-3 grid grid-cols-2 md:grid-cols-5 gap-2">
        <div>
          <label className="block text-xs text-gray-600">Season</label>
          <input
            type="number"
            className="border rounded px-2 py-1 w-full"
            value={seasonId}
            onChange={(e) => setSeasonId(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Desde</label>
          <input type="date" className="border rounded px-2 py-1 w-full" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Hasta</label>
          <input type="date" className="border rounded px-2 py-1 w-full" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <div className="flex items-end">
          <button
            onClick={fetchData}
            className="inline-flex items-center gap-1 px-3 py-2 w-full rounded bg-gray-900 text-white hover:bg-gray-800"
            disabled={loading}
          >
            <Search className="w-4 h-4" /> Buscar
          </button>
        </div>
      </div>
    </header>

    {/* Body */}
    <main className="max-w-6xl mx-auto px-4 py-6">
        {/* ---- MÉTRICAS DE EFECTIVIDAD (añadido) ---- */}
        <Metrics
        apiBase={apiBase}
        seasonId={seasonId}
        from={from || undefined}
        to={to || undefined}
        />

        {/* Mensaje cuando no hay partidos */}
        {rows.length === 0 && !loading && (
        <div className="text-gray-500">No hay partidos para los filtros seleccionados.</div>
        )}

        {/* Render de cada partido */}
        {rows.map((r) => (
        <div key={r.match_id}>
            {/* ... tu render de la tarjeta/tabla del partido r ... */}
        </div>
        ))}
      {/* ------------------------------------------ */}
      {error && <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">{error}</div>}

      {rows.length === 0 && !loading ? (
        <div className="text-gray-500">No hay partidos para los filtros seleccionados.</div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {rows.map((r) => {
            const chartData = [
              { name: "Home", p: Number(r.prob_home_win || 0) },
              { name: "Draw", p: Number(r.prob_draw || 0) },
              { name: "Away", p: Number(r.prob_away_win || 0) },
            ];
            const dateFmt = new Date(r.date).toLocaleDateString();
            return (
              <div key={r.match_id} className="rounded-2xl border bg-white shadow-sm overflow-hidden">
                <div className="p-4 md:p-5">
                  {/* Header row */}
                  <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
                    <div className="text-sm text-gray-500">{dateFmt}</div>
                    <div className="text-lg font-semibold">
                      {r.home_team} <span className="text-gray-400">vs</span> {r.away_team}
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                      <Pill tone="blue">xG {num(r.expected_home_goals)} — {num(r.expected_away_goals)}</Pill>
                      <Pill tone={r.wein_over_2 === "OVER" ? "green" : "gray"}>Over 2.5: {pct(r.poisson_over_2)}</Pill>
                      <Pill tone={r.wein_both_score === "YES" ? "green" : "gray"}>BTTS: {pct(r.poisson_both_score)}</Pill>
                    </div>
                  </div>

                  {/* Probabilities */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div className="space-y-2">
                      <ProbBar label="Home" value={r.prob_home_win} />
                      <ProbBar label="Draw" value={r.prob_draw} />
                      <ProbBar label="Away" value={r.prob_away_win} />
                    </div>
                    <div className="h-36">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                          <XAxis dataKey="name" />
                          <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} domain={[0, 1]} />
                          <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`} />
                          <Bar dataKey="p" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Stats table */}
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500">
                          <th className="py-2 pr-4">Stat</th>
                          <th className="py-2 pr-4">{r.home_team}</th>
                          <th className="py-2 pr-4">{r.away_team}</th>
                          <th className="py-2 pr-4">Edge</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          ["Shots", r.shots_home, r.shots_away],
                          ["Shots OT", r.shots_target_home, r.shots_target_away],
                          ["Fouls", r.fouls_home, r.fouls_away],
                          ["Cards", r.cards_home, r.cards_away],
                          ["Corners", r.corners_home, r.corners_away],
                        ].map(([label, hv, av], idx) => {
                          const h = Number(hv ?? 0);
                          const a = Number(av ?? 0);
                          const edge = h === a ? "—" : h > a ? `${r.home_team}` : `${r.away_team}`;
                          return (
                            <tr key={idx} className="border-t">
                              <td className="py-2 pr-4">{label}</td>
                              <td className="py-2 pr-4">{num(h, 2)}</td>
                              <td className="py-2 pr-4">{num(a, 2)}</td>
                              <td className="py-2 pr-4">{edge}</td>
                            </tr>
                          );
                        })}
                        <tr className="border-t">
                          <td className="py-2 pr-4">Win Corners</td>
                          <td className="py-2 pr-4" colSpan={3}>
                            <Pill tone="amber">{r.win_corners || "—"}</Pill>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}


    </main>
  </div>
);
}

