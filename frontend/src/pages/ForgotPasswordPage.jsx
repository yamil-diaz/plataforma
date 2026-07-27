import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');
    
    try {
      const { data } = await axios.post(`${API}/forgot-password`, { email });
      setMessage(data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al procesar la solicitud');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="bg-[#121212] border border-white/10 p-8 rounded-2xl w-full max-w-md shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-2">Recuperar Contraseña</h1>
          <p className="text-[#A0A0A0] text-sm mb-6">Ingresa tu correo y te enviaremos un enlace para restablecer tu contraseña.</p>
          
          {message && <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-lg text-sm mb-6">{message}</div>}
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6">{error}</div>}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Correo Electrónico</label>
              <input 
                required 
                type="email" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" 
              />
            </div>
            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Enviando...' : 'Enviar enlace'}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <Link to="/login" className="text-sm text-[#A0A0A0] hover:text-white transition-colors">Volver a Iniciar Sesión</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
