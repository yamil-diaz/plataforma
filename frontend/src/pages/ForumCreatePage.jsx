import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { API } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { Navbar } from '../components/Navbar';
import {
  ArrowLeft,
  Send,
  Loader2,
  FileText,
  Tag,
  BookOpen,
  AlertCircle
} from 'lucide-react';

export default function ForumCreatePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [bookId, setBookId] = useState('');
  const [errors, setErrors] = useState({});

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await API.get('/api/forum/categories');
        setCategories(res.data.categories || res.data);
      } catch (err) {
        console.error('Error fetching categories:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCategories();
  }, []);

  const validate = () => {
    const newErrors = {};

    if (!title.trim()) {
      newErrors.title = 'El título es obligatorio';
    } else if (title.trim().length < 3) {
      newErrors.title = 'El título debe tener al menos 3 caracteres';
    } else if (title.trim().length > 200) {
      newErrors.title = 'El título no puede exceder 200 caracteres';
    }

    if (!content.trim()) {
      newErrors.content = 'El contenido es obligatorio';
    } else if (content.trim().length < 10) {
      newErrors.content = 'El contenido debe tener al menos 10 caracteres';
    } else if (content.trim().length > 10000) {
      newErrors.content = 'El contenido no puede exceder 10,000 caracteres';
    }

    if (!categoryId) {
      newErrors.categoryId = 'Selecciona una categoría';
    }

    if (bookId && (isNaN(bookId) || parseInt(bookId) < 1)) {
      newErrors.bookId = 'El ID del libro debe ser un número positivo';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        category_id: parseInt(categoryId)
      };
      if (bookId.trim()) {
        payload.book_id = parseInt(bookId);
      }
      const res = await API.post('/api/forum/posts', payload);
      navigate(`/forum/post/${res.data.post.id}`);
    } catch (err) {
      console.error('Error creating post:', err);
      if (err.response?.data?.error) {
        setErrors({ submit: err.response.data.error });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link
          to="/forum"
          className="inline-flex items-center gap-2 text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al foro
        </Link>

        <div className="bg-[#121212] border border-white/10 rounded-xl p-6">
          <h1 className="text-2xl font-bold text-[#F5F5F5] mb-6 flex items-center gap-3">
            <FileText className="w-6 h-6 text-[#D92B2B]" />
            Nueva publicación
          </h1>

          {errors.submit && (
            <div className="bg-[#D92B2B]/10 border border-[#D92B2B]/30 rounded-lg p-4 mb-6 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-[#D92B2B] flex-shrink-0" />
              <p className="text-[#F03C3C] text-sm">{errors.submit}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Título
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Título de tu publicación"
                maxLength={200}
                className={`w-full bg-[#0A0A0A] border rounded-lg px-4 py-3 text-[#F5F5F5] text-sm focus:outline-none focus:border-[#D92B2B] transition-colors ${
                  errors.title ? 'border-[#D92B2B]' : 'border-white/10'
                }`}
              />
              <div className="flex items-center justify-between mt-1">
                {errors.title ? (
                  <p className="text-[#D92B2B] text-xs">{errors.title}</p>
                ) : (
                  <span />
                )}
                <span className={`text-xs ${title.length > 180 ? 'text-[#D92B2B]' : 'text-[#606060]'}`}>
                  {title.length}/200
                </span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Categoría
              </label>
              {loading ? (
                <div className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-sm text-[#606060]">
                  Cargando categorías...
                </div>
              ) : (
                <div className="relative">
                  <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#606060]" />
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className={`w-full bg-[#0A0A0A] border rounded-lg pl-10 pr-4 py-3 text-[#F5F5F5] text-sm focus:outline-none focus:border-[#D92B2B] transition-colors appearance-none cursor-pointer ${
                      errors.categoryId ? 'border-[#D92B2B]' : 'border-white/10'
                    }`}
                  >
                    <option value="">Selecciona una categoría</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name} {cat.description ? `- ${cat.description}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {errors.categoryId && (
                <p className="text-[#D92B2B] text-xs mt-1">{errors.categoryId}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Libro asociado (opcional)
              </label>
              <div className="relative">
                <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#606060]" />
                <input
                  type="number"
                  value={bookId}
                  onChange={(e) => setBookId(e.target.value)}
                  placeholder="ID del libro (opcional)"
                  min="1"
                  className={`w-full bg-[#0A0A0A] border rounded-lg pl-10 pr-4 py-3 text-[#F5F5F5] text-sm focus:outline-none focus:border-[#D92B2B] transition-colors ${
                    errors.bookId ? 'border-[#D92B2B]' : 'border-white/10'
                  }`}
                />
              </div>
              {errors.bookId && (
                <p className="text-[#D92B2B] text-xs mt-1">{errors.bookId}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Contenido
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Escribe el contenido de tu publicación..."
                rows={10}
                maxLength={10000}
                className={`w-full bg-[#0A0A0A] border rounded-lg px-4 py-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors ${
                  errors.content ? 'border-[#D92B2B]' : 'border-white/10'
                }`}
              />
              <div className="flex items-center justify-between mt-1">
                {errors.content ? (
                  <p className="text-[#D92B2B] text-xs">{errors.content}</p>
                ) : (
                  <span />
                )}
                <span className={`text-xs ${content.length > 9500 ? 'text-[#D92B2B]' : 'text-[#606060]'}`}>
                  {content.length.toLocaleString()}/10,000
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
              <Link
                to="/forum"
                className="px-6 py-2.5 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
              >
                Cancelar
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 px-6 py-2.5 bg-[#D92B2B] text-white text-sm font-medium rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Publicar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
