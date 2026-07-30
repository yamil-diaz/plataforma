import React from 'react';
import { Navbar } from '../components/Navbar';
import { Shield, BookOpen, AlertTriangle, FileText, Gavel } from 'lucide-react';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      <div className="flex-1 max-w-4xl w-full mx-auto p-6 py-12">
        <div className="text-center mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="inline-flex items-center justify-center p-4 bg-[#D92B2B]/10 rounded-full mb-4">
            <Gavel className="w-10 h-10 text-[#D92B2B]" />
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4 uppercase">
            Términos y Condiciones
          </h1>
          <p className="text-[#A0A0A0] text-lg max-w-2xl mx-auto">
            Acuerdo legal para el uso de la plataforma AETERNUM.
          </p>
        </div>

        <div className="bg-[#121212] border border-white/10 rounded-3xl p-8 md:p-12 shadow-2xl space-y-10 text-[#CCCCCC] leading-relaxed">
          
          {/* Section 1 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <BookOpen className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">1. Naturaleza de la Plataforma</h2>
            </div>
            <p>
              AETERNUM es una plataforma diseñada estrictamente con fines de entretenimiento, lectura y competición amistosa. No somos una tienda editorial ni comercializamos con obras literarias.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Shield className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">2. Derechos de Autor y Propiedad Intelectual</h2>
            </div>
            <p>
              Todos los libros, PDFs y textos subidos a la plataforma por los usuarios deben cumplir con las leyes internacionales de derechos de autor. AETERNUM actúa únicamente como proveedor de servicios (Hosting Provider) y no se hace responsable por el contenido subido por terceros.
            </p>
            <p>
              **Queda estrictamente prohibida la venta, comercialización o distribución de material protegido con derechos de autor con fines de lucro dentro de esta plataforma.**
            </p>
            <p>
              Si eres el propietario de los derechos de autor de alguna obra publicada aquí sin tu consentimiento, por favor contacta a la administración para su retiro inmediato (DMCA Takedown).
            </p>
          </section>

          {/* Section 3 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <AlertTriangle className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">3. Economía Virtual ("Rayos") y Donaciones</h2>
            </div>
            <p>
              Los "Rayos" son la moneda virtual interna de la plataforma y **no tienen ningún valor monetario real en el mundo exterior**. No se pueden canjear por dinero fiduciario (dólares, soles, etc.) con la administración.
            </p>
            <p>
              Cualquier donación realizada hacia la plataforma a través de Yape, Plin o PayPal es un acto **completamente voluntario** para el mantenimiento de los servidores. Al realizar una donación, el usuario comprende que no está comprando un producto ni adquiriendo un servicio premium. Todas las donaciones son no-reembolsables.
            </p>
          </section>

          {/* Section 4 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <FileText className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">4. Conducta del Usuario</h2>
            </div>
            <ul className="list-disc pl-6 space-y-2">
              <li>El uso de multicuentas o bots para alterar las posiciones en los Torneos resultará en un baneo permanente.</li>
              <li>Nos reservamos el derecho de eliminar o suspender cuentas que generen un ambiente tóxico en la comunidad o violen estos términos.</li>
              <li>Cualquier intento de ataque cibernético (DDoS, inyección SQL, etc.) será reportado a las autoridades pertinentes.</li>
            </ul>
          </section>

          {/* Final Clause */}
          <div className="mt-12 p-6 bg-white/5 border border-white/10 rounded-2xl text-center">
            <p className="text-sm text-[#A0A0A0]">
              Al utilizar AETERNUM, ya sea creando una cuenta, leyendo libros o donando, aceptas íntegramente todos los términos y condiciones aquí detallados. Nos reservamos el derecho de modificar estos términos en cualquier momento.
            </p>
            <p className="text-xs text-white/40 mt-4">Última actualización: Agosto 2026</p>
          </div>

        </div>
      </div>
    </div>
  );
}
