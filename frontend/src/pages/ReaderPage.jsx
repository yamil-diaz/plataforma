import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { ChevronLeft, ChevronRight, Heart, Zap, Star, Send, Download, Eye, ThumbsUp, ThumbsDown } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

import { API } from '../config/api';

const StarRating = ({ rating, onRatingChange, interactive = false }) => {
  const [hoverRating, setHoverRating] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={!interactive}
          onMouseEnter={() => interactive && setHoverRating(star)}
          onMouseLeave={() => interactive && setHoverRating(0)}
          onClick={() => interactive && onRatingChange(star)}
          className={`${interactive ? 'cursor-pointer' : 'cursor-default'} transition-colors`}
        >
          <Star
            className={`w-5 h-5 ${
              star <= (hoverRating || rating)
                ? 'fill-[#D4AF37] text-[#D4AF37]'
                : 'text-[#A0A0A0]'
            }`}
          />
        </button>
      ))}
    </div>
  );
};

export default function ReaderPage() {
  const { bookId } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showReward, setShowReward] = useState(false);
  const [rewardMessage, setRewardMessage] = useState('');
  const [reviews, setReviews] = useState([]);
  const [newReview, setNewReview] = useState({ rating: 5, comment: '' });
  const [submittingReview, setSubmittingReview] = useState(false);
  const [userInteraction, setUserInteraction] = useState(null);
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  // Estado del lector paginado (FASE 2)
  const [paginated, setPaginated] = useState(true);
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageContent, setPageContent] = useState('');
  const [chapterTitle, setChapterTitle] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [daily, setDaily] = useState({ pages: 0, goal: 15, completed: false, reward_claimed: false, books: [] });
  const [readerLoading, setReaderLoading] = useState(false);
  const reportingRef = useRef(false);
  const pageRequestRef = useRef(0);

  const reportProgress = async (pageNumber) => {
    if (!user || reportingRef.current) return;
    reportingRef.current = true;
    try {
      const { data } = await axios.post(
        `${API}/books/${bookId}/progress`,
        { page: pageNumber },
        { withCredentials: true }
      );
      if (data.daily) setDaily(data.daily);
      if (data.rewarded) {
        setRewardMessage(`¡Meta diaria de ${data.daily.goal} páginas completada! +${data.reward_amount} Rayos`);
        setShowReward(true);
        refreshUser();
        setTimeout(() => setShowReward(false), 4000);
      }
    } catch (error) {
      console.error('Error reportando progreso:', error);
    } finally {
      reportingRef.current = false;
    }
  };

  const goToPage = async (pageNumber) => {
    if (pageNumber < 1) return;
    const requestId = ++pageRequestRef.current;
    setReaderLoading(true);
    try {
      const { data: pageData } = await axios.get(
        `${API}/books/${bookId}/pages/${pageNumber}`,
        { withCredentials: true }
      );
      if (requestId !== pageRequestRef.current) return;
      setPaginated(true);
      setPageNum(pageNumber);
      setPageContent(pageData.content);
      setChapterTitle(pageData.chapter_title || null);
      setTotalPages(pageData.total_pages);
      reportProgress(pageNumber);
    } catch (error) {
      if (requestId !== pageRequestRef.current) return;
      if (error.response?.status === 404) {
        setPaginated(false);
      }
    } finally {
      if (requestId === pageRequestRef.current) setReaderLoading(false);
    }
  };

  const goPrev = () => {
    if (pageNum > 1) goToPage(pageNum - 1);
  };

  const goNext = () => {
    if (pageNum < totalPages) goToPage(pageNum + 1);
  };

  const loadReviews = async (bId) => {
    try {
      const { data } = await axios.get(`${API}/books/${bId}/reviews`);
      setReviews(data);
    } catch (error) {
      console.error('Error loading reviews:', error);
    }
  };

  const loadBook = async () => {
    try {
      const { data: bookDetails } = await axios.get(`${API}/books/${bookId}`);
      setBook(bookDetails);

      if (user) {
        try {
          const { data: interactData } = await axios.get(`${API}/books/${bookId}/interaction`, { withCredentials: true });
          setUserInteraction(interactData.interaction);
        } catch(e) {}
      }

      loadReviews(bookDetails._id || bookDetails.id);

      // FASE 2: iniciar sesión de lectura y reanudar donde quedó
      let resumePage = 1;
      try {
        const { data: startData } = await axios.post(
          `${API}/books/${bookId}/start`,
          {},
          { withCredentials: true }
        );
        if (startData.total_pages > 0) {
          setTotalPages(startData.total_pages);
          if (startData.last_page) resumePage = startData.last_page;
        } else {
          setPaginated(false);
        }
      } catch (error) {
        console.error('Error iniciando sesión de lectura:', error);
      }

      try {
        const { data: chaptersData } = await axios.get(`${API}/books/${bookId}/chapters`, { withCredentials: true });
        setChapters(chaptersData || []);
      } catch (error) {}

      try {
        const { data: todayData } = await axios.get(`${API}/reading/today`, { withCredentials: true });
        setDaily(todayData);
      } catch (error) {}

      await goToPage(resumePage);
    } catch (error) {
      console.error('Error loading book:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    if (!newReview.comment.trim()) return;

    setSubmittingReview(true);
    try {
      await axios.post(
        `${API}/books/${book._id || book.id}/reviews`,
        newReview,
        { withCredentials: true }
      );
      setNewReview({ rating: 5, comment: '' });
      loadReviews(book._id || book.id);
      // Recargar libro para actualizar el promedio de calificaciones
      const { data: bookDetails } = await axios.get(`${API}/books/${book._id || book.id}`);
      setBook(bookDetails);
    } catch (error) {
      console.error('Error submitting review:', error);
      alert(error.response?.data?.detail || 'Error al publicar el comentario');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleInteract = async (action) => {
    if (!user) {
      alert("Debes iniciar sesión para reaccionar");
      return;
    }
    try {
      const { data } = await axios.post(`${API}/books/${bookId}/interact`, { action }, { withCredentials: true });
      setUserInteraction(data.interaction);
      setBook(prev => ({ ...prev, likes: data.likes, dislikes: data.dislikes }));
    } catch (error) {
      alert("Error al registrar interacción");
    }
  };

  useEffect(() => {
    loadBook();
  }, [bookId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="text-center py-40 text-[#A0A0A0]">
          <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
          Abriendo el libro en el lector...
        </div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="text-center py-40 text-[#A0A0A0]">
          <p className="text-lg">El libro no pudo ser encontrado.</p>
          <button onClick={() => navigate('/')} className="mt-4 bg-[#D92B2B] text-white px-4 py-2 rounded-md hover:bg-[#F03C3C]">
            Volver al catálogo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />

      <div className="max-w-4xl mx-auto px-6 pt-8">
        
        {/* Botón Volver */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          Volver al catálogo
        </button>

        {/* Contenedor del Libro */}
        <div className="bg-[#121212] border border-white/10 rounded-lg p-8 md:p-12 shadow-xl">
          
          {/* Cabecera del Libro */}
          <div className="mb-8 pb-8 border-b border-white/10">
            <h1 className="text-3xl md:text-5xl font-['Lora'] font-bold text-white mb-2 leading-tight">
              {book.title}
            </h1>
            <p className="text-[#A0A0A0] text-lg" data-testid="reader-author-name">
              por {book.author_name}
            </p>
            <div className="flex flex-wrap items-center gap-6 mt-4 text-sm text-[#A0A0A0]">
              <span data-testid="reader-book-views">{book.views} vistas</span>
              <span className="flex items-center gap-1" data-testid="reader-book-likes">
                <Heart className="w-4 h-4" />
                {book.likes}
              </span>
              {book.average_rating > 0 && (
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4 fill-[#D4AF37] text-[#D4AF37]" />
                  <span className="text-[#D4AF37] font-medium">{book.average_rating}</span>
                  <span>({book.total_reviews} reseñas)</span>
                </div>
              )}
            </div>
          </div>

          {/* Botón de Descarga PDF */}
            <div className="mt-6">
              <a
                href={`${API}/books/${book._id || book.id}/download`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold px-6 py-3 rounded-lg transition-all duration-200 shadow-lg shadow-[#D92B2B]/20"
              >
                <Download className="w-5 h-5" />
                Descargar PDF
              </a>
            </div>

          {/* Contenido de Lectura (FASE 2: lector paginado) */}
          <div className="border-t border-white/10 pt-8">
            {/* Barra de Meta Diaria */}
            <div className="bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-xl px-4 py-3 mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#D4AF37] tracking-wider uppercase flex items-center gap-1.5">
                  <Zap className="w-4 h-4 fill-[#D4AF37]" />
                  Meta diaria de lectura
                </span>
                <span className="text-sm font-bold text-white" data-testid="daily-goal-counter">
                  {Math.min(daily.pages, daily.goal)}/{daily.goal} páginas hoy
                </span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#D4AF37] to-[#D92B2B] rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, (daily.pages / (daily.goal || 1)) * 100)}%` }}
                ></div>
              </div>
              {daily.completed && (
                <p className="text-xs text-[#D4AF37] mt-2" data-testid="daily-goal-completed">
                  ¡Meta diaria completada!
                </p>
              )}
            </div>

            {paginated ? (
              <div>
                {/* Navegación de Capítulos */}
                {chapters.length > 0 && (
                  <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
                    {chapters.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => goToPage(c.start_page)}
                        className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                          pageNum === c.start_page
                            ? 'bg-[#D92B2B]/20 text-white border-[#D92B2B]/40'
                            : 'bg-white/5 text-[#A0A0A0] border-white/10 hover:text-white'
                        }`}
                      >
                        {c.title}
                      </button>
                    ))}
                  </div>
                )}

                {/* Controles: Anterior | Capítulo • Página N/M | Siguiente */}
                <div className="flex items-center justify-between gap-3 mb-6">
                  <button
                    onClick={goPrev}
                    disabled={pageNum <= 1 || readerLoading}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    data-testid="reader-prev-page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Anterior
                  </button>
                  <div className="text-center text-sm text-[#A0A0A0]">
                    {pageNum === totalPages ? (
                      <span className="text-[#D4AF37] font-semibold" data-testid="reader-page-indicator">Fin del libro</span>
                    ) : (
                      <span data-testid="reader-page-indicator">
                        {chapterTitle ? `${chapterTitle} • ` : ''}Página {pageNum} de {totalPages}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={goNext}
                    disabled={pageNum >= totalPages || readerLoading}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#D92B2B] hover:bg-[#F03C3C] text-white text-sm font-semibold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    data-testid="reader-next-page"
                  >
                    Siguiente
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                {/* Título del capítulo al inicio del rango */}
                {chapters.find((c) => c.start_page === pageNum) && chapterTitle && (
                  <h2 className="font-['Lora'] text-2xl font-bold text-[#F5F5F5] mb-6 text-center" data-testid="reader-chapter-title">
                    {chapterTitle}
                  </h2>
                )}

                {readerLoading ? (
                  <div className="text-center py-16 text-[#A0A0A0]">
                    <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
                    Cargando página...
                  </div>
                ) : (
                  <div
                    className="font-['Merriweather'] text-[#F5F5F5] text-lg leading-relaxed"
                    style={{ lineHeight: '1.8' }}
                    data-testid="reader-book-content"
                  >
                    {pageContent.split('\n').map((paragraph, index) => (
                      <p key={index} className="mb-6">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              /* Libros sin paginación: contenido completo legado */
              <div
                className="font-['Merriweather'] text-[#F5F5F5] text-lg leading-relaxed"
                style={{ lineHeight: '1.8' }}
                data-testid="reader-book-content"
              >
                {book.content.split('\n').map((paragraph, index) => (
                  <p key={index} className="mb-6">
                    {paragraph}
                  </p>
                ))}
              </div>
            )}
          </div>

        </div>

        {/* Barra de Interacciones (Likes/Dislikes/Vistas) */}
        <div className="bg-[#121212] border border-white/10 rounded-lg p-6 shadow-xl mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-[#A0A0A0]">
            <Eye className="w-5 h-5 text-[#00D4C5]" />
            <span className="font-semibold text-white">{book.views}</span>
            <span className="text-sm">Vistas totales</span>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={() => handleInteract('like')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full font-bold transition-all ${userInteraction === 'like' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-white/5 text-[#A0A0A0] hover:bg-white/10 hover:text-white border border-white/5'}`}
            >
              <ThumbsUp className={`w-4 h-4 ${userInteraction === 'like' ? 'fill-emerald-400' : ''}`} />
              {book.likes || 0}
            </button>
            <button 
              onClick={() => handleInteract('dislike')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full font-bold transition-all ${userInteraction === 'dislike' ? 'bg-red-500/20 text-red-500 border border-red-500/30' : 'bg-white/5 text-[#A0A0A0] hover:bg-white/10 hover:text-white border border-white/5'}`}
            >
              <ThumbsDown className={`w-4 h-4 ${userInteraction === 'dislike' ? 'fill-red-500' : ''}`} />
              {book.dislikes || 0}
            </button>
          </div>
        </div>

        {/* Sección de Reseñas */}
        <div className="bg-[#121212] border border-white/10 rounded-lg p-8 md:p-12 shadow-xl mt-8" data-testid="reviews-section">
          <h2 className="text-3xl font-['Lora'] font-semibold text-[#F5F5F5] mb-8">Reseñas</h2>

          {/* Formulario de Reseña */}
          <div className="mb-12 pb-8 border-b border-white/10">
            <h3 className="text-xl font-['Lora'] text-[#F5F5F5] mb-4">Deja tu reseña</h3>
            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div>
                <label className="block text-[#F5F5F5] text-sm font-medium mb-2">
                  Calificación
                </label>
                <StarRating
                  rating={newReview.rating}
                  onRatingChange={(rating) => setNewReview({ ...newReview, rating })}
                  interactive={true}
                />
              </div>
              <div>
                <label className="block text-[#F5F5F5] text-sm font-medium mb-2">
                  Tu opinión
                </label>
                <textarea
                  value={newReview.comment}
                  onChange={(e) => setNewReview({ ...newReview, comment: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-sm px-4 py-3 text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] transition-colors min-h-[120px]"
                  placeholder="Comparte tu opinión sobre este libro..."
                  required
                  data-testid="review-comment-input"
                />
              </div>
              <button
                type="submit"
                disabled={submittingReview}
                className="bg-[#D92B2B] text-white hover:bg-[#F03C3C] transition-colors rounded-sm px-6 py-3 font-medium tracking-wide flex items-center gap-2 disabled:opacity-50"
                data-testid="submit-review-btn"
              >
                <Send className="w-5 h-5" />
                {submittingReview ? 'Publicando...' : 'Publicar Comentario'}
              </button>
            </form>
          </div>

          {/* Listado de Reseñas */}
          <div className="space-y-6">
            {reviews.length > 0 ? (
              reviews.map((review, index) => (
                <div
                  key={review._id}
                  className="pb-6 border-b border-white/5 last:border-0"
                  data-testid={`review-item-${index}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-[#F5F5F5] font-medium mb-1">{review.user_name}</div>
                      <StarRating rating={review.rating} interactive={false} />
                    </div>
                    <div className="text-[#A0A0A0] text-sm">
                      {new Date(review.created_at).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </div>
                  </div>
                  <p className="text-[#F5F5F5] leading-relaxed">{review.comment}</p>
                </div>
              ))
            ) : (
              <div className="text-center text-[#A0A0A0] py-8" data-testid="no-reviews-message">
                <p>Aún no hay reseñas para este libro. ¡Sé el primero en dejar una!</p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Notificación de Recompensa de Meta Diaria */}
      {showReward && (
        <div
          className="fixed top-24 right-6 bg-[#D4AF37]/20 border border-[#D4AF37] rounded-lg px-6 py-4 flex items-center gap-3 shadow-xl backdrop-blur-sm z-50 animate-bounce"
          data-testid="rayos-reward-notification"
        >
          <Zap className="w-6 h-6 text-[#D4AF37]" />
          <div>
            <div className="text-[#F5F5F5] font-medium">{rewardMessage}</div>
            <div className="text-[#A0A0A0] text-sm">Sigue leyendo para ganar más</div>
          </div>
        </div>
      )}
    </div>
  );
}
