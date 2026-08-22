import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { MessageSquare, Search, Plus, Clock, TrendingUp, MessageCircle, CheckCircle, Filter } from 'lucide-react';
import axios from 'axios';

export default function ForumPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || '');
  const [sort, setSort] = useState('newest');

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchPosts();
  }, [page, selectedCategory, sort]);

  const fetchCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/forum/categories`);
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchPosts = async () => {
    setLoading(true);
    try {
      if (searchQuery.trim()) {
        const params = new URLSearchParams({ q: searchQuery, page, limit: 20 });
        if (selectedCategory) params.append('category', selectedCategory);
        params.append('sort', sort === 'newest' ? 'newest' : 'popular');
        const { data } = await axios.get(`${API}/forum/search?${params}`);
        setPosts(data.posts);
        setTotal(data.total);
        setPages(data.pages);
      } else {
        const params = new URLSearchParams({ page, limit: 20, sort });
        if (selectedCategory) params.append('category', selectedCategory);
        const { data } = await axios.get(`${API}/forum/posts?${params}`);
        setPosts(data.posts);
        setTotal(data.total);
        setPages(data.pages);
      }
    } catch (error) {
      console.error('Error fetching posts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchPosts();
  };

  const sortOptions = [
    { value: 'newest', label: 'Recientes', icon: Clock },
    { value: 'popular', label: 'Populares', icon: TrendingUp },
    { value: 'most_replies', label: 'Más respuestas', icon: MessageCircle },
    { value: 'unanswered', label: 'Sin respuesta', icon: MessageSquare },
    { value: 'resolved', label: 'Resueltos', icon: CheckCircle },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 pt-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white font-['Outfit'] mb-2">FORO ESTUDIANTIL</h1>
          <p className="text-[#A0A0A0] text-sm md:text-base">Un espacio para aprender, preguntar, compartir y conversar con la comunidad de AeternumLibrary.</p>
        </div>

        {/* Search + New Post */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#606060]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar en el foro..."
                className="w-full bg-[#121212] border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-[#F5F5F5] text-sm focus:border-[#D92B2B] focus:outline-none"
              />
            </div>
            <button type="submit" className="bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors">
              Buscar
            </button>
          </form>
          {user && (
            <Link to="/forum/new" className="bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 whitespace-nowrap">
              <Plus className="w-4 h-4" /> Nueva publicación
            </Link>
          )}
        </div>

        {/* Categories */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setSelectedCategory(''); setPage(1); }}
              className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wider uppercase border transition-all duration-200 ${
                !selectedCategory
                  ? 'bg-[#D92B2B] text-white border-[#D92B2B] shadow-lg shadow-[#D92B2B]/20'
                  : 'bg-transparent text-[#A0A0A0] border-white/10 hover:text-white hover:border-white/20'
              }`}
            >
              Todos
            </button>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => { setSelectedCategory(cat.id === selectedCategory ? '' : cat.id); setPage(1); }}
                className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wider uppercase border transition-all duration-200 ${
                  selectedCategory == cat.id
                    ? 'text-white border-transparent shadow-lg'
                    : 'bg-transparent text-[#A0A0A0] border-white/10 hover:text-white hover:border-white/20'
                }`}
                style={selectedCategory == cat.id ? { backgroundColor: cat.color, borderColor: cat.color } : {}}
              >
                {cat.icon} {cat.name}
              </button>
            ))}
          </div>
        </div>

        {/* Sort */}
        <div className="flex flex-wrap gap-2 mb-6">
          {sortOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setSort(opt.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                sort === opt.value
                  ? 'bg-white/10 text-white'
                  : 'text-[#A0A0A0] hover:text-white'
              }`}
            >
              <opt.icon className="w-3 h-3" /> {opt.label}
            </button>
          ))}
        </div>

        {/* Posts */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-[#A0A0A0]">Cargando publicaciones...</p>
          </div>
        ) : posts.length === 0 ? (
          <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-[#404040]" />
            <p className="text-lg font-medium text-[#A0A0A0]">No hay publicaciones aún</p>
            <p className="text-sm mt-1 text-[#606060]">Sé el primero en crear una conversación</p>
          </div>
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <Link
                key={post.id}
                to={`/forum/post/${post.id}`}
                className="block bg-[#121212] border border-white/10 rounded-xl p-6 hover:border-white/20 transition-all duration-200"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {post.is_pinned && <span className="text-[#D4AF37] text-xs font-bold">📌 Fijado</span>}
                      {post.is_resolved && <span className="text-emerald-400 text-xs font-bold">✅ Resuelto</span>}
                      {post.category_icon && (
                        <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: (post.category_color || '#606060') + '20', color: post.category_color || '#A0A0A0' }}>
                          {post.category_icon} {post.category_name}
                        </span>
                      )}
                    </div>
                    <h3 className="text-[#F5F5F5] font-semibold text-base mb-1 truncate">{post.title}</h3>
                    <div className="flex items-center gap-3 text-xs text-[#A0A0A0]">
                      <span>Por @{post.author_username || 'usuario'}</span>
                      <span>·</span>
                      <span>{new Date(post.created_at).toLocaleDateString('es-PE')}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-[#606060] shrink-0">
                    <span className="flex items-center gap-1"><MessageSquare className="w-3.5 h-3.5" /> {post.reply_count || 0}</span>
                    <span className="flex items-center gap-1"><TrendingUp className="w-3.5 h-3.5" /> {post.like_count || 0}</span>
                    <span className="flex items-center gap-1"><Filter className="w-3.5 h-3.5" /> {post.views || 0}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#121212] border border-white/10 text-[#A0A0A0] hover:text-white hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Anterior
            </button>
            <span className="text-sm text-[#A0A0A0]">Página {page} de {pages}</span>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#121212] border border-white/10 text-[#A0A0A0] hover:text-white hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
