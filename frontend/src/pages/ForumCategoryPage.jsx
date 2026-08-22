import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { API } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { Navbar } from '../components/Navbar';
import {
  ArrowLeft,
  Plus,
  MessageCircle,
  ThumbsUp,
  Clock,
  User,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Tag,
  Filter,
  ArrowUpDown
} from 'lucide-react';

const SORT_OPTIONS = [
  { value: 'newest', label: 'Más recientes' },
  { value: 'oldest', label: 'Más antiguos' },
  { value: 'popular', label: 'Más populares' },
  { value: 'active', label: 'Más activos' }
];

export default function ForumCategoryPage() {
  const { categoryId } = useParams();
  const { user } = useAuth();

  const [category, setCategory] = useState(null);
  const [posts, setPosts] = useState([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('newest');
  const [page, setPage] = useState(1);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [catRes, postsRes] = await Promise.all([
        API.get('/api/forum/categories'),
        API.get('/api/forum/posts', {
          params: {
            category: categoryId,
            sort,
            page,
            limit: 10
          }
        })
      ]);

      const cats = catRes.data.categories || catRes.data;
      const found = cats.find(c => String(c.id) === String(categoryId));
      setCategory(found || null);

      setPosts(postsRes.data.posts || []);
      setMeta({
        total: postsRes.data.total || 0,
        page: postsRes.data.page || 1,
        pages: postsRes.data.pages || 1
      });
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  }, [categoryId, sort, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    setPage(1);
  }, [sort]);

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);
    if (diffMin < 1) return 'Ahora mismo';
    if (diffMin < 60) return `hace ${diffMin} min`;
    if (diffHr < 24) return `hace ${diffHr}h`;
    if (diffDay < 30) return `hace ${diffDay}d`;
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  if (loading && !category) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-5xl mx-auto px-4 py-8">
        <Link
          to="/forum"
          className="inline-flex items-center gap-2 text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al foro
        </Link>

        <div className="bg-[#121212] border border-white/10 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[#D92B2B]/10 rounded-xl flex items-center justify-center flex-shrink-0">
                <Tag className="w-6 h-6 text-[#D92B2B]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-[#F5F5F5] mb-1">
                  {category?.name || 'Categoría'}
                </h1>
                {category?.description && (
                  <p className="text-[#A0A0A0] text-sm">{category.description}</p>
                )}
                <p className="text-[#606060] text-xs mt-2">
                  {meta.total} publicaciones
                </p>
              </div>
            </div>
            <Link
              to="/forum/new"
              className="flex items-center gap-2 px-4 py-2 bg-[#D92B2B] text-white text-sm font-medium rounded-lg hover:bg-[#F03C3C] transition-colors flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
              Nueva publicación
            </Link>
          </div>
        </div>

        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#606060]" />
            <span className="text-sm text-[#606060]">Ordenar:</span>
            <div className="relative">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="bg-[#121212] border border-white/10 rounded-lg pl-3 pr-8 py-2 text-sm text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] transition-colors appearance-none cursor-pointer"
              >
                {SORT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <ArrowUpDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[#606060] pointer-events-none" />
            </div>
          </div>
          <p className="text-sm text-[#606060]">
            {meta.total} resultados
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <div className="bg-[#121212] border border-white/10 rounded-xl p-12 text-center">
            <MessageCircle className="w-12 h-12 text-[#606060] mx-auto mb-4" />
            <p className="text-[#A0A0A0] text-lg mb-2">No hay publicaciones en esta categoría</p>
            <p className="text-[#606060] text-sm mb-6">Sé el primero en crear una publicación</p>
            <Link
              to="/forum/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#D92B2B] text-white text-sm font-medium rounded-lg hover:bg-[#F03C3C] transition-colors"
            >
              <Plus className="w-4 h-4" />
              Nueva publicación
            </Link>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {posts.map(post => (
                <Link
                  key={post.id}
                  to={`/forum/post/${post.id}`}
                  className="block bg-[#121212] border border-white/10 rounded-xl p-5 hover:border-white/20 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        {post.pinned && (
                          <span className="px-2 py-0.5 bg-[#D4AF37]/10 text-[#D4AF37] text-xs rounded-full font-medium">
                            Fijado
                          </span>
                        )}
                        {post.status === 'closed' && (
                          <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-500 text-xs rounded-full">
                            Cerrado
                          </span>
                        )}
                      </div>
                      <h3 className="text-[#F5F5F5] font-semibold group-hover:text-[#D92B2B] transition-colors mb-2 truncate">
                        {post.title}
                      </h3>
                      <p className="text-[#A0A0A0] text-sm line-clamp-2 mb-3">
                        {post.content?.substring(0, 150)}{post.content?.length > 150 ? '...' : ''}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-[#606060]">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {post.username}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(post.created_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" />
                          {post.like_count || 0}
                        </span>
                        <span className="flex items-center gap-1">
                          <MessageCircle className="w-3 h-3" />
                          {post.reply_count || 0}
                        </span>
                        {post.book_title && (
                          <span className="text-[#D4AF37]">
                            📖 {post.book_title}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {meta.pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                {Array.from({ length: meta.pages }, (_, i) => i + 1).map(p => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                      p === page
                        ? 'bg-[#D92B2B] text-white'
                        : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage(p => Math.min(meta.pages, p + 1))}
                  disabled={page >= meta.pages}
                  className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
