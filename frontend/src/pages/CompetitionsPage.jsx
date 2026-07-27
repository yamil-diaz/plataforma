import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { useNavigate, Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Trophy, Clock, Users, LogIn, Swords, CheckCircle2 } from 'lucide-react';

export default function CompetitionsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCompetitions();
    // Auto-refresh every 30 seconds to update statuses
    const interval = setInterval(fetchCompetitions, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchCompetitions = async () => {
    try {
      const { data } = await axios.get(`${API}/competitions`);
      setCompetitions(data);
    } catch (err) {
      console.error("Error fetching competitions", err);
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async (compId) => {
    if (!user) {
      navigate('/login');
      return;
    }
    try {
      await axios.post(`${API}/competitions/${compId}/join`, {}, { withCredentials: true });
      alert("¡Te has inscrito a la competencia!");
      fetchCompetitions(); // Refresh
      navigate(`/competitions/${compId}`);
    } catch (err) {
      alert(err.response?.data?.detail || "Error al inscribirse");
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center">Cargando...</div>;

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      
      {/* Header */}
      <div className="bg-gradient-to-b from-[#1A1A1A] to-[#0A0A0A] py-16 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-500 font-['Outfit'] mb-6">
            Arena de Campeones
          </h1>
          <p className="text-[#A0A0A0] text-lg max-w-2xl mx-auto leading-relaxed">
            Participa en torneos de comprensión lectora en vivo. Responde más rápido que nadie y gana cientos de Rayos.
          </p>
          {user?.role === 'admin' && (
            <div className="mt-8">
              <Link to="/admin/competitions/new" className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 px-6 py-3 rounded-full text-white font-semibold transition-colors">
                <Trophy className="w-5 h-5" />
                Administrar Competencias
              </Link>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 mt-12 space-y-12">
        {['active', 'pending', 'completed'].map(statusGroup => {
          const groupComps = competitions.filter(c => c.status === statusGroup);
          if (groupComps.length === 0) return null;
          
          let title = "Próximas Competencias";
          let icon = <Clock className="w-5 h-5 text-blue-400" />;
          if (statusGroup === 'active') {
            title = "¡En Vivo Ahora!";
            icon = <Swords className="w-5 h-5 text-red-500 animate-pulse" />;
          } else if (statusGroup === 'completed') {
            title = "Resultados Anteriores";
            icon = <CheckCircle2 className="w-5 h-5 text-green-400" />;
          }

          return (
            <section key={statusGroup}>
              <div className="flex items-center gap-3 mb-6 border-b border-white/10 pb-4">
                {icon}
                <h2 className="text-2xl font-bold text-white">{title}</h2>
                <span className="bg-white/10 text-[#A0A0A0] text-xs px-2.5 py-1 rounded-full">{groupComps.length}</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {groupComps.map(comp => {
                  const date = new Date(comp.scheduled_at);
                  
                  return (
                    <div key={comp.id} className={`bg-[#121212] rounded-2xl border ${statusGroup === 'active' ? 'border-red-500/30' : 'border-white/5'} overflow-hidden hover:border-white/20 transition-all group`}>
                      <div className="h-40 overflow-hidden relative">
                        {comp.cover_image_url ? (
                          <img src={comp.cover_image_url} alt={comp.book_title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                        ) : (
                          <div className="w-full h-full bg-[#1A1A1A] flex items-center justify-center text-[#A0A0A0]">Sin Portada</div>
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-[#121212] to-transparent"></div>
                        <div className="absolute bottom-4 left-4 right-4">
                          <span className="text-xs font-bold text-purple-400 uppercase tracking-wide bg-purple-900/50 px-2 py-1 rounded backdrop-blur-sm">
                            {comp.book_title}
                          </span>
                        </div>
                      </div>
                      
                      <div className="p-5">
                        <h3 className="text-lg font-bold text-white mb-4 line-clamp-2">{comp.title}</h3>
                        
                        <div className="flex items-center justify-between text-sm text-[#A0A0A0] mb-6">
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            <span>
                              {date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })} • {date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>

                        {statusGroup === 'pending' && (
                          <button onClick={() => handleJoin(comp.id)} className="w-full py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors">
                            <LogIn className="w-4 h-4" /> Inscribirse
                          </button>
                        )}
                        
                        {statusGroup === 'active' && (
                          <Link to={`/competitions/${comp.id}`} className="w-full py-3 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors shadow-[0_0_15px_rgba(220,38,38,0.3)]">
                            <Swords className="w-4 h-4" /> Entrar a Competir
                          </Link>
                        )}

                        {statusGroup === 'completed' && (
                          <Link to={`/competitions/${comp.id}`} className="w-full py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors">
                            <Trophy className="w-4 h-4" /> Ver Resultados
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
