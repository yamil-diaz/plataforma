import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Zap, LogOut, BookOpen, Layers, Bell, Video, Trophy, Heart, Sparkles,
  MessageSquare, ShoppingBag, ShoppingCart, User, ChevronDown, Store,
  Package, Wallet, Settings, LifeBuoy, Globe, CreditCard, X
} from 'lucide-react';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '/api';

// ── Carrito global (localStorage) ───────────────────────────────────────────
const CART_KEY = 'aeternum_cart';

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeCart(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  window.dispatchEvent(new CustomEvent('aeternum-cart', { detail: items }));
}

export const useCart = () => {
  const [items, setItems] = useState(readCart);
  useEffect(() => {
    const h = () => setItems(readCart());
    window.addEventListener('aeternum-cart', h);
    window.addEventListener('storage', h);
    return () => {
      window.removeEventListener('aeternum-cart', h);
      window.removeEventListener('storage', h);
    };
  }, []);
  const add = (book) => {
    const cart = readCart().filter(i => i.id !== book.id);
    cart.push({
      id: book.id,
      title: book.title,
      author_name: book.author_name,
      cover_image_url: book.cover_image_url,
      price: book.price || 0,
      rental_price: book.rental_price || 0,
    });
    writeCart(cart);
  };
  const remove = (id) => writeCart(readCart().filter(i => i.id !== id));
  const clear = () => writeCart([]);
  const total = items.reduce((s, i) => s + (parseFloat(i.price) || 0), 0);
  return { items, add, remove, clear, total, count: items.length };
};

