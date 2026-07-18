import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, Mail, Lock, User, AlertCircle } from 'lucide-react';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(name, email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al registrarse. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] px-4 relative overflow-hidden">
      {/* Elementos Decorativos de Fondo */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#D92B2B]/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-[#D4AF37]/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md bg-[#121212] border border-white/10 p-8 rounded-2xl shadow-2xl backdrop-blur-sm relative z-10">
        
        {/* Encabezado */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#D92B2B]/20 animate-bounce">
            <Zap className="w-6 h-6 text-white fill-white" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white font-['Outfit']">Crear Cuenta</h2>
          <p className="text-sm text-[#A0A0A0] mt-2">Únete hoy y obtén 100 Rayos de regalo de bienvenida</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-950/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Nombre Completo</label>
            <div className="relative">
              <User className="absolute left-3.5 top-3.5 w-5 h-5 text-[#606060]" />
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-11 pr-4 py-3.5 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                placeholder="Tu nombre"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Correo Electrónico</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3.5 w-5 h-5 text-[#606060]" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-11 pr-4 py-3.5 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                placeholder="ejemplo@plataforma.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Contraseña</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3.5 w-5 h-5 text-[#606060]" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-11 pr-4 py-3.5 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                placeholder="Crea una contraseña segura"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3.5 rounded-lg transition-all duration-200 shadow-lg shadow-[#D92B2B]/20 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? 'Creando cuenta...' : 'Registrarse'}
          </button>
        </form>

        {/* Login Link */}
        <div className="text-center mt-6 text-sm text-[#A0A0A0]">
          ¿Ya tienes una cuenta?{' '}
          <Link to="/login" className="text-[#D92B2B] hover:underline font-semibold transition-all">
            Inicia sesión aquí
          </Link>
        </div>

      </div>
    </div>
  );
}
