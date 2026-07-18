import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, LogOut, Upload, BookOpen, Layers } from 'lucide-react';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Error al cerrar sesión:', error);
    }
  };

  return (
    <nav className="bg-[#0A0A0A]/80 border-b border-white/10 backdrop-blur-md sticky top-0 z-40 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 hover:opacity-90 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-[#D92B2B] flex items-center justify-center shadow-lg shadow-[#D92B2B]/20">
            <Zap className="w-5 h-5 text-white fill-white" />
          </div>
          <span className="text-xl font-bold tracking-wider text-white font-['Outfit']">RAYOS</span>
        </Link>

        {/* Enlaces de Navegación */}
        <div className="flex items-center gap-6">
          <Link to="/" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" />
            Catálogo
          </Link>

          {user && user.role === 'admin' && (
            <>
              <Link to="/admin/new-book" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
                <Upload className="w-4 h-4" />
                Subir Libro
              </Link>
              <Link to="/admin/import" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
                <Layers className="w-4 h-4" />
                Importar ZIP
              </Link>
            </>
          )}
        </div>

        {/* Autenticación / Perfil */}
        <div className="flex items-center gap-6">
          {user ? (
            <div className="flex items-center gap-6">
              {/* Balance de Rayos */}
              <div className="flex items-center gap-2 px-3.5 py-1.5 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-full text-xs font-semibold text-[#D4AF37] tracking-wider uppercase animate-pulse">
                <Zap className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                <span>{user.rayos_balance} Rayos</span>
              </div>

              {/* Nombre de Usuario */}
              <span className="text-sm text-[#F5F5F5] font-medium hidden sm:inline">{user.name}</span>

              {/* Cerrar Sesión */}
              <button
                onClick={handleLogout}
                className="p-2 text-[#A0A0A0] hover:text-[#D92B2B] hover:bg-[#D92B2B]/5 rounded-lg transition-all duration-200"
                title="Cerrar Sesión"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors">
                Iniciar Sesión
              </Link>
              <Link to="/register" className="bg-[#D92B2B] text-white hover:bg-[#F03C3C] text-sm font-medium px-4 py-2 rounded-md transition-colors shadow-md shadow-[#D92B2B]/10">
                Registrarse
              </Link>
            </div>
          )}
        </div>

      </div>
    </nav>
  );
};
