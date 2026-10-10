import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, Mail, Lock, AlertCircle, Chrome, Loader2 } from 'lucide-react';
import { formatApiError } from '../utils/apiError';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      const returnTo = location.state?.from;
      if (returnTo) {
        navigate(returnTo.pathname + (returnTo.search || ''), { replace: true });
      } else {
        navigate('/');
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 429) {
        setError(typeof detail === 'string' ? detail : 'Demasiados intentos. Espera un momento y vuelve a intentar.');
      } else if (err?.response?.status === 400) {
        setError(typeof detail === 'string' ? detail : 'Correo o contraseña incorrectos. Si te registraste con Google, usa el botón de Google.');
      } else {
        setError(formatApiError(err, 'Error al iniciar sesión. Revisa tus credenciales.'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setGoogleLoading(true);
    try {
      const { data } = await axios.get(`${API}/auth/google`);
      window.location.href = data.auth_url;
    } catch (err) {
      setError(formatApiError(err, 'Error al iniciar sesión con Google'));
      setGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] px-4 relative overflow-hidden">
      <div className="w-full max-w-md bg-[#121212] border border-white/10 p-8 rounded-2xl relative z-10">

        {/* Encabezado */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4">
            <Zap className="w-6 h-6 text-white fill-white" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white font-['Outfit']">Bienvenido de nuevo</h2>
          <p className="text-sm text-[#A0A0A0] mt-2">Inicia sesión para acumular Rayos mientras lees</p>
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
            <span className="px-4 bg-[#121212] text-[#A0A0A0]">o inicia sesión con correo</span>
          </div>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="login-email" className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Correo Electrónico</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3.5 w-5 h-5 text-[#A0A0A0]" />
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="ae-input w-full pl-11 pr-4 py-3.5 text-[#F5F5F5] placeholder-[#707070]"
                placeholder="ejemplo@plataforma.com"
              />
            </div>
          </div>

          <div>
            <label htmlFor="login-password" className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Contraseña</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3.5 w-5 h-5 text-[#A0A0A0]" />
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="ae-input w-full pl-11 pr-4 py-3.5 text-[#F5F5F5] placeholder-[#707070]"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="ae-btn ae-btn-primary w-full py-3.5 disabled:opacity-50"
          >
            {loading ? 'Iniciando sesión...' : 'Ingresar'}
          </button>
        </form>

        <div className="mt-8 flex flex-col gap-4 text-center">
          <Link to="/forgot-password" className="text-sm text-[#A0A0A0] hover:text-white transition-colors">
            ¿Olvidaste tu contraseña?
          </Link>
          <p className="text-[#A0A0A0] text-sm">
            ¿No tienes una cuenta?{' '}
            <Link to="/register" className="text-[#D92B2B] hover:text-[#F03C3C] font-semibold transition-colors">
              Regístrate
            </Link>
          </p>
        </div>

      </div>
    </div>
  );
}
