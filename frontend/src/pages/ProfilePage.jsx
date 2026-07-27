import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { Navbar } from '../components/Navbar';
import { Trophy, BookOpen, Clock, Medal, Edit, X, Save, Zap, Heart } from 'lucide-react';

export default function ProfilePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  
  const [profile, setProfile] = useState(null);
  const [badges, setBadges] = useState([]);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Follow System State
  const [followersCount, setFollowersCount] = useState(0);
  const [followingCount, setFollowingCount] = useState(0);
  const [isFollowing, setIsFollowing] = useState(false);

  // Edit Mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ username: '', bio: '', favorite_genres: '', profile_image: null });
  const [previewImage, setPreviewImage] = useState(null);
  
  // Donate Modal state
  const [showDonateModal, setShowDonateModal] = useState(false);
  const [donateAmount, setDonateAmount] = useState(10);

  const isOwnProfile = user && (user.username === id || user.id === parseInt(id));

  useEffect(() => {
    fetchProfile();
  }, [id]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const { data } = await axios.get(`${API}/users/profile/${id}`);
      setProfile(data.profile);
      setBadges(data.badges);
      setBooks(data.books);
      setFollowersCount(data.followers_count);
      setFollowingCount(data.following_count);
      setIsFollowing(data.is_following);
      setEditForm({ 
        username: data.profile.username || '',
        bio: data.profile.bio || '', 
        favorite_genres: data.profile.favorite_genres || '', 
        profile_image: null 
      });
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Error del servidor.';
      setError(`Usuario no encontrado o error del servidor. Detalle: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const getLevelInfo = (rayos) => {
    if (rayos >= 5000) return { name: 'Aeternum', color: 'bg-purple-500', text: 'text-purple-400' };
    if (rayos >= 1001) return { name: 'Selva', color: 'bg-emerald-600', text: 'text-emerald-500' };
    if (rayos >= 501) return { name: 'Bosque', color: 'bg-emerald-500', text: 'text-emerald-400' };
    if (rayos >= 201) return { name: 'Árbol', color: 'bg-green-500', text: 'text-green-400' };
    if (rayos >= 51) return { name: 'Retoño', color: 'bg-lime-500', text: 'text-lime-400' };
    return { name: 'Semilla', color: 'bg-amber-700', text: 'text-amber-600' };
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      const formData = new FormData();
      formData.append('username', editForm.username);
      formData.append('bio', editForm.bio);
      formData.append('favorite_genres', editForm.favorite_genres);
      if (editForm.profile_image) {
        formData.append('profile_image', editForm.profile_image);
      }
      
      await axios.put(`${API}/users/profile/me`, formData, { withCredentials: true });
      
      // Update global user state with new username so Navbar updates
      if (user) {
        await refreshUser();
      }

      setIsEditing(false);
      
      if (editForm.username && editForm.username !== id) {
        navigate(`/profile/${editForm.username}`);
      } else {
        fetchProfile();
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al actualizar perfil');
    }
  };

  const handleFollowToggle = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    try {
      if (isFollowing) {
        await axios.post(`${API}/users/${profile.username}/unfollow`, {}, { withCredentials: true });
        setFollowersCount(prev => prev - 1);
        setIsFollowing(false);
      } else {
        await axios.post(`${API}/users/${profile.username}/follow`, {}, { withCredentials: true });
        setFollowersCount(prev => prev + 1);
        setIsFollowing(true);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al actualizar seguidor');
    }
  };

  const handleDonateRayos = async (e) => {
    e.preventDefault();
    if (!user) return navigate('/login');
    try {
      await axios.post(`${API}/users/${profile.username}/donate-rayos`, { amount: parseInt(donateAmount) }, { withCredentials: true });
      alert(`¡Has donado ${donateAmount} Rayos exitosamente!`);
      setShowDonateModal(false);
      refreshUser();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al donar Rayos');
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center">Cargando perfil...</div>;
  if (error) return <div className="min-h-screen bg-[#0A0A0A] text-red-500 flex items-center justify-center">{error}</div>;

  const levelInfo = getLevelInfo(profile.historical_rayos);

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 pt-12">
        
        {/* PROFILE HEADER */}
        <div className="bg-[#121212] border border-white/10 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-r from-blue-900/40 to-purple-900/40 opacity-50 pointer-events-none"></div>
          
          <div className="relative z-10 flex flex-col md:flex-row gap-8 items-start md:items-center">
            <div className="relative">
              <div className={`w-32 h-32 rounded-full border-4 ${levelInfo.color.replace('bg-', 'border-')} overflow-hidden flex items-center justify-center bg-[#1A1A1A]`}>
                {profile.profile_image_url ? (
                  <img src={profile.profile_image_url} alt={profile.name} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-4xl font-bold text-white/50">{profile.name.charAt(0).toUpperCase()}</span>
                )}
              </div>
              <div className={`absolute -bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${levelInfo.color} text-white shadow-lg border-2 border-[#121212]`}>
                {levelInfo.name}
              </div>
            </div>

            <div className="flex-1">
              <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-white font-['Outfit']">{profile.name}</h1>
                  {profile.username && (
                    <p className="text-[#3b82f6] font-semibold text-sm mt-1">@{profile.username}</p>
                  )}
                  <p className="text-[#A0A0A0] text-sm mt-1">
                    Miembro desde {new Date(profile.created_at).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                  </p>
                </div>
                {isOwnProfile && !isEditing ? (
                  <button onClick={() => setIsEditing(true)} className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors border border-white/10">
                    <Edit className="w-4 h-4" /> Editar Perfil
                  </button>
                ) : !isOwnProfile && user && (
                  <div className="flex gap-2">
                    <button onClick={handleFollowToggle} className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all shadow-lg ${isFollowing ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-blue-600 text-white hover:bg-blue-500'}`}>
                      {isFollowing ? 'Siguiendo' : 'Seguir'}
                    </button>
                    <button onClick={() => setShowDonateModal(true)} className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all shadow-lg bg-[#D4AF37] text-black hover:bg-[#F3CE56]">
                      <Heart className="w-4 h-4" /> Donar
                    </button>
                  </div>
                )}
              </div>
              
              <div className="mt-3 flex gap-4 text-sm">
                <div className="text-white">
                  <span className="font-bold">{followersCount}</span> <span className="text-[#A0A0A0]">Seguidores</span>
                </div>
                <div className="text-white">
                  <span className="font-bold">{followingCount}</span> <span className="text-[#A0A0A0]">Siguiendo</span>
                </div>
              </div>
              
              <div className="mt-4 text-[#E0E0E0] max-w-2xl text-sm leading-relaxed">
                {profile.bio ? profile.bio : <span className="italic opacity-50">Sin biografía...</span>}
              </div>

              {profile.favorite_genres && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {profile.favorite_genres.split(',').map((genre, i) => (
                    <span key={i} className="bg-white/5 px-2.5 py-1 rounded-md text-xs text-[#A0A0A0] uppercase border border-white/10">{genre.trim()}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* EDIT MODAL */}
        {isEditing && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
              <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#1A1A1A]">
                <h2 className="text-xl font-bold text-white">Editar Perfil</h2>
                <button onClick={() => setIsEditing(false)} className="text-[#A0A0A0] hover:text-white transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleEditSubmit} className="p-6 space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Username (ID Público)</label>
                  <input type="text" value={editForm.username} onChange={e => setEditForm({...editForm, username: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '')})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" placeholder="tu_usuario" />
                  <p className="text-[#A0A0A0] text-xs mt-1">Este ID se usa para compartir tu perfil: /profile/{editForm.username}</p>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Foto de Perfil</label>
                  <input type="file" accept="image/*" onChange={(e) => {
                    const file = e.target.files[0];
                    setEditForm({...editForm, profile_image: file});
                    if (file) {
                      const reader = new FileReader();
                      reader.onloadend = () => setPreviewImage(reader.result);
                      reader.readAsDataURL(file);
                    }
                  }} className="w-full text-sm text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500/10 file:text-blue-500 hover:file:bg-blue-500/20" />
                  {previewImage && <img src={previewImage} alt="Preview" className="w-16 h-16 rounded-full object-cover mt-3 border border-white/10" />}
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Biografía</label>
                  <textarea rows="3" value={editForm.bio} onChange={e => setEditForm({...editForm, bio: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none placeholder-white/20" placeholder="Cuéntanos sobre ti..."></textarea>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Géneros Favoritos (separados por coma)</label>
                  <input type="text" value={editForm.favorite_genres} onChange={e => setEditForm({...editForm, favorite_genres: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" placeholder="Fantasía, Ciencia Ficción, Misterio..." />
                </div>
                <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                <button type="button" onClick={() => setIsEditing(false)} className="px-5 py-2.5 rounded-lg text-sm font-bold text-[#A0A0A0] hover:text-white transition-colors">Cancelar</button>
                <button type="submit" className="px-5 py-2.5 rounded-lg text-sm font-bold bg-[#D92B2B] text-white hover:bg-[#F03C3C] transition-colors flex items-center gap-2 shadow-lg shadow-[#D92B2B]/20">
                  <Save className="w-4 h-4" /> Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DONATE MODAL */}
      {showDonateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#1A1A1A]">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Heart className="w-5 h-5 text-red-500 fill-red-500" /> Donar Rayos
              </h2>
              <button onClick={() => setShowDonateModal(false)} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleDonateRayos} className="p-6">
              <p className="text-[#A0A0A0] text-sm mb-6 text-center">
                Apoya a <b>{profile.name}</b> donándole tus Rayos.
              </p>
              
              <div className="flex items-center justify-center gap-4 mb-8">
                <button type="button" onClick={() => setDonateAmount(10)} className={`px-4 py-2 rounded-lg font-bold border transition-colors ${donateAmount === 10 ? 'bg-[#D4AF37]/20 border-[#D4AF37] text-[#D4AF37]' : 'border-white/10 text-[#A0A0A0] hover:border-white/30'}`}>10</button>
                <button type="button" onClick={() => setDonateAmount(50)} className={`px-4 py-2 rounded-lg font-bold border transition-colors ${donateAmount === 50 ? 'bg-[#D4AF37]/20 border-[#D4AF37] text-[#D4AF37]' : 'border-white/10 text-[#A0A0A0] hover:border-white/30'}`}>50</button>
                <button type="button" onClick={() => setDonateAmount(100)} className={`px-4 py-2 rounded-lg font-bold border transition-colors ${donateAmount === 100 ? 'bg-[#D4AF37]/20 border-[#D4AF37] text-[#D4AF37]' : 'border-white/10 text-[#A0A0A0] hover:border-white/30'}`}>100</button>
              </div>

              <div className="text-center mb-6">
                <label className="text-xs text-[#A0A0A0] uppercase mb-1 block">Otra cantidad:</label>
                <div className="relative inline-block">
                  <Zap className="w-4 h-4 text-[#D4AF37] absolute left-3 top-1/2 -translate-y-1/2" />
                  <input type="number" min="1" max={user.rayos_balance} value={donateAmount} onChange={(e) => setDonateAmount(Number(e.target.value))} className="bg-[#0A0A0A] border border-[#D4AF37]/30 rounded-lg pl-10 pr-4 py-2 text-white font-bold w-32 focus:outline-none focus:border-[#D4AF37]" />
                </div>
              </div>

              <button type="submit" className="w-full py-3 rounded-xl font-bold bg-gradient-to-r from-[#D4AF37] to-amber-600 text-black hover:opacity-90 transition-opacity shadow-[0_0_15px_rgba(212,175,55,0.4)]">
                Enviar {donateAmount} Rayos
              </button>
            </form>
          </div>
        </div>
      )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          
          {/* STATS & BADGES (LEFT COLUMN) */}
          <div className="space-y-8">
            <div className="bg-[#121212] border border-white/10 rounded-2xl p-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2"><Trophy className="w-4 h-4 text-[#D4AF37]" /> Estadísticas</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#1A1A1A] p-4 rounded-xl border border-white/5 text-center">
                  <span className="block text-[#A0A0A0] text-xs font-semibold uppercase mb-1">Rayos Históricos</span>
                  <span className={`text-2xl font-bold ${levelInfo.text}`}>{profile.historical_rayos}</span>
                </div>
                <div className="bg-[#1A1A1A] p-4 rounded-xl border border-white/5 text-center">
                  <span className="block text-[#A0A0A0] text-xs font-semibold uppercase mb-1">Saldo Actual</span>
                  <span className="text-2xl font-bold text-[#D4AF37]">{profile.rayos_balance}</span>
                </div>
              </div>
            </div>

            <div className="bg-[#121212] border border-white/10 rounded-2xl p-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2"><Medal className="w-4 h-4 text-emerald-500" /> Insignias ({badges.length})</h3>
              {badges.length === 0 ? (
                <p className="text-[#A0A0A0] text-sm text-center py-4">Aún no tiene insignias.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {badges.map(b => (
                    <div key={b.id} className="bg-[#1A1A1A] border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center text-center gap-2 hover:bg-white/5 transition-colors group relative cursor-help">
                      <span className="text-3xl">{b.icon_url}</span>
                      <span className="text-[10px] font-bold text-white uppercase">{b.name}</span>
                      
                      {/* Tooltip */}
                      <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity -top-12 left-1/2 -translate-x-1/2 bg-black text-white text-xs px-3 py-1.5 rounded-lg w-max shadow-xl pointer-events-none z-10">
                        {b.description}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* PUBLISHED BOOKS (RIGHT COLUMN) */}
          <div className="lg:col-span-2">
            <h3 className="text-xl font-bold text-white font-['Outfit'] mb-6 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-[#D92B2B]" /> Libros Publicados
            </h3>
            
            {books.length === 0 ? (
              <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
                <p className="text-[#A0A0A0]">Este usuario aún no ha publicado ningún libro.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {books.map(book => (
                  <Link key={book.id} to={`/book/${book.id}`} className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-all flex h-40 group">
                    <img src={book.cover_image_url} alt={book.title} className="w-28 h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="p-4 flex flex-col justify-between flex-1">
                      <div>
                        <h4 className="font-bold text-white line-clamp-2 text-sm">{book.title}</h4>
                        <span className="inline-block mt-2 bg-white/5 px-2 py-0.5 rounded text-[10px] uppercase text-[#A0A0A0]">{book.category}</span>
                      </div>
                      <div className="flex justify-between items-end">
                        <span className="text-[#D92B2B] font-bold text-sm">Ver libro &rarr;</span>
                        <div className="flex items-center gap-3 text-[#A0A0A0] text-xs font-semibold">
                          <span>❤️ {book.likes}</span>
                          <span>👁️ {book.views}</span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
