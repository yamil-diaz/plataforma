import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, LogOut, BookOpen, Layers, Bell, Video } from 'lucide-react';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '/api';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    if (user) {
      fetchNotifications();
    }
  }, [user]);

  const fetchNotifications = async () => {
    try {
      const { data } = await axios.get(`${API}/notifications`, { withCredentials: true });
      setNotifications(data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const handleReadNotification = async (notifId) => {
    try {
      await axios.put(`${API}/notifications/${notifId}/read`, {}, { withCredentials: true });
      setNotifications(notifications.map(n => n.id === notifId ? { ...n, is_read: true } : n));
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
                            <p>{n.message}</p>
                            <span className="text-[10px] text-[#A0A0A0] mt-1 block">{new Date(n.created_at).toLocaleString()}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Balance de Rayos */}
              <div className="flex items-center gap-2 px-3.5 py-1.5 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-full text-xs font-semibold text-[#D4AF37] tracking-wider uppercase animate-pulse">
                <Zap className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                <span>{user.rayos_balance} Rayos</span>
              </div>

              {/* Nombre de Usuario / Perfil */}
              <Link to={`/profile/${user.id}`} className="text-sm text-[#F5F5F5] font-medium hidden sm:inline hover:text-blue-400 transition-colors">
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
            </div>
          )}
        </div>

      </div>
    </nav>
  );
};
