import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import es from './locales/es';
import en from './locales/en';
import pt from './locales/pt';
import fr from './locales/fr';
import { nsBundles } from './locales/ns';

export const LANGUAGES = [
  { code: 'es', label: 'Español', short: 'ES', locale: 'es-CO' },
  { code: 'en', label: 'English', short: 'EN', locale: 'en-US' },
  { code: 'pt', label: 'Português', short: 'PT', locale: 'pt-BR' },
  { code: 'fr', label: 'Français', short: 'FR', locale: 'fr-FR' },
] as const;

export type LangCode = (typeof LANGUAGES)[number]['code'];

const STORAGE_KEY = 'lang';
const SUPPORTED = LANGUAGES.map(l => l.code) as string[];

function isSupported(code: string | null | undefined): code is LangCode {
  return !!code && SUPPORTED.includes(code);
}

// Idioma inicial: 1) el que el usuario eligió antes, 2) el del navegador/
// teléfono si es uno de los 4, 3) inglés para cualquier otro idioma (es el
// más entendible para quien llega de un país que no cubrimos), 4) español si
// el navegador no informa idioma. El acceso a localStorage va en try/catch:
// falla en modo privado o con el almacenamiento bloqueado.
function detectLanguage(): LangCode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isSupported(saved)) return saved;
  } catch { /* sin almacenamiento: se detecta por navegador */ }

  const preferred = typeof navigator !== 'undefined'
    ? (navigator.languages?.length ? navigator.languages : [navigator.language])
    : [];
  for (const tag of preferred) {
    const base = tag?.toLowerCase().split('-')[0];
    if (isSupported(base)) return base;
  }
  return preferred.length > 0 && preferred[0] ? 'en' : 'es';
}

// Diccionario base + los de cada pantalla (locales/ns), bajo su propio espacio
// de nombres: t('matchDetail.algo').
const withScreens = (lang: LangCode, base: object) => ({
  ...base,
  ...Object.fromEntries(Object.entries(nsBundles).map(([ns, bundle]) => [ns, bundle[lang]])),
});

i18n.use(initReactI18next).init({
  resources: {
    es: { translation: withScreens('es', es) },
    en: { translation: withScreens('en', en) },
    pt: { translation: withScreens('pt', pt) },
    fr: { translation: withScreens('fr', fr) },
  },
  lng: detectLanguage(),
  fallbackLng: 'es',
  interpolation: { escapeValue: false }, // React ya escapa
  returnNull: false,
});

function applyHtmlLang(code: string) {
  if (typeof document !== 'undefined') document.documentElement.lang = code;
}
applyHtmlLang(i18n.language);
i18n.on('languageChanged', applyHtmlLang);

export function setLanguage(code: LangCode) {
  try { localStorage.setItem(STORAGE_KEY, code); } catch { /* ignorar */ }
  void i18n.changeLanguage(code);
}

// Etiqueta BCP-47 para toLocaleDateString / Intl según el idioma activo.
export function localeTag(): string {
  return LANGUAGES.find(l => l.code === i18n.language)?.locale ?? 'es-CO';
}

// "hace 5 min" / "5 min ago" / "ayer" / "yesterday"… sin textos propios.
export function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diffMs)) return '';
  const rtf = new Intl.RelativeTimeFormat(localeTag(), { numeric: 'auto' });
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 2) return rtf.format(0, 'minute');
  if (minutes < 60) return rtf.format(-minutes, 'minute');
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return rtf.format(-hours, 'hour');
  return rtf.format(-Math.floor(hours / 24), 'day');
}

export default i18n;
