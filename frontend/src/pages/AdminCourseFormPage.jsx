import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { Upload, ArrowLeft } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function AdminCourseFormPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    instructor: '',
    category: 'Programación',
    reward_amount: 50
  });
  const [videoFile, setVideoFile] = useState(null);
  const [coverFile, setCoverFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!videoFile || !coverFile) {
      setError('Debes subir un video y una portada.');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const data = new FormData();
      data.append('title', formData.title);
      data.append('description', formData.description);
      data.append('instructor', formData.instructor);
      data.append('category', formData.category);
      data.append('reward_amount', formData.reward_amount);
      data.append('video_file', videoFile);
      data.append('cover_file', coverFile);

      await axios.post(`${API}/courses`, data, { 
        withCredentials: true
      });
      navigate('/courses');
    } catch (err) {
      console.error(err);
      let errorMsg = 'Error al subir el curso';
      if (err.response?.status === 413) {
        errorMsg = 'El archivo es demasiado grande (Límite sugerido: 50MB).';
      } else if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMsg = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMsg = 'Faltan campos obligatorios o el formato es incorrecto.';
        }
      } else if (err.message) {
        errorMsg = err.message;
      }
      setError(errorMsg);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      
      <main className="max-w-3xl mx-auto px-6 pt-12">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#A0A0A0] hover:text-white transition-colors mb-6 text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Volver al Panel
        </Link>
        
        <div className="bg-[#121212] border border-white/10 p-8 rounded-2xl shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-2">Publicar Nuevo Curso</h1>
          <p className="text-[#A0A0A0] text-sm mb-6">Sube el archivo de video (.mp4) y los detalles del curso.</p>
          
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6 font-medium">{error}</div>}
          
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Título del Curso</label>
                <input required type="text" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Instructor</label>
                <input required type="text" value={formData.instructor} onChange={e => setFormData({...formData, instructor: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Descripción</label>
              <textarea required rows="4" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"></textarea>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Categoría</label>
                <select required value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none">
                  <option value="Programación">Programación</option>
                  <option value="Diseño">Diseño</option>
                  <option value="Negocios">Negocios</option>
                  <option value="Idiomas">Idiomas</option>
                  <option value="Otros">Otros</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Recompensa (Rayos)</label>
                <input required type="number" min="0" value={formData.reward_amount} onChange={e => setFormData({...formData, reward_amount: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border-t border-white/10 pt-6 mt-6">
              <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5 border-dashed">
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Video del Curso (.mp4)</label>
                <input required type="file" accept="video/mp4,video/webm" onChange={e => setVideoFile(e.target.files[0])} className="text-xs text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600/20 file:text-blue-500 hover:file:bg-blue-600/30 file:cursor-pointer" />
              </div>
              <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5 border-dashed">
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Portada (Miniatura)</label>
                <input required type="file" accept="image/*" onChange={e => setCoverFile(e.target.files[0])} className="text-xs text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20 file:cursor-pointer" />
              </div>
            </div>

            <div className="pt-6">
              <button disabled={loading} type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50">
                {loading ? 'Subiendo archivo (puede tardar)...' : <><Upload className="w-5 h-5" /> Publicar Curso</>}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
