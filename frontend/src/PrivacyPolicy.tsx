import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { localeTag } from './i18n';

const RESPONSABLE = 'Alejandro Gaviria Diaz';
const CORREO = 'agdsports55@gmail.com';
const VIGENCIA = new Date(2026, 9, 15); // 15 de octubre de 2026

const bold = { b: <strong className="text-slate-200" /> };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <div className="text-sm leading-relaxed text-slate-300 space-y-2">{children}</div>
    </section>
  );
}

function List({ keys }: { keys: string[] }) {
  const { t } = useTranslation();
  return (
    <ul className="list-disc pl-5 space-y-1">
      {keys.map(k => <li key={k}>{t(k)}</li>)}
    </ul>
  );
}

export default function PrivacyPolicy() {
  const { t } = useTranslation();
  const values = { owner: RESPONSABLE, email: CORREO };
  const date = VIGENCIA.toLocaleDateString(localeTag(), { day: 'numeric', month: 'long', year: 'numeric' });

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <Link to="/" className="text-xs text-slate-400 hover:text-white">{t('privacy.back')}</Link>
        <h1 className="mt-3 text-2xl sm:text-3xl font-bold text-white">{t('privacy.title')}</h1>
        <p className="mt-1 text-xs text-slate-500">{t('privacy.validSince', { date })}</p>
      </div>

      <Section title={t('privacy.s1.title')}>
        <p><Trans i18nKey="privacy.s1.p1" values={values} components={bold} /></p>
        <p><Trans i18nKey="privacy.s1.p2" values={values} components={bold} /></p>
      </Section>

      <Section title={t('privacy.s2.title')}>
        <p>{t('privacy.s2.p1')}</p>
        <p>{t('privacy.s2.p2')}</p>
      </Section>

      <Section title={t('privacy.s3.title')}>
        <List keys={['privacy.s3.i1', 'privacy.s3.i2', 'privacy.s3.i3', 'privacy.s3.i4']} />
        <p>{t('privacy.s3.p1')}</p>
      </Section>

      <Section title={t('privacy.s4.title')}>
        <p>{t('privacy.s4.p1', values)}</p>
      </Section>

      <Section title={t('privacy.s5.title')}>
        <p>{t('privacy.s5.p1')}</p>
        <List keys={['privacy.s5.i1', 'privacy.s5.i2', 'privacy.s5.i3', 'privacy.s5.i4', 'privacy.s5.i5', 'privacy.s5.i6']} />
        <p>{t('privacy.s5.p2', values)}</p>
      </Section>

      <Section title={t('privacy.s6.title')}>
        <p>{t('privacy.s6.p1')}</p>
      </Section>

      <Section title={t('privacy.s7.title')}>
        <p>{t('privacy.s7.p1')}</p>
      </Section>

      <Section title={t('privacy.s8.title')}>
        <p>{t('privacy.s8.p1')}</p>
      </Section>

      <Section title={t('privacy.s9.title')}>
        <p>{t('privacy.s9.p1')}</p>
        <p>{t('privacy.s9.p2')}</p>
      </Section>

      <Section title={t('privacy.s10.title')}>
        <p>{t('privacy.s10.p1')}</p>
      </Section>
    </div>
  );
}
