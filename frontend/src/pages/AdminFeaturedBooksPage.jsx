import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import axios from 'axios';
import { Star, ArrowLeft, Plus, X, ChevronUp, ChevronDown, Search, BookOpen, GripVertical } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function AdminFeaturedBooksPage() {
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Búsqueda de libros
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    fetchFeatured();
  }, []);

  const fetchFeatured = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.get(`${API}/admin/featured-books`, { withCredentials: true });
      setFeatured(data.featured || []);
      setHasChanges(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cargar los libros destacados');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const { data } = await axios.get(`${API}/books`, { withCredentials: true });
      const query = searchQuery.toLowerCase();
      const results = data.filter(b =>
        b.title.toLowerCase().includes(query) ||
        b.author_name.toLowerCase().includes(query)
      );
      setSearchResults(results);
    } catch (err) {
      setError('Error al buscar libros');
    } finally {
      setSearching(false);
    }
  };

  const handleAddBook = (book) => {
    if (featured.length >= 20) {
      setError('Máximo 20 libros destacados');
      return;
    }
    if (featured.some(f => f.book_id === book.id)) {
      setError('Este libro ya está en los destacados');
      return;
    }
    setFeatured([...featured, {
      book_id: book.id,
      title: book.title,
      author_name: book.author_name,
      category: book.category,
      price: book.price,
      cover_image_url: book.cover_image_url,
      display_order: featured.length,
    }]);
    setHasChanges(true);
    setSearchResults([]);
    setSearchQuery('');
    setShowSearch(false);
    setSuccess('');
    setError('');
  };

  const handleRemoveBook = (bookId) => {
    setFeatured(featured.filter(f => f.book_id !== bookId));
    setHasChanges(true);
    setSuccess('');
  };

  const handleMoveUp = (index) => {
    if (index === 0) return;
    const updated = [...featured];
    [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
    updated.forEach((f, i) => f.display_order = i);
    setFeatured(updated);
    setHasChanges(true);
  };

  const handleMoveDown = (index) => {
    if (index === featured.length - 1) return;
    const updated = [...featured];
    [updated[index], updated[index + 1]] = [updated[index + 1], updated[index]];
    updated.forEach((f, i) => f.display_order = i);
    setFeatured(updated);
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const bookIds = featured.map(f => f.book_id);
      await axios.put(`${API}/admin/featured-books`, { book_ids: bookIds }, { withCredentials: true });
      setSuccess('Libros destacados guardados correctamente');
      setHasChanges(false);
      fetchFeatured();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar los libros destacados');
    } finally {
      setSaving(false);
    }
  };

  const formatPrice = (price) => {
    return price > 0 ? `$${Number(price).toFixed(2)}` : 'GRATIS';
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl mx-auto px-6 pt-12 w-full">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#A0A0A0] hover:text-white transition-colors mb-6 text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Volver al Panel
        </Link>

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
          <div className="flex items-center gap-3">
            <Star className="w-7 h-7 text-[#D4AF37]" />
            <div>
              <h1 className="text-3xl font-bold text-white font-['Outfit']">Libros Destacados del Mes</h1>
              <p className="text-sm text-[#A0A0A0] mt-1">
                Gestiona los libros que aparecen destacados en la página principal.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className={`text-sm font-semibold px-3 py-1.5 rounded-lg ${featured.length >= 20 ? 'bg-red-500/10 text-red-500 border border-red-500/30' : 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/30'}`}>
              {featured.length} / 20 libros
            </span>
            <button
              onClick={() => { setError(''); setShowSearch(!showSearch); }}
              disabled={featured.length >= 20}
              className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" /> Agregar libro
            </button>
          </div>
        </div>

        {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6 font-medium">{error}</div>}
        {success && <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-lg text-sm mb-6 font-medium">{success}</div>}

        {/* Panel de búsqueda */}
        {showSearch && (
          <div className="bg-[#121212] border border-white/10 rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Buscar libros para destacar</h2>
              <button onClick={() => { setShowSearch(false); setSearchResults([]); setSearchQuery(''); }} className="text-[#A0A0A0] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex gap-3 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 w-4 h-4 text-[#606060]" />
                <input
                  type="text"
                  placeholder="Buscar por título o autor..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={searching}
                className="bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {searching ? 'Buscando...' : 'Buscar'}
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="max-h-64 overflow-y-auto space-y-2">
                {searchResults.map(book => {
                  const isFeatured = featured.some(f => f.book_id === book.id);
                  return (
                    <div key={book.id} className="flex items-center gap-3 p-3 bg-[#0A0A0A] border border-white/5 rounded-lg hover:border-white/10 transition-colors">
                      <img src={book.cover_image_url || 'https://via.placeholder.com/40'} alt={book.title} className="w-10 h-14 object-cover rounded border border-white/10" />
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-medium truncate">{book.title}</p>
                        <p className="text-[#A0A0A0] text-xs truncate">{book.author_name} · {book.category} · {formatPrice(book.price)}</p>
                      </div>
                      <button
                        onClick={() => handleAddBook(book)}
                        disabled={isFeatured || featured.length >= 20}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                          isFeatured
                            ? 'bg-[#404040]/10 text-[#505050] border-[#303030] cursor-not-allowed'
                            : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-emerald-500/30'
                        }`}
                      >
                        <Plus className="w-3 h-3" />
                        {isFeatured ? 'Ya destacado' : 'Agregar'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
            {searchQuery && !searching && searchResults.length === 0 && (
              <p className="text-[#A0A0A0] text-sm text-center py-4">No se encontraron libros.</p>
            )}
          </div>
        )}

        {/* Lista de destacados */}
        {loading ? (
          <div className="text-center text-[#A0A0A0] py-20">Cargando libros destacados...</div>
        ) : featured.length === 0 ? (
          <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
            <BookOpen className="w-12 h-12 mx-auto mb-4 text-[#404040]" />
            <p className="text-[#A0A0A0] mb-4">No hay libros destacados este mes.</p>
            <button onClick={() => setShowSearch(true)} className="text-[#D92B2B] hover:underline font-semibold">Agrega el primer libro destacado</button>
          </div>
        ) : (
          <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                    <th className="p-4 font-semibold w-12">#</th>
                    <th className="p-4 font-semibold">Libro</th>
                    <th className="p-4 font-semibold">Categoría</th>
                    <th className="p-4 font-semibold text-center">Precio</th>
                    <th className="p-4 font-semibold text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {featured.map((item, index) => (
                    <tr key={item.book_id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                      <td className="p-4 text-[#D4AF37] font-bold text-sm">{index + 1}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <img
                            src={item.cover_image_url || 'https://via.placeholder.com/40'}
                            alt={item.title}
                            className="w-10 h-14 object-cover rounded border border-white/10 shadow-md"
                          />
                          <div className="min-w-0">
                            <p className="text-white font-medium text-sm truncate max-w-[250px]">{item.title}</p>
                            <p className="text-[#A0A0A0] text-xs truncate">{item.author_name}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-[#A0A0A0] text-sm">{item.category}</td>
                      <td className="p-4 text-center text-xs font-bold text-[#D4AF37]">{formatPrice(item.price)}</td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => handleMoveUp(index)}
                            disabled={index === 0}
                            className="p-1.5 text-[#A0A0A0] hover:text-white hover:bg-white/10 rounded transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
                            title="Mover arriba"
                          >
                            <ChevronUp className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleMoveDown(index)}
                            disabled={index === featured.length - 1}
                            className="p-1.5 text-[#A0A0A0] hover:text-white hover:bg-white/10 rounded transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
                            title="Mover abajo"
                          >
                            <ChevronDown className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleRemoveBook(item.book_id)}
                            className="p-1.5 text-red-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors ml-1"
                            title="Quitar de destacados"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Botón guardar */}
        {featured.length > 0 && (
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-all ${
                hasChanges
                  ? 'bg-[#D4AF37] hover:bg-[#F2D06B] text-black shadow-lg shadow-[#D4AF37]/20'
                  : 'bg-white/5 text-[#505050] cursor-not-allowed'
              } disabled:opacity-50`}
            >
              {saving ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
