import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { BookOpen, ArrowLeft, Download } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function AdminGutenbergPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [bookId, setBookId] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!bookId) return;
    
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const data = new FormData();
      data.append('book_id', bookId);

      const response = await axios.post(`${API}/admin/gutenberg/fetch`, data, { 
        withCredentials: true
      });
      setSuccess(response.data.message);
      setBookId('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al importar de Gutenberg');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24 flex flex-col">
      <Navbar />
      
      <main className="flex-1 max-w-2xl mx-auto px-6 pt-12 w-full">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#A0A0A0] hover:text-white transition-colors mb-6 text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Volver al Panel
        </Link>
        
        <div className="bg-[#121212] border border-white/10 p-8 rounded-2xl shadow-2xl">
          <div className="flex items-center gap-3 mb-2">
            <BookOpen className="w-6 h-6 text-purple-500" />
            <h1 className="text-2xl font-bold text-white">Importador de Gutenberg</h1>
          </div>
          <p className="text-[#A0A0A0] text-sm mb-6">Ingresa el ID numérico de un libro en Project Gutenberg (ej. 84 para Frankenstein) y se importará automáticamente.</p>
          
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6 font-medium">{error}</div>}
          {success && <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-lg text-sm mb-6 font-medium">{success}</div>}
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Project Gutenberg Book ID</label>
              <input 
                required 
                type="number" 
                min="1"
                placeholder="Ej. 1342 (Pride and Prejudice)"
                value={bookId} 
                onChange={e => setBookId(e.target.value)} 
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none text-lg font-mono" 
              />
            </div>

            <button disabled={loading} type="submit" className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50">
              {loading ? 'Buscando y descargando...' : <><Download className="w-5 h-5" /> Importar Libro Automáticamente</>}
            </button>
          </form>
          
          <div className="mt-8 pt-6 border-t border-white/10 text-xs text-[#A0A0A0] space-y-2">
            <p><strong>Nota:</strong> Esta herramienta descarga el texto en el idioma original en el que está publicado en Gutenberg.</p>
            <p>Se importarán automáticamente el título, el autor y una portada de ejemplo.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
