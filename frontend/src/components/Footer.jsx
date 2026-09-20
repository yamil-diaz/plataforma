import React from 'react';
import { Link } from 'react-router-dom';
import { Mail, BookOpen, Heart } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="bg-[#0A0A0A] border-t border-white/5 mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-[#D92B2B]" />
              <span className="text-xl font-bold text-white font-['Outfit']">AETERNUM</span>
            </div>
            <p className="text-[#A0A0A0] text-sm">
              La primera plataforma donde la lectura tiene recompensas.
            </p>
          </div>

          {/* Legal */}
          <div className="space-y-4">
            <h3 className="text-white font-semibold text-sm uppercase tracking-wider">Legal</h3>
            <ul className="space-y-2">
              <li>
                <Link to="/terminos" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Términos y Condiciones
                </Link>
              </li>
              <li>
                <Link to="/privacidad" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Política de Privacidad
                </Link>
              </li>
              <li>
                <Link to="/reembolsos" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Política de Reembolso
                </Link>
              </li>
            </ul>
          </div>

          {/* Plataforma */}
          <div className="space-y-4">
            <h3 className="text-white font-semibold text-sm uppercase tracking-wider">Plataforma</h3>
            <ul className="space-y-2">
              <li>
                <Link to="/" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Catálogo
                </Link>
              </li>
              <li>
                <Link to="/courses" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Cursos
                </Link>
              </li>
              <li>
                <Link to="/competitions" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Competencias
                </Link>
              </li>
              <li>
                <Link to="/forum" className="text-[#A0A0A0] hover:text-white text-sm transition-colors">
                  Foro
                </Link>
              </li>
            </ul>
          </div>

          {/* Contacto */}
          <div className="space-y-4">
            <h3 className="text-white font-semibold text-sm uppercase tracking-wider">Contacto</h3>
            <ul className="space-y-2">
              <li>
                <a href="mailto:soporte@aeternumlibrary.com" className="text-[#A0A0A0] hover:text-white text-sm transition-colors flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  soporte@aeternumlibrary.com
                </a>
              </li>
            </ul>
          </div>

        </div>

        {/* Bottom */}
        <div className="border-t border-white/5 mt-8 pt-8 text-center">
          <p className="text-[#606060] text-sm flex items-center justify-center gap-1">
            Hecho con <Heart className="w-3 h-3 text-[#D92B2B] fill-[#D92B2B]" /> por AETERNUM &copy; {new Date().getFullYear()}
          </p>
        </div>
      </div>
    </footer>
  );
};
