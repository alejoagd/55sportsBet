import { useMemo, useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { localeTag } from './i18n';

// `value` es lo que se guarda en la BD (siempre en español, para que los datos
// de suscriptores sigan siendo consistentes sin importar el idioma de la
// interfaz). `region` (ISO 3166) sirve para mostrar el nombre en el idioma
// activo con Intl.DisplayNames; `key` es para los que no tienen código ISO.
const PAISES: { value: string; region?: string; key?: string }[] = [
  { value: 'Alemania', region: 'DE' }, { value: 'Argentina', region: 'AR' },
  { value: 'Australia', region: 'AU' }, { value: 'Austria', region: 'AT' },
  { value: 'Bélgica', region: 'BE' }, { value: 'Bolivia', region: 'BO' }, { value: 'Brasil', region: 'BR' },
  { value: 'Canadá', region: 'CA' }, { value: 'Chile', region: 'CL' }, { value: 'Colombia', region: 'CO' },
  { value: 'Costa Rica', region: 'CR' }, { value: 'Croacia', region: 'HR' }, { value: 'Cuba', region: 'CU' },
  { value: 'Dinamarca', region: 'DK' },
  { value: 'Ecuador', region: 'EC' }, { value: 'El Salvador', region: 'SV' }, { value: 'Escocia', key: 'scotland' },
  { value: 'Eslovaquia', region: 'SK' }, { value: 'Eslovenia', region: 'SI' }, { value: 'España', region: 'ES' },
  { value: 'Estados Unidos', region: 'US' },
  { value: 'Francia', region: 'FR' },
  { value: 'Gales', key: 'wales' }, { value: 'Grecia', region: 'GR' }, { value: 'Guatemala', region: 'GT' },
  { value: 'Holanda', region: 'NL' }, { value: 'Honduras', region: 'HN' }, { value: 'Hungría', region: 'HU' },
  { value: 'Inglaterra', key: 'england' }, { value: 'Irlanda', region: 'IE' }, { value: 'Italia', region: 'IT' },
  { value: 'Japón', region: 'JP' },
  { value: 'Marruecos', region: 'MA' }, { value: 'México', region: 'MX' },
  { value: 'Nicaragua', region: 'NI' }, { value: 'Noruega', region: 'NO' },
  { value: 'Panamá', region: 'PA' }, { value: 'Paraguay', region: 'PY' }, { value: 'Perú', region: 'PE' },
  { value: 'Polonia', region: 'PL' }, { value: 'Portugal', region: 'PT' }, { value: 'Puerto Rico', region: 'PR' },
  { value: 'República Checa', region: 'CZ' }, { value: 'República Dominicana', region: 'DO' },
  { value: 'Rumanía', region: 'RO' }, { value: 'Rusia', region: 'RU' },
  { value: 'Serbia', region: 'RS' }, { value: 'Suecia', region: 'SE' }, { value: 'Suiza', region: 'CH' },
  { value: 'Turquía', region: 'TR' },
  { value: 'Ucrania', region: 'UA' }, { value: 'Uruguay', region: 'UY' },
  { value: 'Venezuela', region: 'VE' },
  { value: 'Otro', key: 'other' },
];

interface FormData {
  nombre: string;
  apellido: string;
  correo: string;
  telefono: string;
  pais: string;
  ciudad: string;
  acepta_politica: boolean;
}

type Errors = Partial<Record<keyof FormData, string>>; // valores = claves de traducción

const EMPTY: FormData = {
  nombre: '', apellido: '', correo: '',
  telefono: '', pais: '', ciudad: '', acepta_politica: false,
};

function validate(f: FormData): Errors {
  const e: Errors = {};
  if (!f.nombre.trim())   e.nombre   = 'subscribe.errRequired';
  if (!f.apellido.trim()) e.apellido = 'subscribe.errRequired';
  if (!f.correo.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.correo))
    e.correo = 'subscribe.errEmail';
  if (!f.telefono.trim() || !/^\+?[\d\s\-()]{7,}$/.test(f.telefono))
    e.telefono = 'subscribe.errPhone';
  if (!f.pais.trim())     e.pais     = 'subscribe.errCountry';
  if (!f.ciudad.trim())   e.ciudad   = 'subscribe.errRequired';
  if (!f.acepta_politica) e.acepta_politica = 'subscribe.errAccept';
  return e;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SubscribeModal({ isOpen, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const [form, setForm] = useState<FormData>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  // Clave de traducción del error del servidor (el texto del backend está en español)
  const [serverErrKey, setServerErrKey] = useState('subscribe.errGeneric');

  // Países con el nombre en el idioma activo, ordenados alfabéticamente en ese
  // idioma ("Otro" siempre al final).
  const countryOptions = useMemo(() => {
    let names: Intl.DisplayNames | null = null;
    try { names = new Intl.DisplayNames([localeTag()], { type: 'region' }); } catch { /* navegador viejo */ }
    const label = (c: (typeof PAISES)[number]) =>
      c.key ? t(`countries.${c.key}`) : (c.region && names?.of(c.region)) || c.value;
    const options = PAISES.map(c => ({ value: c.value, label: label(c), last: c.key === 'other' }));
    return options.sort((a, b) =>
      a.last === b.last ? a.label.localeCompare(b.label, localeTag()) : a.last ? 1 : -1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language]);

  if (!isOpen) return null;

  const set = (field: keyof FormData) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(prev => ({ ...prev, [field]: field === 'acepta_politica' ? e.target.checked : e.target.value }));

  const setSelect = (field: keyof FormData) =>
    (e: React.ChangeEvent<HTMLSelectElement>) =>
      setForm(prev => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setErrors({});
    setStatus('loading');

    try {
      const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/subscribers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setStatus('success');
      } else {
        // Los mensajes del backend vienen en español: se traducen por código HTTP.
        setStatus('error');
        setServerErrKey(
          res.status === 409 ? 'subscribe.errDuplicate'
          : res.status === 400 ? 'subscribe.errInvalid'
          : 'subscribe.errGeneric'
        );
      }
    } catch {
      setStatus('error');
      setServerErrKey('subscribe.errNetwork');
    }
  };

  const handleClose = () => {
    setForm(EMPTY);
    setErrors({});
    setStatus('idle');
    onClose();
  };

  const err = (field: keyof FormData) => (errors[field] ? t(errors[field]!) : undefined);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md max-h-[calc(100dvh-2rem)] overflow-y-auto bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-yellow-500 to-amber-600 px-6 py-5">
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-slate-900/70 hover:text-slate-900 transition-colors"
            aria-label={t('subscribe.close')}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <span className="text-3xl">🔔</span>
            <div>
              <h2 className="text-slate-900 font-bold text-lg leading-tight">{t('subscribe.title')}</h2>
              <p className="text-slate-800 text-xs mt-0.5">{t('subscribe.subtitle')}</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {status === 'success' ? (
            <div className="flex flex-col items-center gap-4 py-6 text-center">
              <div className="text-6xl">🎉</div>
              <p className="text-white font-semibold text-lg">{t('subscribe.successTitle')}</p>
              <p className="text-slate-400 text-sm">{t('subscribe.successBody')}</p>
              <button
                onClick={handleClose}
                className="mt-2 px-6 py-2.5 bg-yellow-400 text-slate-900 font-semibold rounded-xl hover:bg-yellow-300 transition-colors"
              >
                {t('subscribe.ok')}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {status === 'error' && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
                  {t(serverErrKey)}
                </div>
              )}

              {/* Nombre + Apellido */}
              <div className="grid grid-cols-2 gap-3">
                <Field label={t('subscribe.firstName')} error={err('nombre')}>
                  <input
                    type="text" placeholder={t('subscribe.firstNamePh')}
                    value={form.nombre} onChange={set('nombre')}
                    className={inputCls(!!errors.nombre)}
                  />
                </Field>
                <Field label={t('subscribe.lastName')} error={err('apellido')}>
                  <input
                    type="text" placeholder={t('subscribe.lastNamePh')}
                    value={form.apellido} onChange={set('apellido')}
                    className={inputCls(!!errors.apellido)}
                  />
                </Field>
              </div>

              {/* Correo */}
              <Field label={t('subscribe.email')} error={err('correo')}>
                <input
                  type="email" placeholder="name@example.com"
                  value={form.correo} onChange={set('correo')}
                  className={inputCls(!!errors.correo)}
                />
              </Field>

              {/* Teléfono */}
              <Field label={t('subscribe.phone')} error={err('telefono')}>
                <input
                  type="tel" placeholder="+57 300 000 0000"
                  value={form.telefono} onChange={set('telefono')}
                  className={inputCls(!!errors.telefono)}
                />
              </Field>

              {/* País + Ciudad */}
              <div className="grid grid-cols-2 gap-3">
                <Field label={t('subscribe.country')} error={err('pais')}>
                  <select
                    value={form.pais} onChange={setSelect('pais')}
                    className={`${inputCls(!!errors.pais)} cursor-pointer`}
                  >
                    <option value="">{t('subscribe.select')}</option>
                    {countryOptions.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label={t('subscribe.city')} error={err('ciudad')}>
                  <input
                    type="text" placeholder={t('subscribe.cityPh')}
                    value={form.ciudad} onChange={set('ciudad')}
                    className={inputCls(!!errors.ciudad)}
                  />
                </Field>
              </div>

              {/* Checkbox política */}
              <div className="pt-1">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={form.acepta_politica}
                    onChange={set('acepta_politica')}
                    className="mt-0.5 w-4 h-4 accent-yellow-400 flex-shrink-0 cursor-pointer"
                  />
                  <span className="text-xs text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">
                    <Trans
                      i18nKey="subscribe.consent"
                      components={{
                        b: <strong className="text-slate-300" />,
                        privacy: (
                          <a
                            href="/privacidad"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-yellow-400 underline hover:text-yellow-300"
                          />
                        ),
                        req: <span className="text-yellow-500" />,
                      }}
                    />
                  </span>
                </label>
                {errors.acepta_politica && (
                  <p className="mt-1.5 ml-7 text-xs text-red-400">{err('acepta_politica')}</p>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full py-3 bg-yellow-400 hover:bg-yellow-300 disabled:opacity-60
                           text-slate-900 font-bold rounded-xl transition-all
                           flex items-center justify-center gap-2 mt-2"
              >
                {status === 'loading' ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    {t('subscribe.submitting')}
                  </>
                ) : t('subscribe.submit')}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function inputCls(hasError: boolean) {
  return `w-full bg-slate-800 border ${hasError ? 'border-red-500' : 'border-slate-700'}
          text-white text-sm rounded-lg px-3 py-2.5 placeholder-slate-500
          focus:outline-none focus:ring-2 ${hasError ? 'focus:ring-red-500/40' : 'focus:ring-yellow-500/40'}
          transition-all`;
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-400">{label}</label>
      {children}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
