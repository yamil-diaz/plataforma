import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { buildChatBody, parseErrorDetail } from '../utils/iaChat';
import { Plus, Trash2, Send, Sparkles, Loader2, X, MessageSquare } from 'lucide-react';

// FASE 8.10: INTERFAZ DE USUARIO DE LA IA DE AETERNUM (/ia).
// Solo usuarios autenticados (ruta protegida en App.jsx, sin adminOnly).
// Las conversaciones viven EXCLUSIVAMENTE en el backend: no se usan
// localStorage, sessionStorage ni cookies del lado del cliente.
// El saldo de Rayos es informativo y visual; la UI nunca descuenta Rayos
// y nunca calcula precios: el backend es la única fuente de verdad económica.

export default function IAPage() {
  const { user } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [error, setError] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, sending]);

  const fetchConversations = async () => {
    try {
      const { data } = await axios.get(`${API}/ai/conversations`);
      setConversations(data.conversations || []);
      setError(null);
    } catch (err) {
      setError(parseErrorDetail(err, 'No se pudieron cargar tus conversaciones.'));
    } finally {
      setLoadingList(false);
    }
  };

  const selectConversation = async (conversationId) => {
    setSelectedId(conversationId);
    setMessages([]);
    setSidebarOpen(false);
    setError(null);
    try {
      setLoadingMessages(true);
      const { data } = await axios.get(`${API}/ai/conversations/${conversationId}/messages`);
      setMessages(data.messages || []);
    } catch (err) {
      setError(parseErrorDetail(err, 'No se pudieron cargar los mensajes.'));
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleNewConversation = () => {
    setSelectedId(null);
    setMessages([]);
    setError(null);
    setSidebarOpen(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSend = async () => {
    const message = input.trim();
    if (!message || sending) return;
    const conversationId = selectedId;
    const optimisticUserMessage = { role: 'user', content: message, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, optimisticUserMessage]);
    setInput('');
    setSending(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API}/ai/chat`,
        buildChatBody({ message, conversationId })
      );
      const assistantMessage = { role: 'assistant', content: data.message, created_at: new Date().toISOString() };
      setMessages((prev) => [...prev, assistantMessage]);
      if (data.conversation_id) {
        setSelectedId(data.conversation_id);
        fetchConversations();
      }
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m !== optimisticUserMessage));
      setError(parseErrorDetail(err, 'No se pudo enviar el mensaje. Inténtalo de nuevo.'));
    } finally {
      setSending(false);
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e) => {
    // Enter envía; Shift+Enter inserta salto de línea.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const askDelete = (conversation, e) => {
    e.stopPropagation();
    setDeleteTarget(conversation);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await axios.delete(`${API}/ai/conversations/${deleteTarget.id}`);
      if (selectedId === deleteTarget.id) {
        setSelectedId(null);
        setMessages([]);
      }
      setShowDeleteModal(false);
      setDeleteTarget(null);
      fetchConversations();
    } catch (err) {
      setShowDeleteModal(false);
      setDeleteTarget(null);
      setError(parseErrorDetail(err, 'No se pudo eliminar la conversación.'));
    }
  };

  const selectedConversation = conversations.find((c) => c.id === selectedId) || null;

  const formatDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const today = new Date();
    const sameDay = d.toDateString() === today.toDateString();
    return sameDay
      ? d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />

      {/* SIDEBAR MÓVIL (overlay) */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          ></div>
          <aside className="absolute left-0 top-0 h-full w-80 max-w-[85vw] bg-[#121212] border-r border-white/10 flex flex-col">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-[#D4AF37]" /> Conversaciones
              </h2>
              <button onClick={() => setSidebarOpen(false)} className="text-[#A0A0A0] hover:text-white transition-colors p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-3">
              <button
                onClick={handleNewConversation}
                className="w-full flex items-center justify-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white text-sm font-bold px-4 py-2.5 rounded-xl transition-colors shadow-md shadow-[#D92B2B]/20"
              >
                <Plus className="w-4 h-4" /> Nueva conversación
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => selectConversation(c.id)}
                  className={`w-full group flex items-center justify-between gap-2 text-left px-3 py-2.5 rounded-xl border transition-colors ${
                    c.id === selectedId
                      ? 'bg-[#D92B2B]/10 border-[#D92B2B]/40 text-white'
                      : 'bg-white/[0.03] border-white/5 text-[#A0A0A0] hover:bg-white/[0.06] hover:text-white'
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {c.title || 'Conversación sin título'}
                    </span>
                    <span className="block text-[10px] text-[#A0A0A0]/70 mt-0.5">
                      {formatDate(c.updated_at)}
                    </span>
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => askDelete(c, e)}
                    onKeyDown={(e) => { if (e.key === 'Enter') askDelete(c, e); }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-[#A0A0A0] hover:text-[#D92B2B] rounded-lg"
                    aria-label={`Eliminar conversación ${c.title || c.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </span>
                </button>
              ))}
              {!loadingList && conversations.length === 0 && (
                <p className="text-center text-xs text-[#A0A0A0] py-6">
                  No tienes conversaciones todavía.
                </p>
              )}
            </div>
          </aside>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 md:px-6 py-6 lg:h-[calc(100vh-7rem)]">
        <div className="flex flex-col lg:flex-row gap-6 lg:h-full">

          {/* SIDEBAR DESKTOP */}
          <aside className="hidden lg:flex lg:w-80 lg:shrink-0 bg-[#121212] border border-white/10 rounded-2xl flex-col overflow-hidden">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-[#D4AF37]" /> Conversaciones
              </h2>
            </div>
            <div className="p-3">
              <button
                onClick={handleNewConversation}
                className="w-full flex items-center justify-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white text-sm font-bold px-4 py-2.5 rounded-xl transition-colors shadow-md shadow-[#D92B2B]/20"
              >
                <Plus className="w-4 h-4" /> Nueva conversación
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => selectConversation(c.id)}
                  className={`w-full group flex items-center justify-between gap-2 text-left px-3 py-2.5 rounded-xl border transition-colors ${
                    c.id === selectedId
                      ? 'bg-[#D92B2B]/10 border-[#D92B2B]/40 text-white'
                      : 'bg-white/[0.03] border-white/5 text-[#A0A0A0] hover:bg-white/[0.06] hover:text-white'
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {c.title || 'Conversación sin título'}
                    </span>
                    <span className="block text-[10px] text-[#A0A0A0]/70 mt-0.5">
                      {formatDate(c.updated_at)}
                    </span>
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => askDelete(c, e)}
                    onKeyDown={(e) => { if (e.key === 'Enter') askDelete(c, e); }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-[#A0A0A0] hover:text-[#D92B2B] rounded-lg"
                    aria-label={`Eliminar conversación ${c.title || c.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </span>
                </button>
              ))}
              {!loadingList && conversations.length === 0 && (
                <p className="text-center text-xs text-[#A0A0A0] py-6">
                  No tienes conversaciones todavía.
                </p>
              )}
            </div>
          </aside>

          {/* CHAT */}
          <section className="flex-1 flex flex-col bg-[#121212] border border-white/10 rounded-2xl overflow-hidden lg:h-full h-[72vh]">
            {/* Header del chat */}
            <div className="px-4 md:px-5 py-3.5 border-b border-white/10 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden p-2 text-[#A0A0A0] hover:text-white rounded-lg bg-white/5 transition-colors"
                  aria-label="Abrir conversaciones"
                >
                  <MessageSquare className="w-5 h-5" />
                </button>
                <div className="min-w-0">
                  <h1 className="text-sm md:text-base font-bold text-white font-['Outfit'] truncate flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#D4AF37] shrink-0" />
                    IA de Aeternum
                    {selectedConversation && (
                      <span className="hidden md:inline text-xs font-normal text-[#A0A0A0] truncate">
                        — {selectedConversation.title || 'Conversación sin título'}
                      </span>
                    )}
                  </h1>
                  <p className="text-[10px] text-[#A0A0A0]/70 mt-0.5">
                    Respuestas generadas por el asistente de Aeternum.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {/* Saldo de Rayos: información visual únicamente. La UI nunca
                    descuenta Rayos ni calcula precios (la economía del backend
                    está inactiva; si en el futuro el backend devuelve
                    información económica, se mostrará tal cual). */}
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-full text-xs font-semibold text-[#D4AF37] tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 fill-[#D4AF37] text-[#D4AF37]" />
                  <span>{user ? user.rayos_balance : 0} Rayos</span>
                </div>
                {selectedConversation && (
                  <button
                    onClick={() => askDelete(selectedConversation, { stopPropagation: () => {} })}
                    className="p-2 text-[#A0A0A0] hover:text-[#D92B2B] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                    title="Eliminar conversación"
                    aria-label="Eliminar conversación actual"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="mx-4 mt-4 px-4 py-3 rounded-xl bg-[#D92B2B]/10 border border-[#D92B2B]/30 text-[#F87171] text-sm flex items-start justify-between gap-3">
                <span>{error}</span>
                <button onClick={() => setError(null)} className="text-[#F87171] hover:text-white transition-colors shrink-0" aria-label="Cerrar error">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Área de mensajes */}
            <div className="flex-1 overflow-y-auto px-4 md:px-5 py-4 space-y-4">
              {loadingMessages && (
                <div className="flex items-center justify-center gap-2 text-[#A0A0A0] text-sm py-8">
                  <Loader2 className="w-4 h-4 animate-spin text-[#D4AF37]" /> Cargando mensajes...
                </div>
              )}

              {!loadingMessages && messages.length === 0 && !selectedId && (
                <div className="h-full flex flex-col items-center justify-center text-center px-4">
                  <div className="w-16 h-16 rounded-2xl bg-[#D92B2B]/10 border border-[#D92B2B]/30 flex items-center justify-center mb-5">
                    <Sparkles className="w-8 h-8 text-[#D4AF37]" />
                  </div>
                  <h2 className="text-xl md:text-2xl font-bold text-white font-['Outfit'] mb-2">
                    Bienvenido a la IA de Aeternum
                  </h2>
                  <p className="text-sm text-[#A0A0A0] max-w-md leading-relaxed mb-6">
                    Pregunta por libros, autores o historias de la biblioteca.
                    Crea una nueva conversación o selecciona una existente
                    para continuar.
                  </p>
                  <button
                    onClick={handleNewConversation}
                    className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white text-sm font-bold px-5 py-2.5 rounded-xl transition-colors shadow-md shadow-[#D92B2B]/20"
                  >
                    <Plus className="w-4 h-4" /> Nueva conversación
                  </button>
                </div>
              )}

              {!loadingMessages && messages.length === 0 && selectedId && (
                <p className="text-center text-sm text-[#A0A0A0] py-8">
                  Sin mensajes en esta conversación. Escribe algo para empezar.
                </p>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] md:max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
                      m.role === 'user'
                        ? 'bg-[#D92B2B] text-white rounded-br-md'
                        : 'bg-[#1A1A1A] border border-white/10 text-[#E0E0E0] rounded-bl-md'
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 bg-[#1A1A1A] border border-white/10 text-[#A0A0A0] text-sm px-4 py-3 rounded-2xl rounded-bl-md">
                    <Loader2 className="w-4 h-4 animate-spin text-[#D4AF37]" />
                    Aeternum está escribiendo...
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 md:px-5 py-3.5 border-t border-white/10">
              <div className="flex items-end gap-2 bg-[#0A0A0A] border border-white/10 rounded-2xl p-2 focus-within:border-[#D4AF37]/40 transition-colors">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={sending}
                  placeholder="Escribe un mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
                  className="flex-1 bg-transparent text-white text-sm placeholder-white/25 px-2 py-2 resize-none focus:outline-none max-h-32 disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !input.trim()}
                  className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] disabled:bg-white/10 disabled:text-[#A0A0A0] disabled:cursor-not-allowed text-white text-sm font-bold px-4 py-2.5 rounded-xl transition-colors shrink-0"
                >
                  <Send className="w-4 h-4" />
                  <span className="hidden sm:inline">{sending ? 'Enviando...' : 'Enviar'}</span>
                </button>
              </div>
              <p className="text-[10px] text-[#A0A0A0]/60 mt-2">
                Enter envía · Shift+Enter salta de línea · Las conversaciones se guardan solo en el servidor.
              </p>
            </div>
          </section>
        </div>
      </main>

      {/* MODAL DE CONFIRMACIÓN DE ELIMINACIÓN */}
      {showDeleteModal && deleteTarget && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#1A1A1A]">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-[#D92B2B]" /> Eliminar conversación
              </h2>
              <button onClick={() => setShowDeleteModal(false)} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <p className="text-sm text-[#A0A0A0] leading-relaxed mb-6">
                Se eliminará «{deleteTarget.title || 'Conversación sin título'}» y todos sus mensajes. Esta acción no se puede deshacer.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-5 py-2.5 rounded-lg text-sm font-bold text-[#A0A0A0] hover:text-white transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  className="px-5 py-2.5 rounded-lg text-sm font-bold bg-[#D92B2B] text-white hover:bg-[#F03C3C] transition-colors shadow-lg shadow-[#D92B2B]/20"
                >
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}