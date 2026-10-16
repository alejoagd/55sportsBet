import { Link } from 'react-router-dom';

const RESPONSABLE = 'Alejandro Gaviria Diaz';
const CORREO = 'agdsports55@gmail.com';
const VIGENCIA = '15 de octubre de 2026';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <div className="text-sm leading-relaxed text-slate-300 space-y-2">{children}</div>
    </section>
  );
}

export default function PrivacyPolicy() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <Link to="/" className="text-xs text-slate-400 hover:text-white">← Volver a 55sports Stats</Link>
        <h1 className="mt-3 text-2xl sm:text-3xl font-bold text-white">Política de Privacidad</h1>
        <p className="mt-1 text-xs text-slate-500">Vigente desde el {VIGENCIA}</p>
      </div>

      <Section title="1. Responsable del tratamiento">
        <p>
          <strong className="text-slate-200">{RESPONSABLE}</strong>, titular de la plataforma 55sports Stats
          (en adelante, "55sports Stats"), es el responsable del tratamiento de los datos personales
          descritos en esta política, conforme a la Ley 1581 de 2012, el Decreto 1377 de 2013 y las
          demás normas que los modifiquen o complementen.
        </p>
        <p>Contacto para consultas, reclamos y ejercicio de derechos: <strong className="text-slate-200">{CORREO}</strong></p>
      </Section>

      <Section title="2. Qué datos recolectamos">
        <p>
          Únicamente cuando te suscribes de forma voluntaria: nombre, apellido, correo electrónico,
          teléfono, país y ciudad. No recolectamos datos sensibles ni solicitamos contraseñas,
          datos bancarios ni medios de pago.
        </p>
        <p>
          Además, usamos analítica web (Vercel Web Analytics) que registra métricas de uso agregadas
          del sitio, como páginas visitadas y tipo de dispositivo, para entender y mejorar la plataforma.
        </p>
      </Section>

      <Section title="3. Para qué usamos tus datos">
        <ul className="list-disc pl-5 space-y-1">
          <li>Gestionar tu suscripción a 55sports Stats.</li>
          <li>Enviarte información sobre predicciones, resultados, análisis y novedades de la plataforma.</li>
          <li>Responder tus consultas y solicitudes.</li>
          <li>Mejorar el contenido y el funcionamiento del servicio.</li>
        </ul>
        <p>No vendemos ni cedemos tus datos a terceros con fines comerciales.</p>
      </Section>

      <Section title="4. Autorización">
        <p>
          El tratamiento se realiza con tu autorización previa, expresa e informada, que otorgas
          al marcar la casilla del formulario de suscripción. Puedes revocarla en cualquier momento
          escribiendo a {CORREO}.
        </p>
      </Section>

      <Section title="5. Tus derechos">
        <p>Como titular de los datos tienes derecho a:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Conocer, actualizar y rectificar tus datos personales.</li>
          <li>Solicitar prueba de la autorización otorgada.</li>
          <li>Ser informado sobre el uso que se ha dado a tus datos.</li>
          <li>Revocar la autorización y/o solicitar la supresión de tus datos.</li>
          <li>Presentar quejas ante la Superintendencia de Industria y Comercio (SIC).</li>
          <li>Acceder de forma gratuita a tus datos personales.</li>
        </ul>
        <p>
          Para ejercerlos, escribe a {CORREO} indicando tu nombre y correo de suscripción. Las
          consultas se responden en un máximo de 10 días hábiles y los reclamos en un máximo de
          15 días hábiles, prorrogables en los términos de la ley.
        </p>
      </Section>

      <Section title="6. Dónde se almacenan los datos">
        <p>
          La infraestructura de 55sports Stats (servidor, base de datos y sitio web) está alojada con
          proveedores de servicios en la nube ubicados en Estados Unidos. Esto implica una
          transmisión internacional de datos, que se realiza con proveedores que aplican medidas de
          seguridad adecuadas.
        </p>
      </Section>

      <Section title="7. Seguridad y conservación">
        <p>
          Aplicamos medidas técnicas y administrativas razonables para proteger tus datos contra
          acceso no autorizado, pérdida o alteración. Los conservamos mientras tu suscripción esté
          activa o hasta que solicites su supresión.
        </p>
      </Section>

      <Section title="8. Menores de edad">
        <p>
          55sports Stats está dirigida a mayores de 18 años. No recolectamos intencionalmente datos de
          menores de edad; si detectamos que se registró un menor, eliminaremos sus datos.
        </p>
      </Section>

      <Section title="9. Naturaleza informativa y marcas de terceros">
        <p>
          55sports Stats es una plataforma informativa y de análisis estadístico. No es una casa de
          apuestas, no recibe ni gestiona apuestas ni dinero, y sus predicciones son estimaciones
          que no garantizan resultados.
        </p>
        <p>
          Los nombres, escudos y marcas de equipos y competiciones pertenecen a sus respectivos
          propietarios. 55sports Stats es independiente y no está afiliada ni respaldada por ellos.
        </p>
      </Section>

      <Section title="10. Cambios a esta política">
        <p>
          Podemos actualizar esta política. La versión vigente estará siempre publicada en esta
          página, con su fecha de vigencia.
        </p>
      </Section>
    </div>
  );
}
