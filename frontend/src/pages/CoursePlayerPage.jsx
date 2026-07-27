import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { Zap, CheckCircle, ArrowLeft } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const HOST = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace('/api', '') : 'http://localhost:8000';

export default function CoursePlayerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, fetchProfile } = useAuth();
  
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [videoWatched, setVideoWatched] = useState(false);

  useEffect(() => {
    fetchCourse();
  }, [id]);

  const fetchCourse = async () => {
    try {
      const { data } = await axios.get(`${API}/courses/${id}`);
      setCourse(data);
    } catch (err) {
      setError('Curso no encontrado');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoEnded = () => {
    setVideoWatched(true);
  };

  const handleComplete = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    setCompleting(true);
    setError('');
    setMessage('');
    
    try {
      const { data } = await axios.post(`${API}/courses/${id}/complete`, {}, { withCredentials: true });
      setMessage(data.message);
      await fetchProfile(); // Update Rayos balance in context
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al completar el curso');
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">Cargando curso...</div>;
  }

  if (error && !course) {
    return <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-red-500 font-bold">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8">
        <button onClick={() => navigate('/courses')} className="flex items-center gap-2 text-[#A0A0A0] hover:text-white transition-colors mb-6 text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Volver a Cursos
        </button>

        <div className="bg-[#121212] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
          {/* Video Player */}
          <div className="aspect-video bg-black w-full relative">
            <video 
              controls 
              controlsList="nodownload"
              onEnded={handleVideoEnded}
              className="w-full h-full object-contain"
              poster={course.cover_url}
            >
              <source src={`${HOST}${course.video_url}`} type="video/mp4" />
              Tu navegador no soporta la reproducción de video.
            </video>
          </div>

          {/* Info Section */}
          <div className="p-6 md:p-10 flex flex-col md:flex-row gap-8 justify-between items-start">
            <div className="flex-1">
              <span className="text-xs font-bold text-[#A0A0A0] uppercase tracking-wider bg-white/5 px-3 py-1 rounded-full">{course.category}</span>
              <h1 className="text-3xl font-bold text-white mt-4 font-['Outfit']">{course.title}</h1>
              <p className="text-[#A0A0A0] text-sm mt-2 flex items-center gap-2">
                Instructor: <span className="text-[#F5F5F5] font-semibold">{course.instructor}</span>
              </p>
              
              <div className="mt-6 text-[#D0D0D0] leading-relaxed whitespace-pre-wrap text-sm border-t border-white/10 pt-6">
                {course.description}
              </div>
            </div>

            {/* Action Card */}
            <div className="w-full md:w-80 bg-[#0A0A0A] border border-white/5 rounded-xl p-6 shrink-0">
              <h3 className="text-white font-bold mb-4 text-center">Recompensa del Curso</h3>
              
              <div className="bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-lg p-4 flex flex-col items-center justify-center mb-6">
                <Zap className="w-8 h-8 text-[#D4AF37] mb-2 animate-pulse" />
                <span className="text-2xl font-bold text-[#D4AF37]">+{course.reward_amount}</span>
                <span className="text-xs font-semibold text-[#D4AF37] uppercase tracking-widest">Rayos</span>
              </div>

              {message ? (
                <div className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 p-3 rounded-lg text-sm text-center font-medium flex items-center justify-center gap-2">
                  <CheckCircle className="w-4 h-4" /> {message}
                </div>
              ) : error ? (
                <div className="bg-red-500/10 text-red-500 border border-red-500/30 p-3 rounded-lg text-sm text-center font-medium">
                  {error}
                </div>
              ) : (
                <button 
                  onClick={handleComplete}
                  disabled={completing || !videoWatched}
                  className={`w-full py-3 rounded-lg font-bold text-sm transition-all ${
                    videoWatched 
                      ? 'bg-gradient-to-r from-[#D92B2B] to-[#F03C3C] hover:from-[#F03C3C] hover:to-[#ff5252] text-white shadow-lg shadow-[#D92B2B]/20'
                      : 'bg-white/5 text-[#A0A0A0] cursor-not-allowed border border-white/10'
                  }`}
                >
                  {completing ? 'Procesando...' : videoWatched ? 'Reclamar Rayos' : 'Termina el video primero'}
                </button>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
