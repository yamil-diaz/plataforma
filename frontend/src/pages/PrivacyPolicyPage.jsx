import React from 'react';
import { Navbar } from '../components/Navbar';
import { Shield, Eye, Lock, Database, Mail, UserCheck } from 'lucide-react';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      <div className="flex-1 max-w-4xl w-full mx-auto p-6 py-12">
        <div className="text-center mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="inline-flex items-center justify-center p-4 bg-[#D92B2B]/10 rounded-full mb-4">
            <Shield className="w-10 h-10 text-[#D92B2B]" />
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4 uppercase">
            Política de Privacidad
          </h1>
          <p className="text-[#A0A0A0] text-lg max-w-2xl mx-auto">
            Cómo AETERNUM recopila, usa y protege tu información personal.
          </p>
        </div>

        <div className="bg-[#121212] border border-white/10 rounded-3xl p-8 md:p-12 shadow-2xl space-y-10 text-[#CCCCCC] leading-relaxed">
          
          {/* Section 1 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Database className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">1. Información que Recopilamos</h2>
            </div>
            <p>Al usar AETERNUM, recopilamos la siguiente información:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Datos de registro:</strong> nombre, correo electrónico, contraseña (encriptada) y fecha de nacimiento.</li>
              <li><strong>Datos de perfil:</strong> foto de perfil, biografía y configuración de idioma.</li>
              <li><strong>Datos de lectura:</strong> libros leídos, tiempo de lectura, progreso, reseñas y calificaciones.</li>
              <li><strong>Datos de compras:</strong> historial de transacciones, métodos de pago (procesados por terceros seguros como Paddle, Culqi y Flow).</li>
              <li><strong>Datos de uso:</strong> dirección IP, tipo de navegador, dispositivo y páginas visitadas.</li>
            </ul>
          </section>

          {/* Section 2 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Eye className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">2. Cómo Usamos tu Información</h2>
            </div>
            <p>Utilizamos tu información para:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Proveer y mejorar los servicios de la plataforma (lectura, torneos, cursos, foro).</li>
              <li>Procesar transacciones de compra y alquiler de libros digitales y físicos.</li>
              <li>Enviarte notificaciones sobre tu cuenta, compras y actividad de la plataforma.</li>
              <li>Generar estadísticas de lectura y-ranking de usuarios.</li>
              <li>Prevenir fraudes y garantizar la seguridad de la plataforma.</li>
              <li>Cumplir con obligaciones legales.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Lock className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">3. Protección de Datos</h2>
            </div>
            <p>
              Implementamos medidas de seguridad técnicas y organizativas para proteger tu información personal contra acceso no autorizado, alteración, divulgación o destrucción. Estas incluyen:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Encriptación de contraseñas con bcrypt.</li>
              <li>Conexiones HTTPS/SSL en toda la plataforma.</li>
              <li>Acceso restringido a datos personales solo al personal autorizado.</li>
              <li>Monitoreoregular de vulnerabilidades de seguridad.</li>
            </ul>
          </section>

          {/* Section 4 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <UserCheck className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">4. Compartir Información</h2>
            </div>
            <p>
              No vendemos ni compartimos tu información personal con terceros, excepto en los siguientes casos:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Proveedores de pago:</strong> Paddle, Culqi y Flow reciben los datos necesarios para procesar tus transacciones.</li>
              <li><strong>Servicios de autenticación:</strong> Google OAuth recibe tu nombre y correo electrónico si inicias sesión con Google.</li>
              <li><strong>Obligaciones legales:</strong> Cuando lo requiera la ley o una orden judicial.</li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Mail className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">5. Tus Derechos</h2>
            </div>
            <p>Tienes derecho a:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Acceder a tus datos personales almacenados.</li>
              <li>Solicitar la corrección de datos inexactos.</li>
              <li>Solicitar la eliminación de tu cuenta y datos personales.</li>
              <li>Oponerte al procesamiento de tus datos para fines de marketing.</li>
              <li>Exportar tus datos en un formato estructurado.</li>
            </ul>
            <p>
              Para ejercer estos derechos, contáctanos a <a href="mailto:soporte@aeternumlibrary.com" className="text-[#D92B2B] hover:underline">soporte@aeternumlibrary.com</a>.
            </p>
          </section>

          {/* Section 6 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Database className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">6. Retención de Datos</h2>
            </div>
            <p>
              Conservamos tu información personal mientras tu cuenta esté activa. Si eliminas tu cuenta, tus datos serán eliminados de nuestros sistemas activos dentro de los 30 días, aunque podríamos conservar ciertos datos por razones legales o de auditoría.
            </p>
          </section>

          {/* Section 7 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Shield className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">7. Cookies</h2>
            </div>
            <p>
              AETERNUM utiliza cookies esenciales para el funcionamiento de la plataforma (autenticación, preferencias de usuario). No utilizamos cookies de rastreo publicitario de terceros.
            </p>
          </section>

          {/* Final Clause */}
          <div className="mt-12 p-6 bg-white/5 border border-white/10 rounded-2xl text-center">
            <p className="text-sm text-[#A0A0A0]">
              Esta política de privacidad puede actualizarse periodicamente. Te notificaremos de cambios significativos a través de la plataforma o por correo electrónico.
            </p>
            <p className="text-xs text-white/40 mt-4">Última actualización: Agosto 2026</p>
          </div>

        </div>
      </div>
    </div>
  );
}
