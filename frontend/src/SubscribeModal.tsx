import { useState } from 'react';

const PAISES = [
  'Alemania', 'Argentina', 'Australia', 'Austria',
  'Bélgica', 'Bolivia', 'Brasil',
  'Canadá', 'Chile', 'Colombia', 'Costa Rica', 'Croacia', 'Cuba',
  'Dinamarca',
  'Ecuador', 'El Salvador', 'Escocia', 'Eslovaquia', 'Eslovenia', 'España', 'Estados Unidos',
  'Francia',
  'Gales', 'Grecia', 'Guatemala',
  'Holanda', 'Honduras', 'Hungría',
  'Inglaterra', 'Irlanda', 'Italia',
  'Japón',
  'Marruecos', 'México',
  'Nicaragua', 'Noruega',
  'Panamá', 'Paraguay', 'Perú', 'Polonia', 'Portugal', 'Puerto Rico',
  'República Checa', 'República Dominicana', 'Rumanía', 'Rusia',
  'Serbia', 'Suecia', 'Suiza',
  'Turquía',
  'Ucrania', 'Uruguay',
  'Venezuela',
  'Otro',
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

const EMPTY: FormData = {
  nombre: '', apellido: '', correo: '',
  telefono: '', pais: '', ciudad: '', acepta_politica: false,
};

function validate(f: FormData): Partial<Record<keyof FormData, string>> {
  const e: Partial<Record<keyof FormData, string>> = {};
  if (!f.nombre.trim())   e.nombre   = 'Campo obligatorio';
  if (!f.apellido.trim()) e.apellido = 'Campo obligatorio';
  if (!f.correo.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.correo))
    e.correo = 'Correo inválido';
  if (!f.telefono.trim() || !/^\+?[\d\s\-()]{7,}$/.test(f.telefono))
    e.telefono = 'Teléfono inválido';
  if (!f.pais.trim())     e.pais     = 'Selecciona un país';
  if (!f.ciudad.trim())   e.ciudad   = 'Campo obligatorio';
  if (!f.acepta_politica) e.acepta_politica = 'Debes aceptar para continuar';
  return e;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SubscribeModal({ isOpen, onClose }: Props) {
  const [form, setForm] = useState<FormData>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [serverMsg, setServerMsg] = useState('');

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
      const data = await res.json();
      if (res.ok) {
        setStatus('success');
        setServerMsg(data.message);
      } else {
        setStatus('error');
        setServerMsg(data.detail || 'Ocurrió un error. Intenta de nuevo.');
      }
    } catch {
      setStatus('error');
      setServerMsg('No se pudo conectar. Verifica tu conexión.');
    }
  };

  const handleClose = () => {
    setForm(EMPTY);
    setErrors({});
    setStatus('idle');
    setServerMsg('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-yellow-500 to-amber-600 px-6 py-5">
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-slate-900/70 hover:text-slate-900 transition-colors"
            aria-label="Cerrar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <span className="text-3xl">🏆</span>
            <div>
              <h2 className="text-slate-900 font-bold text-lg leading-tight">Suscríbete al Mundial</h2>
              <p className="text-slate-800 text-xs mt-0.5">Recibe predicciones y noticias exclusivas</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {status === 'success' ? (
            <div className="flex flex-col items-center gap-4 py-6 text-center">
              <div className="text-6xl">🎉</div>
              <p className="text-white font-semibold text-lg">{serverMsg}</p>
              <p className="text-slate-400 text-sm">
                Te enviaremos predicciones, análisis y las mejores apuestas del Mundial 2026.
              </p>
              <button
                onClick={handleClose}
                className="mt-2 px-6 py-2.5 bg-yellow-400 text-slate-900 font-semibold rounded-xl hover:bg-yellow-300 transition-colors"
              >
                ¡Entendido!
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {status === 'error' && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
                  {serverMsg}
                </div>
              )}

              {/* Nombre + Apellido */}
              <div className="grid grid-cols-2 gap-3">
                <Field label="Nombre" error={errors.nombre}>
                  <input
                    type="text" placeholder="Ej: Juan"
                    value={form.nombre} onChange={set('nombre')}
                    className={inputCls(!!errors.nombre)}
                  />
                </Field>
                <Field label="Apellido" error={errors.apellido}>
                  <input
                    type="text" placeholder="Ej: Pérez"
                    value={form.apellido} onChange={set('apellido')}
                    className={inputCls(!!errors.apellido)}
                  />
                </Field>
              </div>

              {/* Correo */}
              <Field label="Correo electrónico" error={errors.correo}>
                <input
                  type="email" placeholder="correo@ejemplo.com"
                  value={form.correo} onChange={set('correo')}
                  className={inputCls(!!errors.correo)}
                />
              </Field>

              {/* Teléfono */}
              <Field label="Teléfono" error={errors.telefono}>
                <input
                  type="tel" placeholder="+57 300 000 0000"
                  value={form.telefono} onChange={set('telefono')}
                  className={inputCls(!!errors.telefono)}
                />
              </Field>

              {/* País + Ciudad */}
              <div className="grid grid-cols-2 gap-3">
                <Field label="País" error={errors.pais}>
                  <select
                    value={form.pais} onChange={setSelect('pais')}
                    className={`${inputCls(!!errors.pais)} cursor-pointer`}
                  >
                    <option value="">Seleccionar...</option>
                    {PAISES.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Ciudad" error={errors.ciudad}>
                  <input
                    type="text" placeholder="Ej: Bogotá"
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
                    Autorizo el tratamiento de mis datos personales conforme a la{' '}
                    <strong className="text-slate-300">Ley 1581 de 2012</strong> (Colombia) y
                    acepto recibir comunicaciones de 55sportsBet relacionadas con el Mundial 2026.{' '}
                    <span className="text-yellow-500">*Obligatorio</span>
                  </span>
                </label>
                {errors.acepta_politica && (
                  <p className="mt-1.5 ml-7 text-xs text-red-400">{errors.acepta_politica}</p>
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
                    Registrando...
                  </>
                ) : '¡Suscribirme ahora!'}
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
