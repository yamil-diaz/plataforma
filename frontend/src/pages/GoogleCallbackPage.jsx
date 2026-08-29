import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Zap, Loader2, AlertCircle } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function GoogleCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  useEffect(() => {
    const handleCallback = async () => {
      if (error) {
        console.error('Google OAuth error:', error);
        navigate('/register?error=google_oauth_failed');
        return;
      }

      if (!code) {
        navigate('/register?error=no_code');
        return;
      }

      try {
        const { data } = await axios.post(`${API}/auth/google/callback`, { code });
        // Login successful - user is already set in cookies
        navigate('/');
      } catch (err) {
        console.error('Google callback error:', err);
        navigate('/register?error=google_callback_failed');
      }
    };

    handleCallback();
  }, [code, error, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] px-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#D92B2B]/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-[#D4AF37]/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md bg-[#121212] border border-white/10 p-8 rounded-2xl shadow-2xl backdrop-blur-sm relative z-10 text-center">
        <div className="w-12 h-12 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#D92B2B]/20 animate-pulse">
          <Zap className="w-6 h-6 text-white fill-white" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white font-['Outfit'] mb-2">Conectando con Google...</h2>
        <p className="text-sm text-[#A0A0A0]">Por favor espera mientras completamos el inicio de sesión</p>
        <Loader2 className="w-8 h-8 mx-auto mt-6 animate-spin text-[#D92B2B]" />
      </div>
    </div>
  );
}