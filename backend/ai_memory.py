"""Memoria de la IA de Aeternum (FASE 8.3).

MEMORIA PERMANENTE DESACTIVADA por decisión de arquitectura: no existe tabla
ai_memory, no se persiste nada del usuario en esta fase.

Lo único que se usa ahora es la ventana de la conversación actual
(build_conversation_window), que también vive en ai_context.

Interfaces preparadas para la fase futura de memoria persistente:
  - get_persistent_memory(user_id): inerte (devuelve []).
  - save_persistent_memory(...): inerte (no guarda nada).

Cuando se active la memoria, deberá cumplir como mínimo:
  - identificación del usuario propietario (owner_id) en toda fila;
  - aislamiento estricto: ninguna consulta sin WHERE owner_id;
  - jamás almacenar contraseñas, tokens, cookies, API keys, secretos ni
    credenciales;
  - solo información útil y apropiada para mejorar conversaciones futuras.
"""

MEMORY_ENABLED = False


def build_conversation_window(messages, max_messages=20, max_chars=8000):
    """Ventana de mensajes recientes de la conversación actual.

    Se delega en ai_context.build_conversation_context para mantener una
    única implementación de la estrategia de ventana.
    """
    from ai_context import build_conversation_context

    return build_conversation_context(
        messages, max_messages=max_messages, max_chars=max_chars
    )


def get_persistent_memory(user_id):
    """Memoria permanente DESACTIVADA (FASE 8.3).

    Devuelve siempre [] y no toca la base de datos. Se implementará en una
    fase posterior cuando la política de memoria sea aprobada.
    """
    if not MEMORY_ENABLED:
        return []
    raise NotImplementedError("Memoria persistente no implementada")


def save_persistent_memory(user_id, content, memory_key=None):
    """Memoria permanente DESACTIVADA (FASE 8.3).

    No guarda nada. Se implementará en una fase posterior.
    """
    if not MEMORY_ENABLED:
        return None
    raise NotImplementedError("Memoria persistente no implementada")