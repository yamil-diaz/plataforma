import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { ChevronLeft, Layers, FileArchive, AlertCircle, CheckCircle, Info } from 'lucide-react';

import { API } from '../config/api';

export default function AdminImportPage() {
  const [zipFile, setZipFile] = useState(null);
  const [defaultCategory, setDefaultCategory] = useState('General');
  const [defaultPrice, setDefaultPrice] = useState(0.0);
  
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [errors, setErrors] = useState([]);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleZipChange = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.zip')) {
      setZipFile(file);
      setError('');
    } else {
      setError('Por favor, selecciona un archivo en formato .zip válido.');
      setZipFile(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setErrors([]);
    
    if (!zipFile) {
      setError('Por favor, selecciona un archivo ZIP.');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', zipFile);
    formData.append('category', defaultCategory);
    formData.append('price', defaultPrice);

    try {
      const { data } = await axios.post(`${API}/books/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true
      });
      setTaskId(data.task_id);
      setStatus('processing');
      setMessage('Subida completada. Iniciando importación en segundo plano...');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Error al iniciar la importación masiva.');
      setLoading(false);
    }
  };

  // Efecto para consultar el estado de la tarea en segundo plano
  useEffect(() => {
    if (!taskId || status === 'completed' || status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const { data } = await axios.get(`${API}/books/import/status/${taskId}`, {
          withCredentials: true
        });
        
        setStatus(data.status);
        setMessage(data.message);
        setErrors(data.errors || []);
        
        if (data.total > 0) {
          const percentage = Math.round((data.processed / data.total) * 100);
          setProgress(percentage);
        }

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err) {
        console.error('Error al consultar estado:', err);
      }
    }, 1000); // Consultar cada 1 segundo

    return () => clearInterval(interval);
  }, [taskId, status]);

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
              <Layers className="w-8 h-8 text-[#D92B2B]" />
              Importación Masiva de Libros
            </h1>
            <p className="text-sm text-[#A0A0A0] mt-1">
              Sube miles de libros en un solo archivo ZIP. El sistema extraerá los PDFs, los procesará e importará las portadas asociadas.
            </p>
          </div>

          {/* Caja Informativa */}
          <div className="mb-8 p-5 bg-blue-950/10 border border-blue-500/20 rounded-xl flex items-start gap-4 text-[#A0A0A0] text-sm leading-relaxed">
            <Info className="w-6 h-6 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white mb-1">¿Cómo estructurar tu archivo ZIP?</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Agrega tus libros en formato <strong>.pdf</strong> (se les extraerá texto automáticamente).</li>
                <li><strong>Emparejamiento de Portadas:</strong> Si colocas fotos de portada con el mismo nombre que el PDF, el sistema las emparejará solas (ej. <code>quijote.pdf</code> y <code>quijote.jpg</code> o <code>quijote.png</code>).</li>
                <li>Los libros sin portada usarán una por defecto.</li>
              </ul>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-950/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Formulario / Estado */}
          {!taskId ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Categoría por Defecto</label>
                  <select
                    value={defaultCategory}
                    onChange={(e) => setDefaultCategory(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] transition-colors"
                  >
                    <option value="General">General</option>
                    <option value="Ficción">Ficción</option>
                    <option value="Clásicos">Clásicos</option>
                    <option value="Ciencia">Ciencia</option>
                    <option value="Negocios">Negocios</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Precio por Defecto</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={defaultPrice}
                    onChange={(e) => setDefaultPrice(parseFloat(e.target.value))}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] placeholder-[#505050] focus:outline-none focus:border-[#D92B2B] transition-colors"
                  />
                </div>
              </div>

              {/* Subida del ZIP */}
              <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-white/20 transition-colors flex flex-col items-center justify-center min-h-[200px]">
                <FileArchive className="w-12 h-12 text-[#A0A0A0] mb-3" />
                <span className="text-sm font-semibold text-white">Selecciona tu Archivo ZIP</span>
                <span className="text-xs text-[#606060] mt-1 mb-5">El archivo debe contener PDFs e imágenes de portadas</span>
                
                <input
                  type="file"
                  accept=".zip"
                  required
                  onChange={handleZipChange}
                  className="text-xs text-[#A0A0A0] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20 file:cursor-pointer"
                />
                
                {zipFile && <span className="text-xs text-[#D92B2B] mt-3 font-semibold">Seleccionado: {zipFile.name} ({Math.round(zipFile.size / 1024 / 1024 * 100) / 100} MB)</span>}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-4 rounded-lg transition-all duration-200 shadow-lg shadow-[#D92B2B]/20 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                Iniciar Procesamiento ZIP
              </button>

            </form>
          ) : (
            /* Pantalla de Monitoreo de Progreso */
            <div className="space-y-6 py-4">
              
              {/* Encabezado del Progreso */}
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-white">Estado de la Tarea</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  status === 'processing' ? 'bg-[#D4AF37]/10 text-[#D4AF37] animate-pulse' :
                  status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                  'bg-red-500/10 text-red-400'
                }`}>
                  {status === 'processing' ? 'Procesando' :
                   status === 'completed' ? 'Completado' :
                   'Fallado'}
                </span>
              </div>

              {/* Mensaje Informativo */}
              <p className="text-sm text-[#A0A0A0]">{message}</p>

              {/* Barra de Progreso */}
              {status !== 'failed' && (
                <div className="space-y-2">
                  <div className="w-full bg-[#0A0A0A] rounded-full h-3 border border-white/5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-[#D92B2B] to-[#D4AF37] h-full rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-[#606060] font-semibold">
                    <span>{progress}% Procesado</span>
                    <span>Consulte el progreso</span>
                  </div>
                </div>
              )}

              {/* Alerta de Éxito al Finalizar */}
              {status === 'completed' && (
                <div className="p-4 bg-emerald-950/10 border border-emerald-500/20 rounded-lg flex items-center gap-3 text-emerald-400 text-sm">
                  <CheckCircle className="w-5 h-5 shrink-0" />
                  <span>¡Importación masiva terminada con éxito!</span>
                </div>
              )}

              {/* Historial de Errores Individuales */}
              {errors.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-white">Advertencias o Errores ({errors.length}):</h3>
                  <div className="bg-[#0A0A0A] border border-white/10 rounded-lg p-4 max-h-[150px] overflow-y-auto text-xs text-red-400 font-mono space-y-1.5">
                    {errors.map((err, idx) => (
                      <div key={idx}>• {err}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Botones de Acción final */}
              {(status === 'completed' || status === 'failed') && (
                <div className="flex gap-4 pt-4">
                  <button
                    onClick={() => navigate('/')}
                    className="flex-1 bg-white/10 text-white hover:bg-white/20 py-3 rounded-lg text-sm font-semibold transition-colors"
                  >
                    Ir al Catálogo
                  </button>
                  <button
                    onClick={() => { setTaskId(null); setStatus(null); setProgress(0); setZipFile(null); }}
                    className="flex-1 bg-[#D92B2B] text-white hover:bg-[#F03C3C] py-3 rounded-lg text-sm font-semibold transition-colors"
                  >
                    Subir Otro ZIP
                  </button>
                </div>
              )}

            </div>
          )}

        </div>

      </main>
    </div>
  );
}
