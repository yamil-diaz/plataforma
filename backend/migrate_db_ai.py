"""Migración preparatoria de las tablas de IA (FASES 8.5 y 8.7).

Idempotente y segura (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT
EXISTS), compatible con el patrón de database.py. Sigue el patrón existente
de la base de datos, pero se entrega como script manual y NO se ejecuta
automáticamente: la economía y la persistencia de IA deben activarse SOLO
cuando se autorice.

Tablas:
  - ai_consumption     (FASE 8.5: registro económico idempotente)
  - ai_conversations   (FASE 8.7: conversaciones por usuario)
  - ai_messages        (FASE 8.7: mensajes con FK CASCADE y CHECK de rol)

USO (NO ejecutar contra producción sin autorización):
    python migrate_db_ai.py              # aplica la migración
    python migrate_db_ai.py --dry-run    # muestra el SQL sin ejecutar nada

Requiere DATABASE_URL (igual que el resto del backend).
"""

import os
import sys

SQL_CREATE_AI_CONSUMPTION = """
CREATE TABLE IF NOT EXISTS ai_consumption (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_id TEXT NOT NULL UNIQUE,
    operation TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    rayos_cost INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    created_at TEXT NOT NULL
)
"""

SQL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ai_consumption_user ON ai_consumption(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_consumption_created ON ai_consumption(created_at);
"""

# FASE 8.7: conversaciones de IA (persistencia de historial, sin memoria
# permanente). FK CASCADE: al borrar un usuario o una conversación, se borran
# sus mensajes. Timestamps TEXT ISO-UTC (convención del proyecto). El rol de
# mensaje está restringido por CHECK a user/assistant/system.
SQL_CREATE_AI_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

SQL_CREATE_AI_MESSAGES = """
CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL
        REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

SQL_CONVERSATION_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_updated
    ON ai_conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation
    ON ai_messages(conversation_id, id);
"""


def run(dry_run=False):
    if dry_run:
        print("--dry-run: SQL a aplicar (no se ejecuta nada)")
        print(SQL_CREATE_AI_CONSUMPTION)
        print(SQL_INDEXES)
        print(SQL_CREATE_AI_CONVERSATIONS)
        print(SQL_CREATE_AI_MESSAGES)
        print(SQL_CONVERSATION_INDEXES)
        return

    import psycopg2
    import psycopg2.extras

    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está definida. No se puede aplicar la migración."
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_CREATE_AI_CONSUMPTION)
            cursor.execute(SQL_INDEXES)
            cursor.execute(SQL_CREATE_AI_CONVERSATIONS)
            cursor.execute(SQL_CREATE_AI_MESSAGES)
            cursor.execute(SQL_CONVERSATION_INDEXES)
        conn.commit()
        print("Migración IA aplicada correctamente (ai_consumption, "
              "ai_conversations, ai_messages).")
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Migración fallida: {exc}") from exc
    finally:
        conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv[1:]
    run(dry_run=dry_run)