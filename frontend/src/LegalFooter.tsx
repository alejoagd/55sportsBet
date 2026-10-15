import { Link } from 'react-router-dom';

// Aviso legal al pie de todas las páginas. Se mantiene corto a propósito:
// las tiendas de apps piden que sea visible que la app no recibe apuestas y
// que está dirigida a mayores de 18, y que la política de privacidad esté a
// un toque de distancia.
export default function LegalFooter() {
  return (
    <footer className="mt-8 border-t border-slate-800 px-4 py-5 text-center text-[11px] leading-relaxed text-slate-500">
      <p>
        <strong className="text-slate-400">+18.</strong> Juega con responsabilidad: apostar puede
        generar adicción. 55sports es una plataforma informativa y de análisis; no es una casa de
        apuestas ni recibe apuestas. Las predicciones son estimaciones estadísticas y no garantizan resultados.
      </p>
      <p className="mt-1.5">
        © {new Date().getFullYear()} 55sports ·{' '}
        <Link to="/privacidad" className="underline hover:text-slate-300">Política de Privacidad</Link>
      </p>
    </footer>
  );
}
