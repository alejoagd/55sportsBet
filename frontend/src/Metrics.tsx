import React, { useEffect, useState } from "react";

type MetricRow = {
  model: "poisson" | "weinston";
  n: number;
  acc_1x2: number | null;
  acc_over25: number | null;
  acc_btts: number | null;
  rmse_goals: number | null;
};

function pct(x?: number | null) {
  return x == null ? "—" : `${(x * 100).toFixed(1)}%`;
}

export default function Metrics({ apiBase, seasonId, from, to }:{
  apiBase: string; seasonId: number; from?: string; to?: string;
}) {
  const [rows, setRows] = useState<MetricRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const u = new URL("/api/metrics", apiBase);
    u.searchParams.set("season_id", String(seasonId));
    if (from) u.searchParams.set("date_from", from);
    if (to) u.searchParams.set("date_to", to);

    setLoading(true);
    fetch(u.toString())
      .then(r => r.json())
      .then(setRows)
      .finally(() => setLoading(false));
  }, [apiBase, seasonId, from, to]);

  return (
    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
      {rows.map(r => (
        <div key={r.model} className="rounded-2xl border bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Modelo</div>
          <div className="text-lg font-semibold capitalize mb-3">{r.model}</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div><div className="text-gray-500">Muestras</div><div className="font-semibold">{r.n}</div></div>
            <div><div className="text-gray-500">Acierto 1X2</div><div className="font-semibold">{pct(r.acc_1x2)}</div></div>
            <div><div className="text-gray-500">Acierto O/U 2.5</div><div className="font-semibold">{pct(r.acc_over25)}</div></div>
            <div><div className="text-gray-500">Acierto BTTS</div><div className="font-semibold">{pct(r.acc_btts)}</div></div>
          </div>
          <div className="mt-3 text-sm"><span className="text-gray-500">RMSE goles:</span> <span className="font-semibold">{r.rmse_goals?.toFixed?.(3) ?? "—"}</span></div>
        </div>
      ))}
      {loading && <div className="text-gray-500">Cargando métricas…</div>}
    </div>
  );
}
