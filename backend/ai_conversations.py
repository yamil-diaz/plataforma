"""Persistencia de conversaciones de IA (FASE 8.7).

Encapsula TODO acceso a las tablas ai_conversations y ai_messages: creación,
obtención segura (siempre filtrada por el user_id del JWT), listado, inserción
de mensajes y eliminación con CASCADE. Ni los endpoints ni el orquestador
escriben SQL de conversaciones directamente.

Garantías de seguridad:
  - Ownership estricto: TODA consulta por conversación incluye user_id. Una
    conversación inexistente y una ajena producen el MISMO 404 ("Conversación
    no encontrada"): nunca se revela la existencia de datos ajenos.
  - La identidad proviene EXCLUSIVAMENTE del JWT (server.py). Este módulo
    jamás acepta un user_id enviado por el cliente.
  - Aislamiento de historial: cada conversación solo ve sus propios mensajes.
  - NO es memoria permanente: los mensajes son el historial de UNA
    conversación. ai_memory sigue desactivada (MEMORY_ENABLED = False).

Convenciones (idénticas al resto del proyecto):
  - Timestamps TEXT ISO-UTC: datetime.now(timezone.utc).isoformat().
  - FK con ON DELETE CASCADE (BD real vía migrate_db_ai.py; el stub de tests
    replica el CASCADE de mensajes al eliminar una conversación).
  - Roles de mensaje restringidos por CHECK (user/assistant/system) en la
    migración; este módulo solo escribe user y assistant.
"""

from datetime import datetime, timezone


class AIConversationError(Exception):
    """Error de persistencia de conversaciones (404 genérico para ajenas)."""

    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _now():
    """Timestamp de la convención del proyecto: TEXT ISO-UTC."""
    return datetime.now(timezone.utc).isoformat()


def create_conversation(db, user_id):
    """Crea una conversación 'active' del usuario (title NULL) y la devuelve."""
    cursor = db.cursor()
    now = _now()
    cursor.execute(
        """
        INSERT INTO ai_conversations (user_id, title, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (user_id, None, "active", now, now),
    )
    row = cursor.fetchone()
    if not row:
        raise AIConversationError("No se pudo crear la conversación", 500)
    return {
        "id": row["id"],
        "user_id": user_id,
        "title": None,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def get_conversation(db, conversation_id, user_id):
    """Devuelve la conversación SOLO si pertenece al usuario (None si no)."""
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT id, title, status, created_at, updated_at
        FROM ai_conversations
        WHERE id = %s AND user_id = %s
        """,
        (conversation_id, user_id),
    )
    return cursor.fetchone()


def resolve_conversation(db, conversation_id, user_id):
    """Valida que la conversación exista y pertenezca al usuario.

    Tanto la inexistente como la ajena producen el mismo 404 genérico.
    """
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        raise AIConversationError("Conversación no encontrada", 404)
    return conversation


def list_conversations(db, user_id):
    """Conversaciones del usuario ordenadas por updated_at DESC.

    Nunca devuelve los mensajes completos (solo metadatos).
    """
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT id, title, status, created_at, updated_at
        FROM ai_conversations
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )
    return cursor.fetchall()


def get_messages(db, conversation_id, user_id):
    """Mensajes cronológicos de la conversación, SOLO si es del usuario.

    404 genérico si no existe o pertenece a otro usuario.
    """
    resolve_conversation(db, conversation_id, user_id)
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT role, content, created_at
        FROM ai_messages
        WHERE conversation_id = %s
        ORDER BY id
        """,
        (conversation_id,),
    )
    return cursor.fetchall()


def add_message(db, conversation_id, role, content):
    """Guarda un mensaje y actualiza updated_at de la conversación.

    El contenido se trunca al límite técnico MAX_MESSAGE_CHARS (4000) para
    que un texto muy largo nunca desborde el historial de contexto.
    """
    from ai_service import MAX_MESSAGE_CHARS

    content = str(content)[:MAX_MESSAGE_CHARS]
    now = _now()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO ai_messages (conversation_id, role, content, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (conversation_id, role, content, now),
    )
    cursor.execute(
        "UPDATE ai_conversations SET updated_at = %s WHERE id = %s",
        (now, conversation_id),
    )


def delete_conversation(db, conversation_id, user_id):
    """Elimina la conversación SOLO si es del usuario (mensajes por CASCADE).

    404 genérico si no existe o pertenece a otro usuario.
    """
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM ai_conversations WHERE id = %s AND user_id = %s",
        (conversation_id, user_id),
    )
    if cursor.rowcount == 0:
        raise AIConversationError("Conversación no encontrada", 404)
    return True