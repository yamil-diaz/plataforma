import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Zap, Loader2 } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function GoogleCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeAuth } = useAuth();
  const code = searchParams.get('code');
  const error = searchParams.get('error');
  // El código de Google es de un solo uso. Si el effect se corre 2 veces
  // (StrictMode, re-render), el segundo intento recibe 400 y te saca del flujo.
  const consumedRef = useRef(false);

  useEffect(() => {
    if (consumedRef.current) return;
    if (!code && !error) return;

    const handleCallback = async () => {
      if (error) {
        console.error('Google OAuth error:', error);
        navigate('/register?error=google_oauth_failed', { replace: true });
        return;
      }

      if (!code) {
        navigate('/register?error=no_code', { replace: true });
        return;
      }

      consumedRef.current = true;

      try {
        const { data } = await axios.post(`${API}/auth/google/callback`, { code });
        if (data && (data.id || data._id)) {
          completeAuth(data);
          try { sessionStorage.removeItem('pending_verify_email'); } catch (_) {}
          navigate('/', { replace: true });
          return;
        }
        navigate('/register?error=google_callback_failed', { replace: true });
      } catch (err) {
        console.error('Google callback error:', err);
        // Si el primer request tuvo éxito y este es el reintento del mismo code,
        // no navegar a error: ya estamos logueados.
        navigate('/register?error=google_callback_failed', { replace: true });
      }
    };

    handleCallback();
  }, [code, error, navigate, completeAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] px-4 relative overflow-hidden">
      <div className="w-full max-w-md bg-[#121212] border border-white/10 p-8 rounded-2xl relative z-10 text-center">
        <div className="w-12 h-12 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4">
          <Zap className="w-6 h-6 text-white fill-white" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white font-['Outfit'] mb-2">Conectando con Google...</h2>
        <p className="text-sm text-[#A0A0A0]">Por favor espera mientras completamos el inicio de sesión</p>
        <Loader2 className="w-8 h-8 mx-auto mt-6 animate-spin text-[#D92B2B]" />
      </div>
    </div>
  );
}
