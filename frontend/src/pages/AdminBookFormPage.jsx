import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { ChevronLeft, BookOpen, AlertCircle, Image as ImageIcon, FileText } from 'lucide-react';

import { API } from '../config/api';

export default function AdminBookFormPage() {
  const [title, setTitle] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [category, setCategory] = useState('Ficción');
  const [price, setPrice] = useState(0.0);
  const [pdfFile, setPdfFile] = useState(null);
  const [coverFile, setCoverFile] = useState(null);
  
  const [coverPreview, setCoverPreview] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();

  const handleCoverChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCoverFile(file);
      setCoverPreview(URL.createObjectURL(file));
    }
  };

  const handlePdfChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPdfFile(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!pdfFile) {
      setError('Por favor, selecciona un archivo PDF del libro.');
      return;
    }

    setLoading(true);
    
    // Crear FormData para subida multipart/form-data
    const formData = new FormData();
    formData.append('title', title);
    formData.append('author_name', authorName);
    formData.append('category', category);
    formData.append('price', price);
    formData.append('pdf_file', pdfFile);
    if (coverFile) {
      formData.append('cover_file', coverFile);
    }

    try {
      await axios.post(`${API}/books`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true
      });
      alert('Libro subido e importado con éxito.');
      navigate('/');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Error al subir el libro. Asegúrate de estar logueado como Admin.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />

      <main className="max-w-3xl mx-auto px-6 pt-8">
        
        {/* Volver */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          Volver al catálogo
        </button>

        <div className="bg-[#121212] border border-white/10 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
          
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white font-['Outfit'] flex items-center gap-2">
              <BookOpen className="w-8 h-8 text-[#D92B2B]" />
              Añadir Nuevo Libro
            </h1>
            <p className="text-sm text-[#A0A0A0] mt-1">
              Sube un libro en formato PDF, extrae su texto para el lector de forma automática y asígnale una foto de portada.
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-950/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Fila Título y Autor */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Título del Libro</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                  placeholder="Ej. Cien Años de Soledad"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Autor</label>
                <input
                  type="text"
                  required
                  value={authorName}
                  onChange={(e) => setAuthorName(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                  placeholder="Ej. Gabriel García Márquez"
                />
              </div>
            </div>

            {/* Fila Categoría y Precio */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Categoría</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] transition-colors"
                >
                  <option value="Ficción">Ficción</option>
                  <option value="Clásicos">Clásicos</option>
                  <option value="Ciencia">Ciencia</option>
                  <option value="Negocios">Negocios</option>
                  <option value="General">General</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Precio (Configurable)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={price}
                  onChange={(e) => setPrice(parseFloat(e.target.value))}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                />
              </div>
            </div>

            {/* Subida de PDF y Portada */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
              
              {/* PDF File */}
              <div className="border-2 border-dashed border-white/10 rounded-xl p-6 text-center hover:border-white/20 transition-colors flex flex-col items-center justify-center min-h-[180px]">
                <FileText className="w-10 h-10 text-[#A0A0A0] mb-3" />
                <span className="text-sm font-semibold text-white">Archivo PDF del Libro</span>
                <span className="text-xs text-[#606060] mt-1 mb-4">Obligatorio (Sube el contenido del libro)</span>
                <input
                  type="file"
                  accept=".pdf"
                  required
                  onChange={handlePdfChange}
                  className="text-xs text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20 file:cursor-pointer"
                />
                {pdfFile && <span className="text-xs text-[#D92B2B] mt-2 font-medium">Seleccionado: {pdfFile.name}</span>}
              </div>

              {/* Cover File */}
              <div className="border-2 border-dashed border-white/10 rounded-xl p-6 text-center hover:border-white/20 transition-colors flex flex-col items-center justify-center min-h-[180px] relative">
                {coverPreview ? (
                  <div className="absolute inset-0 p-4 bg-[#121212] rounded-xl flex items-center justify-between">
                    <img src={coverPreview} alt="Preview" className="h-full w-24 object-cover rounded-lg border border-white/10" />
                    <div className="flex-1 px-4 text-left">
                      <p className="text-xs text-white font-semibold line-clamp-1">{coverFile.name}</p>
                      <button
                        type="button"
                        onClick={() => { setCoverFile(null); setCoverPreview(null); }}
                        className="text-xs text-[#D92B2B] font-semibold mt-2 hover:underline"
                      >
                        Quitar Imagen
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <ImageIcon className="w-10 h-10 text-[#A0A0A0] mb-3" />
                    <span className="text-sm font-semibold text-white">Foto de Portada</span>
                    <span className="text-xs text-[#606060] mt-1 mb-4">Opcional (Dejar en blanco para usar genérica)</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleCoverChange}
                      className="text-xs text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20 file:cursor-pointer"
                    />
                  </>
                )}
              </div>

            </div>

            {/* Botón de Enviar */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-4 rounded-lg transition-all duration-200 shadow-lg shadow-[#D92B2B]/20 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? 'Subiendo y procesando libro...' : 'Publicar Libro'}
            </button>

          </form>

        </div>

      </main>
    </div>
  );
}
