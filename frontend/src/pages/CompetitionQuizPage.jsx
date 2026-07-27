import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Trophy, Clock, Swords, CheckCircle2, AlertCircle } from 'lucide-react';

export default function CompetitionQuizPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Quiz state
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [score, setScore] = useState(0);
  const [timeTakenMs, setTimeTakenMs] = useState(0);
  const [timeLeft, setTimeLeft] = useState(15);
  const [startTime, setStartTime] = useState(null);
  
  // Leaderboard state
  const [leaderboard, setLeaderboard] = useState([]);

  useEffect(() => {
    fetchData();
  }, [id]);

  useEffect(() => {
    // If we are in quiz mode, run the timer
    if (data?.competition?.status === 'active' && data?.participant?.status === 'registered' && data?.questions?.length > 0) {
      if (!startTime) setStartTime(Date.now());
      
      const timer = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            // Auto advance
            handleAnswer(null);
            return 15;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [data, currentQuestionIdx, startTime]);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/competitions/${id}`, { withCredentials: true });
      setData(res.data);
      
      if (res.data.competition.status === 'completed' || res.data.participant?.status === 'submitted') {
        fetchLeaderboard();
      }
    } catch (err) {
      alert("Error al cargar competencia");
      navigate('/competitions');
    } finally {
      setLoading(false);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const res = await axios.get(`${API}/competitions/${id}/leaderboard`);
      setLeaderboard(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAnswer = async (selectedOption) => {
    const q = data.questions[currentQuestionIdx];
    let newScore = score;
    
    if (selectedOption === q.correct_option) {
      newScore += 10; // 10 points per correct answer
    }
    
    if (currentQuestionIdx < data.questions.length - 1) {
      setScore(newScore);
      setCurrentQuestionIdx(currentQuestionIdx + 1);
      setTimeLeft(15);
    } else {
      // Finished
      clearInterval();
      const finalTime = Date.now() - startTime;
      setScore(newScore);
      setTimeTakenMs(finalTime);
      submitResult(newScore, finalTime);
    }
  };

  const submitResult = async (finalScore, finalTime) => {
    try {
      await axios.post(`${API}/competitions/${id}/submit`, {
        score: finalScore,
        time_taken_ms: finalTime
      }, { withCredentials: true });
      
      // Update local state to show leaderboard
      setData(prev => ({
        ...prev,
        participant: { ...prev.participant, status: 'submitted' }
      }));
      fetchLeaderboard();
    } catch (err) {
      alert("Error enviando resultados");
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center">Cargando arena...</div>;
  if (!data) return null;

  const { competition, participant, questions } = data;

  // View: Not registered
  if (!participant) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] pb-24">
        <Navbar />
        <div className="max-w-xl mx-auto px-4 mt-20 text-center">
          <AlertCircle className="w-16 h-16 text-yellow-500 mx-auto mb-6" />
          <h1 className="text-3xl font-bold text-white mb-4">No estás inscrito</h1>
          <p className="text-[#A0A0A0] mb-8">Debes inscribirte en la Arena para poder participar.</p>
          <Link to="/competitions" className="bg-white/10 hover:bg-white/20 text-white px-6 py-3 rounded-xl font-bold transition-colors">Volver a la Arena</Link>
        </div>
      </div>
    );
  }

  // View: Waiting to start
  if (competition.status === 'pending') {
    return (
      <div className="min-h-screen bg-[#0A0A0A] pb-24">
        <Navbar />
        <div className="max-w-xl mx-auto px-4 mt-20 text-center">
          <Clock className="w-16 h-16 text-blue-500 mx-auto mb-6 animate-pulse" />
          <h1 className="text-3xl font-bold text-white mb-4">Esperando el inicio...</h1>
          <p className="text-[#A0A0A0] mb-8">El torneo de <b>{competition.book_title}</b> comenzará pronto. Esta página se actualizará sola o recarga para comprobar.</p>
          <button onClick={fetchData} className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold shadow-[0_0_15px_rgba(37,99,235,0.4)] transition-all">
            Comprobar Estado
          </button>
        </div>
      </div>
    );
  }

  // View: Quiz Active
  if (competition.status === 'active' && participant.status === 'registered') {
    const q = questions[currentQuestionIdx];
    if (!q) return <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center">Cargando preguntas...</div>;

    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-12 max-w-3xl mx-auto w-full">
          
          <div className="w-full flex justify-between items-center mb-8">
            <span className="text-[#A0A0A0] font-bold">Pregunta {currentQuestionIdx + 1} de {questions.length}</span>
            <div className="flex items-center gap-2 text-red-500 font-bold bg-red-500/10 px-4 py-2 rounded-full border border-red-500/20">
              <Clock className="w-5 h-5 animate-pulse" />
              <span className="text-xl tabular-nums">{timeLeft}s</span>
            </div>
          </div>

          <div className="w-full bg-white/5 border border-white/10 rounded-2xl p-8 mb-8 text-center shadow-2xl">
            <h2 className="text-2xl md:text-3xl font-bold text-white leading-tight">{q.question_text}</h2>
          </div>

          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
            {['A', 'B', 'C', 'D'].map(opt => (
              <button 
                key={opt}
                onClick={() => handleAnswer(opt)}
                className="bg-[#121212] hover:bg-purple-600/20 border border-white/10 hover:border-purple-500 text-left p-6 rounded-xl transition-all group flex items-start gap-4"
              >
                <span className="bg-white/10 group-hover:bg-purple-500 text-white w-8 h-8 rounded flex items-center justify-center font-bold flex-shrink-0 transition-colors">
                  {opt}
                </span>
                <span className="text-white text-lg font-medium pt-0.5">{q[`option_${opt.toLowerCase()}`]}</span>
              </button>
            ))}
          </div>

        </div>
      </div>
    );
  }

  // View: Leaderboard (Submitted or Completed)
  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 mt-12">
        <div className="text-center mb-12">
          <Trophy className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h1 className="text-4xl font-extrabold text-white font-['Outfit'] mb-2">Tabla de Clasificación</h1>
          <p className="text-[#A0A0A0] text-lg">Torneo: {competition.title}</p>
        </div>

        <div className="bg-[#121212] rounded-2xl border border-white/10 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-[#1A1A1A] text-[#A0A0A0] text-xs uppercase tracking-wider">
                <th className="p-4 font-semibold text-center w-16">Rank</th>
                <th className="p-4 font-semibold">Competidor</th>
                <th className="p-4 font-semibold text-center">Puntaje</th>
                <th className="p-4 font-semibold text-right">Tiempo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {leaderboard.length === 0 ? (
                <tr>
                  <td colSpan="4" className="p-8 text-center text-[#A0A0A0]">Nadie ha terminado aún.</td>
                </tr>
              ) : (
                leaderboard.map((row, i) => (
                  <tr key={row.id} className={`${row.id === user?.id ? 'bg-purple-500/10' : 'hover:bg-white/5'} transition-colors`}>
                    <td className="p-4 text-center">
                      {i === 0 ? <Medal className="w-6 h-6 text-yellow-500 mx-auto" /> : 
                       i === 1 ? <Medal className="w-6 h-6 text-gray-400 mx-auto" /> : 
                       i === 2 ? <Medal className="w-6 h-6 text-amber-700 mx-auto" /> : 
                       <span className="text-white font-bold">{i + 1}</span>}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <img src={row.profile_image_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${row.name}`} alt={row.name} className="w-10 h-10 rounded-full bg-white/10" />
                        <div>
                          <p className="text-white font-bold">{row.name}</p>
                          <p className="text-xs text-[#A0A0A0]">@{row.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">{row.score}</span>
                    </td>
                    <td className="p-4 text-right text-[#A0A0A0] tabular-nums">
                      {(row.time_taken_ms / 1000).toFixed(2)}s
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {competition.status === 'active' && user?.role === 'admin' && (
          <div className="mt-8 text-center">
            <button onClick={async () => {
              try {
                await axios.post(`${API}/admin/competitions/${id}/finish`, {}, { withCredentials: true });
                alert("Torneo finalizado. Premios repartidos.");
                fetchData();
              } catch (err) {
                alert("Error al finalizar: " + err.response?.data?.detail);
              }
            }} className="bg-red-600 hover:bg-red-500 text-white px-8 py-3 rounded-xl font-bold">
              Cerrar Competencia y Repartir Premios
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Medal({ className }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 256 256">
      <path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216ZM174.45,102.3l-24.89,24.26,5.88,34.25a8,8,0,0,1-11.61,8.44L128,161l-30.82,16.21a8,8,0,0,1-11.61-8.44l5.88-34.25L66.55,102.3a8,8,0,0,1,4.43-13.65l34.39-5,15.38-31.16a8,8,0,0,1,14.34,0l15.38,31.16,34.39,5A8,8,0,0,1,174.45,102.3Z" />
    </svg>
  );
}
