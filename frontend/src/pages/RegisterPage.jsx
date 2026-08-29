import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { sanitizeRef } from '../utils/ref';
import { Zap, Mail, Lock, User, AlertCircle, Chrome, Loader2 } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Parámetro ?ref= del QR: se valida solo el formato; si no cumple se trata
  // como inexistente (null) y el registro continúa normal. Se conserva en el
  // estado de React durante toda la interacción con el formulario.
  const ref = sanitizeRef(searchParams.get('ref'));

  // Tracking de visita (FASE 5): una sola petición por montaje de la página,
  // solo si hay un ref válido. Best effort: si falla, tarda o el QR no existe,
  // el registro continúa normal; nunca se muestran errores al usuario.
  useEffect(() => {
    if (!ref) return;
    const controller = new AbortController();
    axios
      .post(`${API}/qr/${ref}/visit`, null, { signal: controller.signal })
      .catch(() => {});
    return () => controller.abort();
  }, [ref]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(name, email, password, ref);
      navigate('/');
    } catch (err) {
      // Si el backend requiere verificación, redirigir a la página de verificación
      if (err.response?.data?.requires_verification) {
        navigate('/verify-email', { state: { email: err.response.data.email, user_id: err.response.data.user_id } });
        return;
      }
      setError(err.response?.data?.detail || 'Error al registrarse. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setGoogleLoading(true);
    try {
      // Obtener URL de autorización de Google
      const { data } = await axios.get(`${API}/auth/google`);
      // Redirigir a Google OAuth
      window.location.href = data.auth_url;
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión con Google');
      setGoogleLoading(false);
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

        {/* Botón Google OAuth */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={loading || googleLoading}
          className="w-full flex items-center justify-center gap-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold py-3.5 rounded-lg transition-all duration-200 disabled:opacity-50 mb-6"
        >
          <Chrome className="w-5 h-5" />
          <span>{googleLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Continuar con Google'}</span>
        </button>

        {/* Separador */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-[#121212] text-[#A0A0A0]">o regístrate con correo</span>
          </div>
        </div>

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

          <p className="text-xs text-[#A0A0A0] mt-4 mb-4 text-center">
            Al registrarte, aceptas nuestros <Link to="/terminos" className="text-[#D92B2B] hover:underline">Términos y Condiciones</Link>.
          </p>

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
