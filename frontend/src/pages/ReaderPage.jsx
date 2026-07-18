import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { ChevronLeft, Heart, Zap, Star, Send } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API = 'http://localhost:8000/api';

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
  const [reviews, setReviews] = useState([]);
  const [newReview, setNewReview] = useState({ rating: 5, comment: '' });
  const [submittingReview, setSubmittingReview] = useState(false);
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const loadBook = async () => {
    try {
      // Obtener el libro directamente por su ID de SQLite
      const { data: bookDetails } = await axios.get(`${API}/books/${bookId}`);
      setBook(bookDetails);
      
      // Cargar reseñas
      loadReviews(bookDetails._id || bookDetails.id);
      
      // Ganar Rayos por leer
      setTimeout(async () => {
        try {
          await axios.post(
            `${API}/rayos/earn`,
            {
              amount: 10,
              type: 'earned',
              description: `Leyó "${bookDetails.title}"`
            },
            { withCredentials: true }
          );
          setShowReward(true);
          refreshUser();
          setTimeout(() => setShowReward(false), 3000);
        } catch (error) {
          console.error('Error earning Rayos:', error);
        }
      }, 5000);
    } catch (error) {
      console.error('Error loading book:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadReviews = async (bId) => {
    try {
      const { data } = await axios.get(`${API}/books/${bId}/reviews`);
      setReviews(data);
    } catch (error) {
      console.error('Error loading reviews:', error);
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

          {/* Contenido de Lectura */}
          <div className="border-t border-white/10 pt-8">
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

      {/* Notificación de Recompensa de Rayos */}
      {showReward && (
        <div
          className="fixed top-24 right-6 bg-[#D4AF37]/20 border border-[#D4AF37] rounded-lg px-6 py-4 flex items-center gap-3 shadow-xl backdrop-blur-sm z-50 animate-bounce"
          data-testid="rayos-reward-notification"
        >
          <Zap className="w-6 h-6 text-[#D4AF37]" />
          <div>
            <div className="text-[#F5F5F5] font-medium">¡+10 Rayos Ganados!</div>
            <div className="text-[#A0A0A0] text-sm">Sigue leyendo para ganar más</div>
          </div>
        </div>
      )}
    </div>
  );
}
