import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { useCart } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { Star, Eye, Heart, BookOpen, Search, Trash2, CreditCard, Clock, Truck, ShoppingCart } from 'lucide-react';
import { API } from '../config/api';

export default function HomePage() {
  const [books, setBooks] = useState([]);
  const [featuredBooks, setFeaturedBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const { user, refreshUser } = useAuth();
  const { add: addToCart } = useCart();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const ptxn = searchParams.get('_ptxn');
    if (ptxn) {
      navigate(`/checkout/result?_ptxn=${encodeURIComponent(ptxn)}`, { replace: true });
      return;
    }
    // Google OAuth backend redirect: ?oauth=success
    const oauth = searchParams.get('oauth');
    if (oauth) {
      const next = oauth === 'success' ? '/' : '/login';
      refreshUser?.();
      navigate(next, { replace: true });
    }
  }, [searchParams, navigate, refreshUser]);

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

  useEffect(() => {
    const loadFeatured = async () => {
      try {
        const { data } = await axios.get(`${API}/featured-books`);
        setFeaturedBooks(data);
      } catch (error) {
        console.error('Error al cargar libros destacados:', error);
      }
    };
    loadFeatured();
  }, []);

  const handleDeleteBook = async (bookId, e) => {
    e.preventDefault(); // Evitar que haga clic en el Link del libro
    if (!window.confirm('¿Estás seguro de que deseas eliminar este libro?')) return;

    try {
      await axios.delete(`${API}/books/${bookId}`, { withCredentials: true });
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

  const categories = ['Todos', 'Ficción', 'Clásicos', 'Ciencia Ficción', 'Terror', 'Poesía', 'Historia', 'Filosofía', 'Autoayuda', 'Romance', 'Aventura', 'Ciencia', 'Infantil'];

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-16">
      <Navbar />

      {/* Hero Section */}
      <header className="max-w-7xl mx-auto px-6 pt-14 pb-10 text-center relative">
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4 font-['Outfit'] text-balance">
          Lee, acumula Rayos y reseña en <span className="text-[#D92B2B]">Aeternum</span>
        </h1>
        <p className="text-base md:text-lg text-[#A0A0A0] max-w-2xl mx-auto">
          Compra y alquila libros digitales, pide físicos en Perú y gana recompensas por cada lectura.
        </p>
      </header>

      {/* Libros Destacados del Mes */}
      {featuredBooks.length > 0 && (
        <section className="max-w-7xl mx-auto px-6 mb-12">
          <div className="flex items-center gap-3 mb-6">
            <Star className="w-5 h-5 text-[#D4AF37] fill-[#D4AF37]" />
            <h2 className="text-xl md:text-2xl font-bold text-white font-['Outfit']">Los libros destacados de este mes</h2>
          </div>
          <div className="flex gap-6 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent" style={{ scrollbarWidth: 'thin' }}>
            {featuredBooks.map((book) => (
              <Link
                key={book.id}
                to={`/books/${book.id}`}
                className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-white/15 transition-[transform,border-color] duration-150 ease-ae-out flex flex-col relative hover:-translate-y-0.5 active:scale-[0.99] flex-shrink-0"
                style={{ width: '200px' }}
              >
                {/* Portada */}
                <div className="aspect-[3/4] overflow-hidden bg-[#181818] relative">
                  <img
                    src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"}
                    alt={book.title}
                    className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-200 ease-ae-out"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-transparent to-transparent opacity-60"></div>
                  <div className="absolute top-2 left-2 bg-[#D4AF37] text-black text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-wider">
                    Destacado
                  </div>
                </div>

                {/* Detalles */}
                <div className="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-bold tracking-wider uppercase text-[#D92B2B] mb-1 block">
                      {book.category}
                    </span>
                    <h3 className="text-sm font-semibold text-white group-hover:text-[#D92B2B] transition-colors line-clamp-1">
                      {book.title}
                    </h3>
                    <p className="text-xs text-[#A0A0A0] mt-1 line-clamp-1">
                      por {book.author_name}
                    </p>
                    <div className="flex items-center gap-1.5 mt-2">
                      {book.average_rating > 0 ? (
                        <>
                          <Star className="w-3 h-3 fill-[#D4AF37] text-[#D4AF37]" />
                          <span className="text-[11px] font-semibold text-[#D4AF37]">{book.average_rating}</span>
                          <span className="text-[11px] text-[#A0A0A0]">({book.total_reviews})</span>
                        </>
                      ) : (
                        <span className="text-[11px] text-[#A0A0A0]">Sin calificaciones</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-3">
                    <div className="flex items-center gap-2 text-[11px] text-[#A0A0A0]">
                      <span className="flex items-center gap-0.5">
                        <Eye className="w-3 h-3" />
                        {book.views}
                      </span>
                      <span className="flex items-center gap-0.5">
                        <Heart className="w-3 h-3" />
                        {book.likes}
                      </span>
                    </div>
                    <span className="text-xs font-bold text-[#D4AF37]">
                      {book.price > 0 ? `S/ ${book.price.toFixed(2)}` : 'GRATIS'}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Buscador principal */}
      <section className="max-w-3xl mx-auto px-6 mb-8">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#A0A0A0]" />
          <input
            type="text"
            placeholder="Buscar por título o autor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#121212] border border-white/10 rounded-lg pl-12 pr-4 py-3.5 text-base text-[#F5F5F5] placeholder-[#707070] focus:outline-none focus:border-[#D92B2B]/60 focus:ring-2 focus:ring-[#D92B2B]/15 transition-[border-color,box-shadow] duration-150 ease-ae-out"
          />
        </div>
      </section>

      {/* Categorías */}
      <section className="max-w-7xl mx-auto px-6 mb-10">
        <p className="text-[11px] font-bold tracking-[0.16em] uppercase text-[#A0A0A0] mb-3 px-1">Explorar por categoría</p>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === 'Todos' ? '' : cat)}
              className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide border transition-[background-color,color,border-color,transform] duration-150 ease-ae-out active:scale-[0.97] ${
                (cat === 'Todos' && !selectedCategory) || selectedCategory === cat
                  ? 'bg-[#D92B2B] text-white border-[#D92B2B]'
                  : 'bg-[#0A0A0A]/60 text-[#A0A0A0] border-white/10 hover:text-white hover:border-white/25 hover:bg-white/[0.04]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </section>

      {/* Secciones destacadas por tipo */}
      {!loading && !selectedCategory && !searchQuery && (
        <div className="max-w-7xl mx-auto px-6 mb-10 space-y-10">

          {/* Libros de pago (digitales) */}
          {books.filter(b => b.price > 0).length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-5">
                <CreditCard className="w-5 h-5 text-[#D92B2B]" />
                <h2 className="text-xl md:text-2xl font-bold text-white font-['Outfit']">Libros digitales de pago</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {books.filter(b => b.price > 0).slice(0, 4).map((book) => (
                  <Link
                    key={book.id}
                    to={`/books/${book.id}`}
                    className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-[#D92B2B]/30 transition-[transform,border-color] duration-150 ease-ae-out flex flex-col hover:-translate-y-0.5 active:scale-[0.99]"
                  >
                    <div className="aspect-[3/4] overflow-hidden bg-[#181818]">
                      <img src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"} alt={book.title} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-200 ease-ae-out" loading="lazy" />
                    </div>
                    <div className="p-4 flex-1 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold tracking-wider uppercase text-[#D92B2B]">{book.category}</span>
                        <h3 className="text-sm font-semibold text-white mt-1 line-clamp-1">{book.title}</h3>
                        <p className="text-xs text-[#A0A0A0] mt-0.5">por {book.author_name}</p>
                      </div>
                      <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-3">
                        <span className="text-xs text-[#A0A0A0] flex items-center gap-1"><Eye className="w-3 h-3" />{book.views}</span>
                        <span className="text-xs font-bold text-[#D4AF37]">S/ {parseFloat(book.price).toFixed(2)}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Libros físicos */}
          {books.filter(b => b.is_physical).length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-5">
                <Truck className="w-5 h-5 text-emerald-400" />
                <h2 className="text-xl md:text-2xl font-bold text-white font-['Outfit']">Libros físicos</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {books.filter(b => b.is_physical).slice(0, 4).map((book) => (
                  <Link
                    key={book.id}
                    to={`/books/${book.id}`}
                    className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-emerald-500/30 transition-[transform,border-color] duration-150 ease-ae-out flex flex-col hover:-translate-y-0.5 active:scale-[0.99]"
                  >
                    <div className="aspect-[3/4] overflow-hidden bg-[#181818]">
                      <img src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"} alt={book.title} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-200 ease-ae-out" loading="lazy" />
                    </div>
                    <div className="p-4 flex-1 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold tracking-wider uppercase text-emerald-400">{book.category}</span>
                        <h3 className="text-sm font-semibold text-white mt-1 line-clamp-1">{book.title}</h3>
                        <p className="text-xs text-[#A0A0A0] mt-0.5">por {book.author_name}</p>
                      </div>
                      <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-3">
                        <span className="text-xs text-[#A0A0A0] flex items-center gap-1"><Eye className="w-3 h-3" />{book.views}</span>
                        <span className="text-xs font-bold text-emerald-400">S/ {parseFloat(book.physical_price || 0).toFixed(2)}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Sección de alquiler — todos los libros digitales de pago admiten alquiler */}
          {books.filter(b => b.price > 0).length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-2">
                <Clock className="w-5 h-5 text-[#D4AF37]" />
                <h2 className="text-xl md:text-2xl font-bold text-white font-['Outfit']">Alquiler de libros</h2>
              </div>
              <p className="text-[#A0A0A0] text-sm mb-1">
                Todos los libros digitales de pago están disponibles para alquiler por 7, 14 o 30 días.
              </p>
              <p className="text-[#A0A0A0] text-xs mb-5">
                Precio de alquiler: 30% del precio de compra. Elige la duración en la página de cada libro.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {books.filter(b => b.price > 0).slice(0, 4).map((book) => (
                  <Link
                    key={book.id}
                    to={`/books/${book.id}`}
                    className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-[#D4AF37]/30 transition-[transform,border-color] duration-150 ease-ae-out flex flex-col hover:-translate-y-0.5 active:scale-[0.99]"
                  >
                    <div className="aspect-[3/4] overflow-hidden bg-[#181818]">
                      <img src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"} alt={book.title} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-200 ease-ae-out" loading="lazy" />
                    </div>
                    <div className="p-4 flex-1 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold tracking-wider uppercase text-[#D4AF37]">{book.category}</span>
                        <h3 className="text-sm font-semibold text-white mt-1 line-clamp-1">{book.title}</h3>
                        <p className="text-xs text-[#A0A0A0] mt-0.5">por {book.author_name}</p>
                      </div>
                      <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-3">
                        <span className="text-xs text-[#A0A0A0]">Alquiler desde</span>
                        <span className="text-xs font-bold text-[#D4AF37]">S/ {parseFloat(book.price * 0.3).toFixed(2)}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

        </div>
      )}

      {/* Grid de Libros */}
      <main className="max-w-7xl mx-auto px-6">
        {loading ? (
          <div className="text-center py-20 text-[#A0A0A0]">
            <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
            Cargando catálogo de libros...
          </div>
        ) : filteredBooks.length === 0 ? (
          <div className="text-center py-20 border border-white/5 bg-[#121212]/30 rounded-xl text-[#A0A0A0]">
            <BookOpen className="w-12 h-12 mx-auto mb-4 text-[#707070]" />
            <p className="text-lg font-medium">No se encontraron libros</p>
            <p className="text-sm mt-1">Intenta con otra búsqueda o categoría.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 sm:gap-5">
            {filteredBooks.map((book) => (
              <Link
                key={book.id}
                to={`/books/${book.id}`}
                className="group bg-[#121212] border border-white/5 rounded-xl overflow-hidden hover:border-white/15 transition-[transform,border-color] duration-150 ease-ae-out flex flex-col relative hover:-translate-y-0.5 active:scale-[0.99]"
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
                    className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-200 ease-ae-out"
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
                    
                    {/* Vendedor */}
                    <p className="text-xs text-[#A0A0A0] mt-1 line-clamp-1">
                      por {book.author_name}
                    </p>

                    {/* Reseñas (Estrellas) */}
                    <div className="flex items-center gap-1.5 mt-3">
                      {book.average_rating > 0 ? (
                        <>
                          <Star className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                          <span className="text-xs font-semibold text-[#D4AF37]">{book.average_rating}</span>
                          <span className="text-[11px] text-[#A0A0A0]">({book.total_reviews})</span>
                        </>
                      ) : (
                        <span className="text-[11px] text-[#A0A0A0]">Sin calificaciones</span>
                      )}
                    </div>
                  </div>

                  {/* Footer de Tarjeta */}
                  <div className="flex items-center justify-between border-t border-white/5 pt-4 mt-4">
                    <div className="flex items-center gap-3 text-[11px] text-[#A0A0A0]">
                      <span className="flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5" />
                        {book.views}
                      </span>
                      <span className="flex items-center gap-1">
                        <Heart className="w-3.5 h-3.5" />
                        {book.likes}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          addToCart(book);
                        }}
                        className="p-2 bg-[#D4AF37]/15 hover:bg-[#D4AF37] text-[#D4AF37] hover:text-black rounded-lg transition-[background-color,color,transform] duration-150 ease-ae-out active:scale-[0.97]"
                        title="Agregar al carrito"
                      >
                        <ShoppingCart className="w-4 h-4" />
                      </button>
                      <span className="text-xs font-bold text-[#D4AF37] tabular-nums">
                        {book.price > 0 ? `S/ ${parseFloat(book.price).toFixed(2)}` : 'GRATIS'}
                      </span>
                    </div>
                  </div>

                </div>

              </Link>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
