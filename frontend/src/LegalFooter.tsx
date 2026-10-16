import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';

// Aviso legal al pie de todas las páginas. Se mantiene corto a propósito:
// las tiendas de apps piden que sea visible que la app no recibe apuestas y
// que está dirigida a mayores de 18, y que la política de privacidad esté a
// un toque de distancia.
export default function LegalFooter() {
  const { t } = useTranslation();
  return (
    <footer className="mt-8 border-t border-slate-800 px-4 py-5 text-center text-[11px] leading-relaxed text-slate-500">
      <p>
        <Trans i18nKey="footer.legal" components={{ b: <strong className="text-slate-400" /> }} />
      </p>
      <p className="mt-1.5">
        © {new Date().getFullYear()} 55sports Stats ·{' '}
        <Link to="/privacidad" className="underline hover:text-slate-300">{t('footer.privacy')}</Link>
      </p>
    </footer>
  );
}
