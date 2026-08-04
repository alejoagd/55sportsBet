import { useEffect, useState } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Mismo componente visual que NewsView/NewsCard de WorldCupDashboard.tsx,
// apuntando al feed genérico por liga. Para las ligas sudamericanas es
// normal que salga vacío casi siempre (Marca, la fuente RSS, cubre sobre
// todo fútbol europeo) — no es un error, solo no hay artículos que calcen.

interface NewsArticle {
  title: string;
  description: string;
  image: string | null;
  url: string;
  source: string;
  published_at: string;
}

function formatRelativeDate(isoStr: string): string {
  try {
    const diffMs = Date.now() - new Date(isoStr).getTime();
    const diffM = Math.floor(diffMs / 60000);
    if (diffM < 2) return 'ahora';
    if (diffM < 60) return `hace ${diffM}m`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `hace ${diffH}h`;
    const diffD = Math.floor(diffH / 24);
    if (diffD === 1) return 'ayer';
    return `hace ${diffD} días`;
  } catch {
    return '';
  }
}

const CARD_GRADIENTS = [
  'from-blue-900/60 to-slate-900',
  'from-emerald-900/60 to-slate-900',
  'from-amber-900/60 to-slate-900',
  'from-purple-900/60 to-slate-900',
  'from-rose-900/60 to-slate-900',
];

function NewsCard({ article, index }: { article: NewsArticle; index: number }) {
  const [imgError, setImgError] = useState(false);
  const gradient = CARD_GRADIENTS[index % CARD_GRADIENTS.length];
  const showImg = article.image && !imgError;

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col overflow-hidden rounded-xl border border-slate-700/50
                 hover:border-yellow-500/40 hover:shadow-lg hover:shadow-yellow-400/5
                 transition-all group bg-slate-800/60"
    >
      <div className="relative w-full h-44 overflow-hidden flex-shrink-0">
        {showImg ? (
          <img
            src={article.image!}
            alt={article.title}
            loading="lazy"
            onError={() => setImgError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${gradient} flex items-center justify-center`}>
            <span className="text-5xl opacity-30">⚽</span>
          </div>
        )}
        <span className="absolute top-2 left-2 bg-black/60 backdrop-blur-sm text-white text-[11px] font-semibold px-2 py-0.5 rounded-full">
          {article.source}
        </span>
        <span className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm text-slate-300 text-[11px] px-2 py-0.5 rounded-full">
          {formatRelativeDate(article.published_at)}
        </span>
      </div>

      <div className="flex flex-col gap-2 p-4 flex-1">
        <h3 className="text-white font-semibold text-sm leading-snug line-clamp-2 group-hover:text-yellow-400 transition-colors">
          {article.title}
        </h3>
        {article.description && (
          <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">{article.description}</p>
        )}
        <span className="mt-auto pt-2 text-xs text-yellow-500/70 font-medium group-hover:text-yellow-400 transition-colors">
          Leer más →
        </span>
      </div>
    </a>
  );
}

export default function LeagueNewsView({ leagueId, leagueName }: { leagueId: number; leagueName: string }) {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!leagueId) return;
    setLoading(true);
    setError(false);
    fetch(`${API_URL}/api/leagues/${leagueId}/news`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((data: NewsArticle[]) => { setNews(data); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, [leagueId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
        <div className="text-5xl animate-pulse">📰</div>
        <p className="text-sm">Cargando noticias...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
        <div className="text-5xl">📭</div>
        <p className="text-sm">No se pudieron cargar las noticias</p>
      </div>
    );
  }

  if (news.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
        <div className="text-5xl">📭</div>
        <p className="text-sm">No hay noticias recientes de {leagueName}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-white font-bold text-lg">Noticias de {leagueName}</h2>
        <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-full border border-slate-700">
          Fuente: Marca · actualizado cada hora
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {news.map((article, i) => (
          <NewsCard key={i} article={article} index={i} />
        ))}
      </div>
    </div>
  );
}