export const ROLE_LABELS = {
  admin: 'Admin',
  autor: 'Vendedor',
  user: 'Comprador',
};

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { count: cartCount, items: cartItems, remove: cartRemove, clear: cartClear, total: cartTotal } = useCart();
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSupportModal, setShowSupportModal] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showCart, setShowCart] = useState(false);
  const profileRef = useRef(null);
  const cartRef = useRef(null);

  useEffect(() => {
    if (user) fetchNotifications();
  }, [user]);

  useEffect(() => {
    const onClick = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) setShowProfile(false);
      if (cartRef.current && !cartRef.current.contains(e.target)) setShowCart(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const fetchNotifications = async () => {
    try {
      const { data } = await axios.get(`${API}/notifications`, { withCredentials: true });
      setNotifications(data.notifications || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const handleReadNotification = async () => {
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
  const roleLabel = user ? (ROLE_LABELS[user.role] || 'Comprador') : '';
  const panelPath = user?.role === 'admin' ? '/dashboard' : user?.role === 'autor' ? '/dashboard' : '/dashboard';

  return (
    <nav className="bg-[#0A0A0A]/90 border-b border-white/10 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 shrink-0 hover:opacity-90 transition-opacity">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#D92B2B] to-[#9F1239] flex items-center justify-center shadow-lg shadow-[#D92B2B]/25">
            <Zap className="w-5 h-5 text-white fill-white" />
          </div>
          <div className="leading-tight hidden sm:block">
            <span className="text-lg font-bold tracking-[0.15em] text-white font-['Outfit']">AETERNUM</span>
            <span className="block text-[9px] tracking-[0.25em] text-[#D4AF37] uppercase">Library</span>
          </div>
        </Link>

        {/* Nav links */}
        <div className="hidden lg:flex items-center gap-1">
          <Link to="/" className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" /> Catálogo
          </Link>
          <Link to="/courses" className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
            <Video className="w-4 h-4" /> Cursos
          </Link>
          <Link to="/forum" className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
            <MessageSquare className="w-4 h-4" /> Foro
          </Link>
          {user && (
            <Link to={panelPath} className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
              <Layers className="w-4 h-4" /> {user.role === 'admin' ? 'Panel Admin' : user.role === 'autor' ? 'Panel Vendedor' : 'Panel Comprador'}
            </Link>
          )}
          {user && (
            <Link to="/mis-compras" className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
              <ShoppingBag className="w-4 h-4" /> Mis Compras
            </Link>
          )}
          {user && (
            <Link to="/ia" className="px-3 py-2 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-[#D4AF37]" /> IA
            </Link>
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Moneda / Idioma (display) */}
          <div className="hidden xl:flex items-center gap-2 text-[10px] text-[#A0A0A0] mr-1">
            <span className="flex items-center gap-1 px-2 py-1 border border-white/10 rounded-md"><Globe className="w-3 h-3" /> ES</span>
            <span className="flex items-center gap-1 px-2 py-1 border border-white/10 rounded-md"><CreditCard className="w-3 h-3" /> PEN · S/</span>
          </div>

          {user ? (
            <>
              {/* Notificaciones */}
              <div className="relative" ref={cartRef}>
                  <button
                    onClick={() => { setShowNotifications(false); setShowProfile(false); setShowCart(!showCart); }}
                    className="relative p-2 text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-[color,background-color,transform] duration-150 ease-ae-out active:scale-[0.97]"
                    title="Carrito"
                  >
                  <ShoppingCart className="w-5 h-5" />
                  {cartCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-[#D92B2B] text-white text-[10px] font-bold rounded-full flex items-center justify-center border border-[#0A0A0A]">
                      {cartCount}
                    </span>
                  )}
                </button>
                {showCart && (
                  <div className="ae-dropdown absolute right-0 mt-2 w-80 z-50 overflow-hidden">
                    <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                      <span className="font-bold text-white text-sm">Tu carrito</span>
                      <span className="text-[#D4AF37] text-sm font-bold">S/ {cartTotal.toFixed(2)}</span>
                    </div>
                    <div className="max-h-72 overflow-y-auto">
                      {cartItems.length === 0 ? (
                        <div className="px-4 py-8 text-center text-[#A0A0A0] text-sm">
                          <ShoppingCart className="w-8 h-8 mx-auto mb-2 opacity-40" />
                          Tu carrito está vacío
                        </div>
                      ) : (
                        cartItems.map(item => (
                          <div key={item.id} className="px-4 py-3 border-b border-white/5 flex items-center gap-3">
                            {item.cover_image_url && (
                              <img src={item.cover_image_url} alt="" className="w-10 h-14 object-cover rounded" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="text-white text-sm font-medium truncate">{item.title}</p>
                              <p className="text-[#A0A0A0] text-xs truncate">{item.author_name}</p>
                              <p className="text-[#D4AF37] text-xs font-bold mt-0.5">S/ {(parseFloat(item.price) || 0).toFixed(2)}</p>
                            </div>
                            <button
                              onClick={() => cartRemove(item.id)}
                              className="text-[#A0A0A0] hover:text-red-400 p-1 transition-colors"
                              title="Quitar del carrito"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                    {cartItems.length > 0 && (
                      <div className="p-3 border-t border-white/10 space-y-2">
                        <button
                          onClick={() => {
                            setShowCart(false);
                            const first = cartItems[0];
                            if (first?.id) navigate(`/checkout?book_id=${first.id}`);
                          }}
                          className="ae-btn ae-btn-primary w-full py-2.5 text-sm"
                        >
                          Ir a pagar
                        </button>
                        <button onClick={cartClear} className="w-full text-[#A0A0A0] hover:text-red-400 text-xs py-1 transition-colors">
                          Vaciar carrito
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Notificaciones bell */}
              <div className="relative">
                <button
                  onClick={() => { setShowCart(false); setShowProfile(false); setShowNotifications(!showNotifications); }}
                  className="relative p-2 text-[#A0A0A0] hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                  title="Notificaciones"
                >
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse border border-[#0A0A0A]" />
                  )}
                </button>
                {showNotifications && (
                  <div className="ae-dropdown absolute right-0 mt-2 w-80 py-2 z-50">
                    <div className="px-4 py-2 border-b border-white/10 font-bold text-white text-sm">Notificaciones</div>
                    <div className="max-h-64 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <div className="px-4 py-4 text-xs text-[#A0A0A0] text-center">No tienes notificaciones.</div>
                      ) : (
                        notifications.map(n => (
                          <div
                            key={n.id}
                            onClick={() => !n.is_read && handleReadNotification()}
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

              {/* Rayos */}
              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-[#D4AF37]/10 border border-[#D4AF37]/25 rounded-full text-xs font-semibold text-[#D4AF37] tabular-nums">
                <Zap className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                <span>{user.rayos_balance}</span>
              </div>

              {/* Mi Perfil dropdown */}
              <div className="relative" ref={profileRef}>
                <button
                  onClick={() => { setShowCart(false); setShowNotifications(false); setShowProfile(!showProfile); }}
                  className="flex items-center gap-2 pl-2 pr-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full transition-colors"
                >
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#D92B2B] to-[#9F1239] flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <span className="hidden md:block text-xs font-semibold text-white max-w-[100px] truncate">{user.name}</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-[#A0A0A0] transition-transform ${showProfile ? 'rotate-180' : ''}`} />
                </button>

                {showProfile && (
                  <div className="ae-dropdown absolute right-0 mt-2 w-64 z-50 overflow-hidden">
                    <div className="px-4 py-3 border-b border-white/10">
                      <p className="text-white font-semibold text-sm truncate">{user.name}</p>
                      <p className="text-[#A0A0A0] text-xs truncate">{user.email}</p>
                      <span className="inline-block mt-1.5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-[#D4AF37]/15 text-[#D4AF37] rounded border border-[#D4AF37]/30">
                        {roleLabel}
                      </span>
                    </div>
                    <div className="py-1">
                      <Link to={`/profile/${user.username || user.id}`} onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                        <User className="w-4 h-4" /> Mi perfil
                      </Link>
                      <Link to="/mis-compras" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                        <ShoppingBag className="w-4 h-4" /> Mis compras
                      </Link>
                      <Link to="/mis-pedidos" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                        <Package className="w-4 h-4" /> Tus pedidos
                      </Link>
                      <Link to={panelPath} onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                        <Layers className="w-4 h-4" /> {user.role === 'admin' ? 'Panel Admin' : user.role === 'autor' ? 'Panel Vendedor' : 'Panel Comprador'}
                      </Link>
                      {user.role !== 'user' && (
                        <Link to="/dashboard" onClick={() => { setShowProfile(false); }} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                          <Wallet className="w-4 h-4" /> Ganancias
                        </Link>
                      )}
                      <Link to="/ia" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-white hover:bg-white/5 transition-colors">
                        <Sparkles className="w-4 h-4 text-[#D4AF37]" /> Asistente IA
                      </Link>
                    </div>
                    <div className="border-t border-white/10 py-1">
                      <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#A0A0A0] hover:text-red-400 hover:bg-red-500/5 transition-colors">
                        <LogOut className="w-4 h-4" /> Cerrar sesión
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="text-sm font-medium text-[#A0A0A0] hover:text-white px-3 py-2 rounded-lg hover:bg-white/5 transition-colors">
                Iniciar sesión
              </Link>
              <Link to="/register" className="ae-btn ae-btn-primary text-sm px-4 py-2">
                Crear cuenta
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* SUPPORT MODAL */}
      {showSupportModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121212] border border-white/10 rounded-3xl w-full max-w-md overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.5)]">
            <div className="relative h-32 bg-[#D92B2B] flex items-center justify-center">
              <Heart className="w-16 h-16 text-white fill-white" />
              <button onClick={() => setShowSupportModal(false)} className="absolute top-4 right-4 text-white/70 hover:text-white bg-black/20 p-1.5 rounded-full transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-8 text-center">
              <h2 className="text-2xl font-bold text-white mb-3">Apoya a AETERNUM</h2>
              <p className="text-[#A0A0A0] text-sm mb-6">Tu donación mantiene viva la plataforma.</p>
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5 mb-4">
                <div className="flex items-center justify-center gap-3 mb-3">
                  <span className="bg-[#742384] text-white text-xs font-black px-3 py-1 rounded">YAPE</span>
                  <span className="text-[#A0A0A0]">/</span>
                  <span className="bg-[#00D4C5] text-black text-xs font-black px-3 py-1 rounded">PLIN</span>
                </div>
                <div className="bg-white p-2 rounded-xl inline-block mb-2">
                  <img src="/yape-qr.png" alt="QR Yape" className="w-32 h-32 object-contain" onError={(e) => e.target.style.display='none'} />
                </div>
                <p className="text-3xl font-black text-white tracking-widest">931 524 201</p>
              </div>
              <a href="https://paypal.me/Jorgeramos1997" target="_blank" rel="noopener noreferrer" className="block bg-[#00457C] hover:bg-[#005ea6] rounded-xl p-4 transition-colors">
                <span className="text-white font-bold">PayPal · Donaciones internacionales</span>
              </a>
              <button onClick={() => setShowSupportModal(false)} className="ae-btn ae-btn-ghost w-full mt-6 py-3">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};
