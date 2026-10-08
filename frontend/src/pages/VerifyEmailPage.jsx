import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Zap, Mail, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { formatApiError } from '../utils/apiError';
import { useAuth } from '../contexts/AuthContext';

const API = import.meta.env.VITE_API_URL || '/api';

export default function VerifyEmailPage() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const { completeAuth } = useAuth();

  // Obtener email del state, query params o sessionStorage (si refresca la página)
  const email =
    location.state?.email ||
    new URLSearchParams(location.search).get('email') ||
    (() => {
      try { return sessionStorage.getItem('pending_verify_email'); } catch { return null; }
    })();
  const userId = location.state?.user_id || new URLSearchParams(location.search).get('user_id');

  useEffect(() => {
    if (!email) {
      navigate('/register');
    }
  }, [email, navigate]);

  // Countdown timer para reenvío
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (code.length !== 6) {
      setError('El código debe tener 6 dígitos');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/verify-email`, { email, code });
      // CRITICAL: el backend setea cookies, pero React sigue sin user
      // hasta que actualizamos el contexto. Sin esto, el navbar muestra
      // "Crear cuenta" y el usuario cree que debe registrarse de nuevo.
      completeAuth({
        id: data.id || data._id,
        _id: data._id || data.id,
        email: data.email,
        name: data.name,
        role: data.role || 'user',
        rayos_balance: data.rayos_balance ?? 0,
      });
      try {
        sessionStorage.removeItem('pending_verify_email');
        sessionStorage.removeItem('pending_verify_user_id');
      } catch (_) {}
      setMessage(data.message || 'Correo verificado. Bienvenido a AETERNUM!');
      setTimeout(() => navigate('/', { replace: true }), 1200);
    } catch (err) {
      setError(formatApiError(err, 'Error al verificar el código'));
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0) return;
    setError('');
    setMessage('');
    setResending(true);
    try {
      await axios.post(`${API}/resend-verification`, { email });
      setMessage('Nuevo código enviado a tu correo');
      setCountdown(60); // 60 segundos de espera
    } catch (err) {
      setError(formatApiError(err, 'Error al reenviar el código'));
    } finally {
      setResending(false);
    }
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
    if (value.length === 6) {
      handleSubmit(e);
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
          <div className="w-12 h-12 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4">
            <Mail className="w-6 h-6 text-white fill-white" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white font-['Outfit']">Verifica tu Correo</h2>
          <p className="text-sm text-[#A0A0A0] mt-2">
            Hemos enviado un código de 6 dígitos a <span className="text-white font-medium">{email}</span>
          </p>
        </div>

        {/* Error/Success Alerts */}
        {error && (
          <div className="mb-6 p-4 bg-red-950/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {message && (
          <div className="mb-6 p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-lg flex items-start gap-3 text-emerald-400 text-sm">
            <Zap className="w-5 h-5 shrink-0" />
            <span>{message}</span>
          </div>
        )}

        {/* Input de código */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="flex gap-3 justify-center">
            {[...Array(6)].map((_, i) => (
              <input
                key={i}
                type="text"
                maxLength={1}
                value={code[i] || ''}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '');
                  const newCode = code.split('');
                  newCode[i] = value;
                  setCode(newCode.join(''));
                  // Auto-focus next input
                  if (value && i < 5) {
                    e.target.nextElementSibling?.focus();
                  }
                  if (!value && i > 0) {
                    e.target.previousElementSibling?.focus();
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Backspace' && !code[i] && i > 0) {
                    e.target.previousElementSibling?.focus();
                  }
                }}
                className="w-10 h-14 bg-[#0A0A0A] border border-white/10 rounded-lg text-2xl text-center text-white focus:outline-none focus:border-[#D92B2B] transition-colors"
                autoComplete="one-time-code"
                inputMode="numeric"
              />
            ))}
          </div>

          <button
            type="submit"
            disabled={loading || code.length !== 6}
            className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Verificando...
              </>
            ) : (
              'Verificar Código'
            )}
          </button>
        </form>

        {/* Reenviar código */}
        <div className="mt-6 text-center">
          <p className="text-sm text-[#A0A0A0]">
            ¿No recibiste el código?{' '}
            <button
              onClick={handleResend}
              disabled={resending || countdown > 0}
              className="text-[#D92B2B] hover:underline font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {countdown > 0 ? (
                `Reenviar en ${countdown}s`
              ) : resending ? (
                'Enviando...'
              ) : (
                'Reenviar código'
              )}
            </button>
          </p>
        </div>

        <div className="text-center mt-4 text-sm text-[#A0A0A0]">
          <p>¿Registro incorrecto?{' '}</p>
          <button
            onClick={() => navigate('/register')}
            className="text-[#D92B2B] hover:underline font-semibold transition-all"
          >
            Volver al registro
          </button>
        </div>

      </div>
    </div>
  );
}