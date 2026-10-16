import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { LANGUAGES, setLanguage, type LangCode } from './i18n';

// Selector de idioma de la barra superior: visible en desktop y mobile, en
// cualquier página. Muestra el código del idioma activo y un menú con los
// nombres completos (cada idioma en su propio idioma).
export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = LANGUAGES.find(l => l.code === i18n.language) ?? LANGUAGES[0];

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('touchstart', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('touchstart', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const choose = (code: LangCode) => {
    setLanguage(code);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t('lang.label')}
        title={t('lang.label')}
      >
        <Globe className="h-4 w-4" />
        <span>{current.short}</span>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={t('lang.label')}
          className="absolute right-0 top-full z-[70] mt-1 w-40 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 shadow-xl"
        >
          {LANGUAGES.map(l => (
            <li key={l.code} role="option" aria-selected={l.code === current.code}>
              <button
                onClick={() => choose(l.code)}
                className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors
                  ${l.code === current.code
                    ? 'bg-blue-600/20 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
              >
                <span>{l.label}</span>
                <span className="text-[11px] text-slate-500">{l.short}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
