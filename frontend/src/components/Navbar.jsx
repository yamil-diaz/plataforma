import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, LogOut, BookOpen, Layers, Bell, Video, Trophy, Heart } from 'lucide-react';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '/api';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSupportModal, setShowSupportModal] = useState(false);

  useEffect(() => {
    if (user) {
      fetchNotifications();
    }
  }, [user]);

  const fetchNotifications = async () => {
    try {
      const { data } = await axios.get(`${API}/notifications`, { withCredentials: true });
      setNotifications(data.notifications || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const handleReadNotification = async (notifId) => {
    try {
      await axios.put(`${API}/notifications/read`, {}, { withCredentials: true });
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (error) {
      console.error('Error reading notification:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Error al cerrar sesión:', error);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <nav className="bg-[#0A0A0A]/80 border-b border-white/10 backdrop-blur-md sticky top-0 z-40 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 hover:opacity-90 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-[#D92B2B] flex items-center justify-center shadow-lg shadow-[#D92B2B]/20">
            <Zap className="w-5 h-5 text-white fill-white" />
          </div>
          <span className="text-xl font-bold tracking-wider text-white font-['Outfit']">AETERNUM</span>
        </Link>

        {/* Enlaces de Navegación */}
        <div className="flex items-center gap-6">
          <Link to="/courses" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
            <Video className="w-4 h-4" />
            Cursos
          </Link>

          <Link to="/" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" />
            Catálogo
          </Link>

          {user && (
            <Link to="/dashboard" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5">
              <Layers className="w-4 h-4" />
              {user.role === 'admin' ? 'Panel Admin' : 'Panel Autor'}
            </Link>
          )}

          <Link to="/terminos" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5 ml-2">
            Términos
          </Link>
        </div>

        {/* Autenticación / Perfil */}
        <div className="flex items-center gap-6">
          {user ? (
            <div className="flex items-center gap-6">
              
              {/* Notificaciones */}
              <div className="relative">
                <button 
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="relative p-2 text-[#A0A0A0] hover:text-white transition-colors"
                >
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse border border-[#0A0A0A]"></span>
                  )}
                </button>
                
                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-[#121212] border border-white/10 rounded-xl shadow-2xl py-2 z-50">
                    <div className="px-4 py-2 border-b border-white/10 font-bold text-white text-sm">Notificaciones</div>
                    <div className="max-h-64 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <div className="px-4 py-4 text-xs text-[#A0A0A0] text-center">No tienes notificaciones.</div>
                      ) : (
                        notifications.map(n => (
                          <div 
                            key={n.id} 
                            onClick={() => !n.is_read && handleReadNotification(n.id)}
                            className={`px-4 py-3 border-b border-white/5 text-sm transition-colors ${!n.is_read ? 'bg-white/5 cursor-pointer hover:bg-white/10 text-white' : 'text-[#A0A0A0]'}`}
                          >
                            <p>{n.content}</p>
                            <span className="text-[10px] text-[#A0A0A0] mt-1 block">{new Date(n.created_at).toLocaleString()}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Botón Apoyar (Plataforma) */}
              <button 
                onClick={() => setShowSupportModal(true)}
                className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 text-white text-xs font-bold rounded-full transition-all shadow-[0_0_10px_rgba(220,38,38,0.3)]"
              >
                <Heart className="w-3.5 h-3.5 fill-white" /> Apoyar
              </button>

              {/* Balance de Rayos */}
              <div className="flex items-center gap-2 px-3.5 py-1.5 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-full text-xs font-semibold text-[#D4AF37] tracking-wider uppercase animate-pulse">
                <Zap className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                <span>{user.rayos_balance} Rayos</span>
              </div>

              {/* Nombre de Usuario / Perfil */}
              <Link to={`/profile/${user.username || user.id}`} className="text-sm text-[#F5F5F5] font-medium hidden sm:inline hover:text-blue-400 transition-colors">
                {user.name}
              </Link>

              {/* Cerrar Sesión */}
              <button
                onClick={handleLogout}
                className="p-2 text-[#A0A0A0] hover:text-[#D92B2B] hover:bg-[#D92B2B]/5 rounded-lg transition-all duration-200"
                title="Cerrar Sesión"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-sm font-medium text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors">
                Iniciar Sesión
              </Link>
              <Link to="/register" className="bg-[#D92B2B] text-white hover:bg-[#F03C3C] text-sm font-medium px-4 py-2 rounded-md transition-colors shadow-md shadow-[#D92B2B]/10">
                Registrarse
              </Link>
              <button onClick={() => setShowSupportModal(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 text-white text-xs font-bold rounded-full transition-all shadow-[0_0_10px_rgba(220,38,38,0.3)]">
                <Heart className="w-3.5 h-3.5 fill-white" /> Apoyar
              </button>
            </div>
          )}
        </div>
      </div>

      {/* SUPPORT MODAL (Plataforma) */}
      {showSupportModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121212] border border-white/10 rounded-3xl w-full max-w-md overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.5)]">
            <div className="relative h-32 bg-gradient-to-r from-[#D92B2B] to-purple-800 flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-20"></div>
              <Heart className="w-16 h-16 text-white fill-white animate-pulse relative z-10 drop-shadow-lg" />
              <button onClick={() => setShowSupportModal(false)} className="absolute top-4 right-4 text-white/70 hover:text-white bg-black/20 hover:bg-black/40 p-1.5 rounded-full backdrop-blur-sm transition-all z-20">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            
            <div className="p-8 text-center">
              <h2 className="text-2xl font-bold text-white mb-3">Apoya a AETERNUM</h2>
              <p className="text-[#A0A0A0] text-sm mb-8 leading-relaxed">
                Esta plataforma es gratuita y sin anuncios. Tu donación ayuda directamente a pagar los servidores y mantener viva la comunidad.
              </p>
              
              <div className="space-y-4">
                {/* YAPE / PLIN (PERÚ) */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition-colors">
                  <div className="flex items-center justify-center gap-3 mb-3">
                    <span className="bg-[#742384] text-white text-xs font-black px-3 py-1 rounded">YAPE</span>
                    <span className="text-[#A0A0A0] text-xs">/</span>
                    <span className="bg-[#00D4C5] text-black text-xs font-black px-3 py-1 rounded">PLIN</span>
                  </div>
                  <p className="text-sm text-[#A0A0A0] mb-2">Para usuarios en Perú</p>
                  
                  {/* QR de Yape */}
                  <div className="bg-white p-2 rounded-xl inline-block mb-2">
                    <img src="/yape-qr.png" alt="QR Yape" className="w-32 h-32 object-contain" onError={(e) => e.target.style.display='none'} />
                  </div>
                  
                  <p className="text-3xl font-black text-white tracking-widest">931 524 201</p>
                </div>

                {/* PAYPAL (INTERNACIONAL) */}
                <a href="https://paypal.me/Jorgeramos1997" target="_blank" rel="noopener noreferrer" className="block bg-[#00457C] hover:bg-[#005ea6] rounded-2xl p-5 transition-colors group">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <span className="text-white text-lg font-bold italic">PayPal</span>
                  </div>
                  <p className="text-sm text-blue-200 group-hover:text-white transition-colors">Donaciones Internacionales (Dólares)</p>
                </a>
              </div>
              
              <p className="text-xs text-[#A0A0A0] mt-8 mb-4">
                ¡Gracias infinitas por creer en este proyecto! ❤️
              </p>
              
              <button 
                onClick={() => setShowSupportModal(false)}
                className="w-full bg-white/10 hover:bg-white/20 text-white font-semibold py-3 rounded-xl transition-colors border border-white/10"
              >
                Cerrar Ventana
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};
