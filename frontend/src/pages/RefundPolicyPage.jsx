import React from 'react';
import { Navbar } from '../components/Navbar';
import { RotateCcw, CreditCard, BookOpen, Clock, AlertTriangle, Mail } from 'lucide-react';

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      <div className="flex-1 max-w-4xl w-full mx-auto p-6 py-12">
        <div className="text-center mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="inline-flex items-center justify-center p-4 bg-[#D92B2B]/10 rounded-full mb-4">
            <RotateCcw className="w-10 h-10 text-[#D92B2B]" />
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4 uppercase">
            Política de Reembolso
          </h1>
          <p className="text-[#A0A0A0] text-lg max-w-2xl mx-auto">
            Condiciones para reembolsos en compras digitales y físicas en AETERNUM.
          </p>
        </div>

        <div className="bg-[#121212] border border-white/10 rounded-3xl p-8 md:p-12 shadow-2xl space-y-10 text-[#CCCCCC] leading-relaxed">
          
          {/* Section 1 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <BookOpen className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">1. Libros Digitales (Compra)</h2>
            </div>
            <p>
              Las compras de libros digitales en AETERNUM son <strong>no reembolsables</strong> una vez que el contenido haya sido accedido o descargado. Esto se debe a la naturaleza digital del producto, que no puede ser "devuelto" una vez entregado.
            </p>
            <p>
              Si no has accedido al contenido del libro, puedes solicitar un reembolso dentro de las primeras <strong>24 horas</strong> después de la compra.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Clock className="text-[#D4AF37] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">2. Alquileres Digitales</h2>
            </div>
            <p>
              Los alquileres digitales son <strong>no reembolsables</strong> una vez activados. El acceso temporal comienza inmediatamente después del pago y no puede pausarse ni suspenderse.
            </p>
            <p>
              Si experimentas problemas técnicos que impidan el acceso al contenido durante el periodo de alquiler, contáctanos para evaluartu caso.
            </p>
          </section>

          {/* Section 3 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <CreditCard className="text-green-400 w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">3. Libros Físicos</h2>
            </div>
            <p>
              Para libros físicos, aceptamos reembolsos o cambios bajo las siguientes condiciones:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Producto dañado o defectuoso:</strong> Solicita un reembolso o cambio dentro de los primeros <strong>7 días</strong> después de la recepción.</li>
              <li><strong>Producto incorrecto:</strong> Si recibiste un libro diferente al solicitado, lo cambiamos sin costo adicional.</li>
              <li><strong>Envío perdido:</strong> Si tu pedido no llegó dentro del tiempo estimado, investigaremos y procesaremos un reembolso completo.</li>
            </ul>
            <p className="text-[#A0A0A0] text-sm">
              Nota: Los costos de envío para devoluciones voluntarias corren por cuenta del cliente.
            </p>
          </section>

          {/* Section 4 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <AlertTriangle className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">4. Excepciones</h2>
            </div>
            <p>No se otorgan reembolsos en los siguientes casos:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Cambios de opinión después de acceder al contenido digital.</li>
              <li>Solicitudes de reembolso después de 24 horas para digitales o 7 días para físicos.</li>
              <li>Cuentas suspendidas o baneadas por violación de los Términos y Condiciones.</li>
              <li>Donaciones realizadas a la plataforma (son voluntarias y no reembolsables).</li>
              <li>Moneda virtual "Rayos" adquirida o ganada en la plataforma.</li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <RotateCcw className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">5. Proceso de Solicitud</h2>
            </div>
            <p>Para solicitar un reembolso:</p>
            <ol className="list-decimal pl-6 space-y-2">
              <li>Envía un correo a <a href="mailto:soporte@aeternumlibrary.com" className="text-[#D92B2B] hover:underline">soporte@aeternumlibrary.com</a> con tu número de orden y motivo.</li>
              <li>Nuestro equipo revisará tu solicitud dentro de 48 horas hábiles.</li>
              <li>Si es aprobado, el reembolso se procesará en un plazo de 5-10 días hábiles.</li>
              <li>El reembolso se realizará a través del mismo método de pago original.</li>
            </ol>
          </section>

          {/* Section 6 */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
              <Mail className="text-[#D92B2B] w-6 h-6" />
              <h2 className="text-2xl font-bold text-white">6. Contacto</h2>
            </div>
            <p>
              Si tienes preguntas sobre esta política de reembolso, contáctanos a:
            </p>
            <p>
              <a href="mailto:soporte@aeternumlibrary.com" className="text-[#D92B2B] hover:underline font-semibold">soporte@aeternumlibrary.com</a>
            </p>
          </section>

          {/* Final Clause */}
          <div className="mt-12 p-6 bg-white/5 border border-white/10 rounded-2xl text-center">
            <p className="text-sm text-[#A0A0A0]">
              Esta política de reembolso puede actualizarse. Los cambios no se aplicarán retroactivamente a compras ya realizadas.
            </p>
            <p className="text-xs text-white/40 mt-4">Última actualización: Agosto 2026</p>
          </div>

        </div>
      </div>
    </div>
  );
}
