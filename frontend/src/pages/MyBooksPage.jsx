import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { BookOpen, Clock, Zap, Lock } from 'lucide-react';

export default function MyBooksPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [entitlements, setEntitlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadEntitlements();
  }, []);

  const loadEntitlements = async () => {
    try {
      const { data } = await axios.get(`${API}/user/entitlements`, { withCredentials: true });
      setEntitlements(data);
    } catch (err) {
      console.error('Error loading entitlements:', err);
      setError('Error al cargar tu biblioteca. Verifica tu conexión e intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (entitlement) => {
    if (entitlement.status === 'permanent') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 border border-green-500/30 rounded-full text-xs text-green-400">
          <Zap className="w-3 h-3" /> Compra permanente
        </span>
      );
    }
    if (entitlement.status === 'expired') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-500/10 border border-red-500/30 rounded-full text-xs text-red-400">
          <Lock className="w-3 h-3" /> Expirado
        </span>
      );
    }
    if (entitlement.status === 'active') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-xs text-yellow-400">
          <Clock className="w-3 h-3" /> {entitlement.days_remaining} días restantes
        </span>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando tu biblioteca...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-white mb-2 font-['Outfit']">Mis Libros</h1>
        <p className="text-[#A0A0A0] mb-8">Libros con acceso digital</p>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-400 text-sm flex items-start justify-between">
            <span>{error}</span>
            <button onClick={() => { setError(null); setLoading(true); loadEntitlements(); }} className="ml-3 text-red-400 hover:text-red-300 flex-shrink-0">
              ✕
            </button>
          </div>
        )}

        {entitlements.length === 0 ? (
          <div className="text-center py-20">
            <BookOpen className="w-16 h-16 text-[#A0A0A0] mx-auto mb-4" />
            <p className="text-[#A0A0A0] text-lg mb-4">No tienes libros en tu biblioteca</p>
            <Link to="/" className="text-[#D92B2B] hover:underline font-semibold">
              Explorar catálogo
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {entitlements.map(e => (
              <div key={e.id} className="bg-[#121212] border border-white/10 rounded-2xl overflow-hidden hover:border-white/20 transition-all">
                {e.cover_image_url && (
                  <img src={e.cover_image_url} alt={e.book_title} className="w-full h-48 object-cover" />
                )}
                <div className="p-5">
                  <h3 className="text-white font-bold text-lg mb-1 line-clamp-1">{e.book_title}</h3>
                  <p className="text-[#A0A0A0] text-sm mb-3">{e.author_name}</p>
                  {getStatusBadge(e)}
                  <div className="mt-4 flex gap-2">
                    {e.status !== 'expired' && (
                      <Link to={`/books/${e.book_id}`}
                        className="flex-1 bg-[#D92B2B] hover:bg-[#F03C3C] text-white text-center py-2 rounded-lg text-sm font-semibold transition-all">
                        Leer
                      </Link>
                    )}
                    <Link to={`/books/${e.book_id}`}
                      className="flex-1 bg-white/5 hover:bg-white/10 text-white text-center py-2 rounded-lg text-sm font-semibold transition-all border border-white/10">
                      Detalles
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
