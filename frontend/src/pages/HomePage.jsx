import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { Star, Eye, Heart, BookOpen, Search, Trash2 } from 'lucide-react';

const API = 'http://localhost:8000/api';

export default function HomePage() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const { user } = useAuth();

  const loadBooks = async () => {
    setLoading(true);
    try {
      const url = selectedCategory 
        ? `${API}/books?category=${encodeURIComponent(selectedCategory)}` 
        : `${API}/books`;
      const { data } = await axios.get(url);
      setBooks(data);
    } catch (error) {
      console.error('Error al cargar libros:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBooks();
  }, [selectedCategory]);

  const handleDeleteBook = async (bookId, e) => {
    e.preventDefault(); // Evitar que haga clic en el Link del libro
    if (!window.confirm('¿Estás seguro de que deseas eliminar este libro?')) return;

    try {
      await axios.delete(`${API}/books/${bookId}`);
      loadBooks(); // Recargar catálogo
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al eliminar el libro');
    }
  };

  // Filtrar en frontend por título/autor si hay búsqueda
  const filteredBooks = books.filter(b => 
    b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.author_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const categories = ['Todos', 'Ficción', 'Clásicos', 'Ciencia', 'Negocios', 'General'];

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-16">
      <Navbar />

      {/* Hero Section */}
      <header className="max-w-7xl mx-auto px-6 pt-16 pb-12 text-center relative">
        <div className="absolute top-10 left-1/2 -translate-x-1/2 w-80 h-80 bg-[#D92B2B]/5 rounded-full blur-[80px] pointer-events-none"></div>
        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white mb-4 font-['Outfit']">
          Lee Libros, Gana <span className="text-[#D92B2B]">Rayos</span>
        </h1>
        <p className="text-lg md:text-xl text-[#A0A0A0] max-w-2xl mx-auto">
          La primera plataforma donde la lectura tiene recompensa. Acumula Rayos leyendo y deja tus reseñas y opiniones de estrellas.
        </p>
      </header>

      {/* Controles de Búsqueda y Filtro */}
      <section className="max-w-7xl mx-auto px-6 mb-12 flex flex-col md:flex-row items-center justify-between gap-6">
        
        {/* Categorías */}
        <div className="flex flex-wrap gap-2.5 justify-center md:justify-start">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === 'Todos' ? '' : cat)}
              className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wider uppercase border transition-all duration-200 ${
                (cat === 'Todos' && !selectedCategory) || selectedCategory === cat
                  ? 'bg-[#D92B2B] text-white border-[#D92B2B] shadow-lg shadow-[#D92B2B]/20'
                  : 'bg-transparent text-[#A0A0A0] border-white/10 hover:text-white hover:border-white/20'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Buscador */}
        <div className="relative w-full md:max-w-xs">
          <Search className="absolute left-3 top-3 w-4.5 h-4.5 text-[#606060]" />
          <input
            type="text"
            placeholder="Buscar libro o autor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#121212] border border-white/10 rounded-full pl-10 pr-4 py-2.5 text-sm text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
          />
        </div>

      </section>

      {/* Grid de Libros */}
      <main className="max-w-7xl mx-auto px-6">
        {loading ? (
          <div className="text-center py-20 text-[#A0A0A0]">
            <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
            Cargando catálogo de libros...
          </div>
        ) : filteredBooks.length === 0 ? (
          <div className="text-center py-20 border border-white/5 bg-[#121212]/30 rounded-2xl text-[#A0A0A0]">
            <BookOpen className="w-12 h-12 mx-auto mb-4 text-[#404040]" />
            <p className="text-lg font-medium">No se encontraron libros</p>
            <p className="text-sm mt-1">Intenta con otra búsqueda o categoría.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
            {filteredBooks.map((book) => (
              <Link
                key={book.id}
                to={`/books/${book.id}`}
                className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-white/10 transition-all duration-300 flex flex-col relative shadow-xl hover:-translate-y-1"
              >
                
                {/* Botón de Borrar (Admin) */}
                {user && user.role === 'admin' && (
                  <button
                    onClick={(e) => handleDeleteBook(book.id, e)}
                    className="absolute top-3 right-3 p-2 bg-[#0A0A0A]/80 hover:bg-[#D92B2B] text-white hover:text-white rounded-lg transition-all duration-200 z-10 opacity-0 group-hover:opacity-100 backdrop-blur-sm"
                    title="Eliminar Libro"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}

                {/* Portada */}
                <div className="aspect-[3/4] overflow-hidden bg-[#181818] relative">
                  <img
                    src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"}
                    alt={book.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-transparent to-transparent opacity-60"></div>
                </div>

                {/* Detalles */}
                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    {/* Categoría */}
                    <span className="text-[10px] font-bold tracking-wider uppercase text-[#D92B2B] mb-1.5 block">
                      {book.category}
                    </span>
                    
                    {/* Título */}
                    <h3 className="text-base font-semibold text-white group-hover:text-[#D92B2B] transition-colors line-clamp-1">
                      {book.title}
                    </h3>
                    
                    {/* Autor */}
                    <p className="text-xs text-[#A0A0A0] mt-1 line-clamp-1">
                      por {book.author_name}
                    </p>

                    {/* Reseñas (Estrellas) */}
                    <div className="flex items-center gap-1.5 mt-3">
                      {book.average_rating > 0 ? (
                        <>
                          <Star className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                          <span className="text-xs font-semibold text-[#D4AF37]">{book.average_rating}</span>
                          <span className="text-[10px] text-[#606060]">({book.total_reviews})</span>
                        </>
                      ) : (
                        <span className="text-[10px] text-[#606060]">Sin calificaciones</span>
                      )}
                    </div>
                  </div>

                  {/* Footer de Tarjeta */}
                  <div className="flex items-center justify-between border-t border-white/5 pt-4 mt-4">
                    <div className="flex items-center gap-3 text-[11px] text-[#606060]">
                      <span className="flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5" />
                        {book.views}
                      </span>
                      <span className="flex items-center gap-1">
                        <Heart className="w-3.5 h-3.5" />
                        {book.likes}
                      </span>
                    </div>
                    <span className="text-xs font-bold text-[#D4AF37]">
                      {book.price > 0 ? `$${book.price.toFixed(2)}` : 'GRATIS'}
                    </span>
                  </div>

                </div>

              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
