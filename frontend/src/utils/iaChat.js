// FASE 8.10: lógica pura de la UI de IA (Aeternum).
// El backend es la fuente de verdad: el body del chat NUNCA incluye
// user_id, role, provider, model, coste ni permisos.
// La identidad viaja en la cookie JWT (axios.withCredentials de AuthContext).

// context (book_id / page_number / chapter_id) se prepara aquí para la
// futura integración con el lector, pero hoy siempre es null: la UI actual
// no envía nada de esto (FASE 8.10 no integra ReaderPage).
export const buildChatBody = ({ message, conversationId, context = null }) => {
  const body = { message };
  if (conversationId != null) {
    body.conversation_id = conversationId;
  }
  if (context) {
    if (context.bookId != null) body.book_id = context.bookId;
    if (context.pageNumber != null) body.page_number = context.pageNumber;
    if (context.chapterId != null) body.chapter_id = context.chapterId;
  }
  return body;
};

// Mensaje legible de error sin exponer secretos: usa el detail del backend
// cuando existe y un texto seguro de respaldo en caso contrario.
export const parseErrorDetail = (error, fallback) => {
  if (error && error.response && error.response.data && error.response.data.detail) {
    return String(error.response.data.detail);
  }
  return fallback;
};