// Barra de probabilidad 1X2 — mismo azul/naranja que usa el resto de la app
// para local/visitante (MatchDetail, etc.), gris para el empate.
export default function ProbabilityBar({
  home, draw, away, size = 'sm',
}: {
  home?: number | null; draw?: number | null; away?: number | null; size?: 'sm' | 'lg';
}) {
  const h = Math.max(0, (home ?? 0) * 100);
  const d = Math.max(0, (draw ?? 0) * 100);
  const a = Math.max(0, (away ?? 0) * 100);
  const barH = size === 'lg' ? 'h-2.5' : 'h-1.5';
  return (
    <div className="w-full">
      <div className={`flex ${barH} rounded-full overflow-hidden bg-slate-700/60`}>
        <div className="bg-blue-500" style={{ width: `${h}%` }} />
        <div className="bg-slate-400" style={{ width: `${d}%` }} />
        <div className="bg-orange-500" style={{ width: `${a}%` }} />
      </div>
      <div className="flex justify-between mt-1 text-[10px] sm:text-[11px] font-semibold tabular-nums">
        <span className="text-blue-400">{h.toFixed(0)}%</span>
        <span className="text-slate-400">{d.toFixed(0)}%</span>
        <span className="text-orange-400">{a.toFixed(0)}%</span>
      </div>
    </div>
  );
}
