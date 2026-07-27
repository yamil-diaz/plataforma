import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { BookOpen, Calendar, Clock, Plus, Trash2, CheckCircle2 } from 'lucide-react';

export default function AdminCompetitionPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    title: '',
    book_title: '',
    date: '',
    time: ''
  });

  const [questions, setQuestions] = useState([{
    question_text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A'
  }]);

  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    setLoading(false);
  }, [user]);

  const addQuestion = () => {
    setQuestions([...questions, { question_text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A' }]);
  };

  const removeQuestion = (index) => {
    if (questions.length > 1) {
      setQuestions(questions.filter((_, i) => i !== index));
    }
  };

  const handleQuestionChange = (index, field, value) => {
    const newQ = [...questions];
    newQ[index][field] = value;
    setQuestions(newQ);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.book_title || !form.date || !form.time) return alert("Faltan datos de la competencia");
    
    // Validar preguntas
    for (let q of questions) {
      if (!q.question_text || !q.option_a || !q.option_b || !q.option_c || !q.option_d) {
        return alert("Completa todas las opciones de las preguntas");
      }
    }

    try {
      setSaving(true);
      // Construct UTC datetime
      const localDate = new Date(`${form.date}T${form.time}`);
      const scheduled_at = localDate.toISOString();

      const payload = {
        title: form.title || 'Competencia de Lectura',
        book_title: form.book_title,
        scheduled_at,
        questions
      };

      await axios.post(`${API}/admin/competitions`, payload, { withCredentials: true });
      alert("Competencia creada con éxito");
      navigate('/dashboard');
    } catch (err) {
      alert("Error al crear competencia: " + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center">Cargando...</div>;

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      
      <div className="max-w-4xl mx-auto px-4 mt-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-purple-500/20 p-3 rounded-xl border border-purple-500/30">
            <TrophyIcon className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white font-['Outfit']">Crear Competencia</h1>
            <p className="text-[#A0A0A0] text-sm">Programa un cuestionario en vivo para los usuarios.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-[#121212] rounded-2xl border border-white/10 p-6 space-y-4">
            <h2 className="text-lg font-bold text-white mb-4">Detalles Generales</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase mb-2">Título de la Competencia</label>
                <input type="text" value={form.title} onChange={e => setForm({...form, title: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 outline-none" placeholder="Ej: Gran Torneo de Ciencia Ficción" required />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase mb-2">Escribe el Libro Base</label>
                <input type="text" value={form.book_title} onChange={e => setForm({...form, book_title: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 outline-none" placeholder="Ej: Harry Potter y la Piedra Filosofal" required />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase mb-2"><Calendar className="w-4 h-4 inline mr-1" />Fecha de Inicio (Tu hora local)</label>
                <input type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 outline-none" required />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase mb-2"><Clock className="w-4 h-4 inline mr-1" />Hora Exacta</label>
                <input type="time" value={form.time} onChange={e => setForm({...form, time: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 outline-none" required />
              </div>
            </div>
          </div>

          <div className="bg-[#121212] rounded-2xl border border-white/10 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-white">Preguntas ({questions.length})</h2>
              <button type="button" onClick={addQuestion} className="flex items-center gap-2 text-sm font-semibold text-purple-400 bg-purple-500/10 px-3 py-1.5 rounded-lg hover:bg-purple-500/20 transition-colors">
                <Plus className="w-4 h-4" /> Agregar
              </button>
            </div>

            <div className="space-y-8">
              {questions.map((q, i) => (
                <div key={i} className="p-4 border border-white/5 bg-[#1A1A1A] rounded-xl relative">
                  {questions.length > 1 && (
                    <button type="button" onClick={() => removeQuestion(i)} className="absolute top-4 right-4 text-red-400 hover:text-red-300">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                  
                  <div className="mb-4">
                    <label className="block text-xs font-semibold text-[#A0A0A0] uppercase mb-2">Pregunta {i+1}</label>
                    <input type="text" value={q.question_text} onChange={e => handleQuestionChange(i, 'question_text', e.target.value)} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white outline-none" placeholder="¿Qué personaje dijo...?" required />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['A', 'B', 'C', 'D'].map(opt => (
                      <div key={opt} className={`flex items-center gap-3 p-2 rounded-lg border ${q.correct_option === opt ? 'border-green-500/50 bg-green-500/10' : 'border-white/10 bg-[#0A0A0A]'}`}>
                        <input 
                          type="radio" 
                          name={`correct_${i}`} 
                          checked={q.correct_option === opt}
                          onChange={() => handleQuestionChange(i, 'correct_option', opt)}
                          className="w-4 h-4 accent-green-500"
                        />
                        <span className="text-xs font-bold text-[#A0A0A0] w-4">{opt}</span>
                        <input 
                          type="text" 
                          value={q[`option_${opt.toLowerCase()}`]} 
                          onChange={e => handleQuestionChange(i, `option_${opt.toLowerCase()}`, e.target.value)}
                          className="w-full bg-transparent text-sm text-white outline-none"
                          placeholder={`Opción ${opt}`}
                          required
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button type="submit" disabled={saving} className="w-full py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl shadow-lg hover:opacity-90 transition-opacity disabled:opacity-50">
            {saving ? 'Guardando...' : 'Programar Competencia'}
          </button>
        </form>
      </div>
    </div>
  );
}

const TrophyIcon = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
)
