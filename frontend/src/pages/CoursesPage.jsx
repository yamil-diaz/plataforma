import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { PlayCircle, Video } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const { data } = await axios.get(`${API}/courses`);
      setCourses(data);
    } catch (error) {
      console.error('Error al cargar cursos:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-6 pt-12">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-lg bg-[#D92B2B] flex items-center justify-center shadow-lg shadow-[#D92B2B]/20">
            <Video className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white font-['Outfit']">Cursos con Video</h1>
            <p className="text-[#A0A0A0] text-sm mt-1">Aprende nuevas habilidades y gana Rayos al completar los cursos.</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-[#A0A0A0]">Cargando cursos...</div>
        ) : courses.length === 0 ? (
          <div className="text-center py-20 bg-[#121212] border border-white/5 rounded-2xl">
            <p className="text-[#A0A0A0]">Aún no hay cursos disponibles.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {courses.map(course => (
              <Link 
                key={course.id} 
                to={`/courses/${course.id}`}
                className="group bg-[#121212] rounded-xl overflow-hidden border border-white/10 hover:border-white/30 transition-all shadow-lg hover:shadow-2xl hover:-translate-y-1 block relative"
              >
                <div className="absolute top-2 right-2 bg-[#D4AF37] text-black text-xs font-bold px-2 py-1 rounded shadow-lg z-10 flex items-center gap-1">
                  +{course.reward_amount} Rayos
                </div>
                <div className="aspect-video bg-black relative">
                  <img src={course.cover_url} alt={course.title} className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                    <PlayCircle className="w-12 h-12 text-white" />
                  </div>
                </div>
                <div className="p-4">
                  <span className="text-[10px] font-bold text-[#A0A0A0] uppercase tracking-wider block mb-1">{course.category}</span>
                  <h3 className="text-white font-bold text-base leading-tight mb-1 group-hover:text-[#D92B2B] transition-colors">{course.title}</h3>
                  <p className="text-[#A0A0A0] text-xs">Por {course.instructor}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
