import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      setError("Token inválido o no encontrado.");
      return;
    }
    setLoading(true);
    setMessage('');
    setError('');
    
    try {
      const { data } = await axios.post(`${API}/reset-password`, { token, new_password: password });
      setMessage(data.message);
      setTimeout(() => navigate('/login'), 3000);
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
          <h1 className="text-2xl font-bold text-white mb-2">Nueva Contraseña</h1>
          <p className="text-[#A0A0A0] text-sm mb-6">Ingresa tu nueva contraseña para recuperar el acceso a tu cuenta.</p>
          
          {message && <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-lg text-sm mb-6">{message}</div>}
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6">{error}</div>}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Nueva Contraseña</label>
              <input 
                required 
                type="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" 
              />
            </div>
            <button 
              type="submit" 
              disabled={loading || !token}
              className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Guardando...' : 'Guardar Contraseña'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
