import React from 'react';
import { Link } from 'react-router-dom';
import { Zap, Globe, CreditCard } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="border-t border-white/10 bg-[#080808] mt-16">
      <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="col-span-2 md:col-span-1">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#D92B2B] to-[#9F1239] flex items-center justify-center">
              <Zap className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="text-lg font-bold tracking-[0.15em] text-white font-['Outfit']">AETERNUM</span>
          </div>
          <p className="text-xs text-[#A0A0A0] leading-relaxed">
            La primera plataforma donde la lectura tiene recompensas.
            Compra, vende y aprende con Rayos.
          </p>
          <div className="mt-4 flex items-center gap-2 text-[11px] text-[#A0A0A0]">
            <Globe className="w-3.5 h-3.5" /> Español
            <span className="text-[#A0A0A0]">|</span>
            <CreditCard className="w-3.5 h-3.5" /> Moneda: PEN (S/)
          </div>
        </div>
        <div>
          <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-4">Plataforma</h4>
          <ul className="space-y-2.5 text-sm">
            <li><Link to="/" className="text-[#A0A0A0] hover:text-white transition-colors">Catálogo</Link></li>
            <li><Link to="/courses" className="text-[#A0A0A0] hover:text-white transition-colors">Cursos</Link></li>
            <li><Link to="/precios" className="text-[#A0A0A0] hover:text-white transition-colors">Precios</Link></li>
            <li><Link to="/forum" className="text-[#A0A0A0] hover:text-white transition-colors">Foro</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-4">Cuenta</h4>
          <ul className="space-y-2.5 text-sm">
            <li><Link to="/login" className="text-[#A0A0A0] hover:text-white transition-colors">Iniciar sesión</Link></li>
            <li><Link to="/register" className="text-[#A0A0A0] hover:text-white transition-colors">Crear cuenta</Link></li>
            <li><Link to="/mis-compras" className="text-[#A0A0A0] hover:text-white transition-colors">Mis compras</Link></li>
            <li><Link to="/forgot-password" className="text-[#A0A0A0] hover:text-white transition-colors">Recuperar contraseña</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-4">Legal y ayuda</h4>
          <ul className="space-y-2.5 text-sm">
            <li><Link to="/terminos" className="text-[#A0A0A0] hover:text-white transition-colors">Términos de uso</Link></li>
            <li><Link to="/privacidad" className="text-[#A0A0A0] hover:text-white transition-colors">Política de privacidad</Link></li>
            <li><Link to="/reembolsos" className="text-[#A0A0A0] hover:text-white transition-colors">Política de reembolsos</Link></li>
            <li><Link to="/precios" className="text-[#A0A0A0] hover:text-white transition-colors">Centro de ayuda</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/5 px-6 py-5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-[#A0A0A0]">
          <p>© {new Date().getFullYear()} AeternumLibrary. Todos los derechos reservados.</p>
          <p className="flex items-center gap-3">
            <span>Protección de compras</span>
            <span className="text-[#A0A0A0]">·</span>
            <span>Compra segura SSL</span>
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
