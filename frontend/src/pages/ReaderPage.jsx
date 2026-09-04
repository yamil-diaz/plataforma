import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import PDFViewer from '../components/PDFViewer';
import ThumbnailSidebar from '../components/ThumbnailSidebar';
import ReaderToolbar from '../components/ReaderToolbar';
import BookPreviewModal from '../components/BookPreviewModal';
import { ChevronLeft, Heart, Zap, Star, Send, Download, Eye, ThumbsUp, ThumbsDown } from 'lucide-react';
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
  const [paginated, setPaginated] = useState(null);
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(null);
  const [pageContent, setPageContent] = useState('');
  const [chapterTitle, setChapterTitle] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [daily, setDaily] = useState({ pages: 0, goal: 15, completed: false, reward_claimed: false, books: [] });
  const [readerLoading, setReaderLoading] = useState(false);
  const [readerError, setReaderError] = useState(null);
  const reportingRef = useRef(false);
  const pageRequestRef = useRef(0);

  // PDF viewer states (new)
  const [zoom, setZoom] = useState(1.0);
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [pdfTotalPages, setPdfTotalPages] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

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
    setReaderError(null);
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
      // Solo actualizar totalPages si no estaba seteado (o para validar)
      if (totalPages === null) {
        setTotalPages(pageData.total_pages);
      }
      reportProgress(pageNumber);
    } catch (error) {
      if (requestId !== pageRequestRef.current) return;
      if (error.response?.status === 404) {
        setPaginated(false);
        setTotalPages(0);
      } else {
        setReaderError('Error cargando la página. Verifica tu conexión e inténtalo de nuevo.');
        // No borramos totalPages válido ya establecido por /start
      }
    } finally {
      if (requestId === pageRequestRef.current) setReaderLoading(false);
    }
  };

  const goPrev = () => {
    if (pageNum > 1) goToPage(pageNum - 1);
  };

  const goNext = () => {
    if (totalPages && pageNum < totalPages) goToPage(pageNum + 1);
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
          setPaginated(true);
          if (startData.last_page) resumePage = startData.last_page;
        } else {
          setTotalPages(0);
          setPaginated(false);
        }
      } catch (error) {
        console.error('Error iniciando sesión de lectura:', error);
        setReaderError('No se pudo iniciar la lectura. Intenta recargar la página.');
        setPaginated(false);
        setTotalPages(0);
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

  // PDF viewer handlers (new)
  const handleDocumentLoaded = (doc) => {
    setPdfDocument(doc);
    setPdfError(null);
    if (doc && doc.numPages) {
      setPdfTotalPages(doc.numPages);
      if (totalPages !== null && doc.numPages !== totalPages) {
        console.warn(`[PDF] Discrepancia detectada: PDF tiene ${doc.numPages} páginas, API dice ${totalPages}`);
      }
    }
  };

  const handleZoomChange = (newZoom) => {
    setZoom(Math.max(0.5, Math.min(3.0, newZoom)));
  };

  const handleToggleSidebar = () => {
    setSidebarVisible(prev => !prev);
  };

  const handlePdfError = (error) => {
    setPdfError(error?.message || 'Error al cargar el PDF');
  };

  // PDF page change handler — wraps goToPage, but caps at totalPages (API limit)
  const handlePdfPageChange = (newPage) => {
    if (totalPages && newPage > totalPages) {
      console.warn(`[PDF] Navegación bloqueada: intento de página ${newPage} pero totalPages (API) es ${totalPages}`);
      return;
    }
    goToPage(newPage);
  };

  useEffect(() => {
    loadBook();
  }, [bookId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="text-center py-20 sm:py-40 text-[#A0A0A0]">
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
        <div className="text-center py-20 sm:py-40 text-[#A0A0A0]">
          <p className="text-lg">El libro no pudo ser encontrado.</p>
          <button onClick={() => navigate('/')} className="mt-4 bg-[#D92B2B] text-white px-4 py-2 rounded-md hover:bg-[#F03C3C]">
            Volver al catálogo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24 overflow-x-hidden">
      <Navbar />

      <div className="max-w-6xl mx-auto px-3 sm:px-6 pt-4 sm:pt-8">
        
        {/* Botón Volver */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          Volver al catálogo
        </button>

        {/* Contenedor del Libro */}
        <div className="bg-[#121212] border border-white/10 rounded-lg p-4 sm:p-8 md:p-12 shadow-xl">
          
          {/* Cabecera del Libro */}
          <div className="mb-6 sm:mb-8 pb-6 sm:pb-8 border-b border-white/10">
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

          {/* Botones: Vista previa + Descarga PDF */}
            <div className="flex flex-wrap items-center gap-3 mt-4 sm:mt-6">
              {book.pdf_path && (
                <button
                  onClick={() => setShowPreview(true)}
                  className="inline-flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-[#F5F5F5] font-semibold px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg transition-all duration-200 text-sm sm:text-base"
                >
                  <Eye className="w-5 h-5" />
                  Vista previa del libro
                </button>
              )}
              <a
                href={`${API}/books/${book._id || book.id}/download`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg transition-all duration-200 shadow-lg shadow-[#D92B2B]/20 text-sm sm:text-base"
              >
                <Download className="w-5 h-5" />
                Descargar PDF
              </a>
            </div>

          {/* Contenido de Lectura (FASE 2: lector paginado) */}
          <div className="border-t border-white/10 pt-8">
            {/* Barra de Meta Diaria */}
            <div className="bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 mb-4 sm:mb-6">
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

            {readerError && (
              <div className="bg-red-500/20 border border-red-500/30 rounded-xl px-4 py-3 mb-6 text-center text-red-300">
                {readerError}
                <button onClick={() => goToPage(pageNum)} className="ml-4 text-sm underline hover:text-red-100">
                  Reintentar
                </button>
              </div>
            )}

            {paginated === null ? (
              <div className="text-center py-12 sm:py-16 text-[#A0A0A0]">
                <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
                Cargando libro...
              </div>
            ) : paginated ? (
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

                {/* ReaderToolbar */}
                <ReaderToolbar
                  currentPage={pageNum}
                  totalPages={totalPages || 0}
                  onPageChange={handlePdfPageChange}
                  zoom={zoom}
                  onZoomChange={handleZoomChange}
                  sidebarVisible={sidebarVisible}
                  onToggleSidebar={handleToggleSidebar}
                />

                {/* Main area: Sidebar + PDF Viewer */}
                <div className="flex gap-0 mt-2 rounded-lg overflow-hidden border border-white/10 relative" style={{ minHeight: 'min(500px, 70vh)' }}>
                  {/* Thumbnail Sidebar */}
                  <ThumbnailSidebar
                    pdfDocument={pdfDocument}
                    pdfUrl={book.pdf_path ? `${API}/books/${book.id}/download` : null}
                    totalPages={totalPages || 0}
                    currentPage={pageNum}
                    onPageSelect={handlePdfPageChange}
                    onClose={handleToggleSidebar}
                    visible={sidebarVisible}
                  />

                  {/* PDF Viewer */}
                  <div className="flex-1 min-w-0">
                    {pdfError ? (
                      <div className="flex flex-col items-center justify-center h-full min-h-[300px] sm:min-h-[400px] bg-[#1a1a1a] rounded-r-lg p-4">
                        <p className="text-red-400 mb-2">Error al cargar el PDF</p>
                        <p className="text-sm text-[#A0A0A0] mb-4">{pdfError}</p>
                        {pageContent && (
                          <div className="font-['Merriweather'] text-[#F5F5F5] text-lg leading-relaxed max-w-2xl px-8 text-center" style={{ lineHeight: '1.8' }}>
                            {pageContent.split('\n').map((paragraph, index) => (
                              <p key={index} className="mb-6">{paragraph}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <PDFViewer
                        pdfUrl={book.pdf_path ? `${API}/books/${book.id}/download` : null}
                        currentPage={pageNum}
                        totalPages={totalPages}
                        onPageChange={handlePdfPageChange}
                        zoom={zoom}
                        onZoomChange={handleZoomChange}
                        onDocumentLoaded={handleDocumentLoaded}
                        onError={handlePdfError}
                      />
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* Libros sin paginacion (API confirmo total_pages = 0) */
              <div className="text-center py-12 sm:py-16 text-[#A0A0A0]">
                <p className="text-lg">Libro sin paginación</p>
                <p className="text-sm mt-2">Este libro no está disponible en el lector paginado.</p>
              </div>
            )}
          </div>

        </div>

        {/* Barra de Interacciones (Likes/Dislikes/Vistas) */}
        <div className="bg-[#121212] border border-white/10 rounded-lg p-4 sm:p-6 shadow-xl mt-6 sm:mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
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
        <div className="bg-[#121212] border border-white/10 rounded-lg p-4 sm:p-8 md:p-12 shadow-xl mt-6 sm:mt-8" data-testid="reviews-section">
          <h2 className="text-3xl font-['Lora'] font-semibold text-[#F5F5F5] mb-8">Reseñas</h2>

          {/* Formulario de Reseña */}
          <div className="mb-8 sm:mb-12 pb-6 sm:pb-8 border-b border-white/10">
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
          className="fixed top-20 sm:top-24 right-3 sm:right-6 bg-[#D4AF37]/20 border border-[#D4AF37] rounded-lg px-4 sm:px-6 py-3 sm:py-4 flex items-center gap-3 shadow-xl backdrop-blur-sm z-50 animate-bounce"
          data-testid="rayos-reward-notification"
        >
          <Zap className="w-6 h-6 text-[#D4AF37]" />
          <div>
            <div className="text-[#F5F5F5] font-medium">{rewardMessage}</div>
            <div className="text-[#A0A0A0] text-sm">Sigue leyendo para ganar más</div>
          </div>
        </div>
      )}

      {/* Modal de Vista Previa del PDF */}
      {showPreview && book.pdf_path && (
        <BookPreviewModal
          pdfUrl={`${API}/books/${book.id}/download`}
          bookTitle={book.title}
          onClose={() => setShowPreview(false)}
        />
      )}
    </div>
  );
}
