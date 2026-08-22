"""Migración idempotente: tablas del Foro Estudiantil de AeternumLibrary.

Ejecuta CREATE TABLE IF NOT EXISTS para todas las tablas del foro.
Segura para ejecutar múltiples veces sin destruir datos existentes.
"""
import os
import psycopg2
import psycopg2.extras


INITIAL_CATEGORIES = [
    ("Libros y lecturas", "Habla sobre libros, reseñas y recomendaciones", "📚", "#D92B2B", 1),
    ("Escritura", "Consejos, técnicas y retroalimentación sobre escritura", "✍️", "#8B5CF6", 2),
    ("Ayuda académica", "Resuelve dudas de estudios y tareas", "🧠", "#3B82F6", 3),
    ("Literatura", "Análisis literario, géneros y movimientos", "📖", "#F59E0B", 4),
    ("Ciencias y conocimientos", "Ciencia, tecnología y descubrimientos", "🔬", "#10B981", 5),
    ("Historia y cultura", "Debates históricos y culturales", "🌎", "#EC4899", 6),
    ("Debate y opinión", "Opiniones y debates abiertos", "💬", "#6366F1", 7),
    ("Recomendaciones", "Recomendaciones de libros y lecturas", "⭐", "#D4AF37", 8),
    ("Preguntas generales", "Preguntas sobre la plataforma y más", "❓", "#6B7280", 9),
    ("Comunidad estudiantil", "Conecta con otros estudiantes", "🏫", "#14B8A6", 10),
]


def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Sin DATABASE_URL — skipping forum migration")
        return

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    now = "2026-01-01T00:00:00+00:00"

    # ── forum_categories ──────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        icon TEXT,
        color TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        post_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    # ── forum_posts ───────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        category_id INTEGER NOT NULL REFERENCES forum_categories(id) ON DELETE RESTRICT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        book_id INTEGER REFERENCES books(id) ON DELETE SET NULL,
        status TEXT DEFAULT 'active',
        views INTEGER DEFAULT 0,
        reply_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        is_pinned BOOLEAN DEFAULT FALSE,
        is_resolved BOOLEAN DEFAULT FALSE,
        slug TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # ── forum_replies ─────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_replies (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        is_accepted BOOLEAN DEFAULT FALSE,
        like_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # ── forum_likes ───────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_likes (
        id SERIAL PRIMARY KEY,
        post_id INTEGER REFERENCES forum_posts(id) ON DELETE CASCADE,
        reply_id INTEGER REFERENCES forum_replies(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        CONSTRAINT fk_like_target CHECK (
            (post_id IS NOT NULL AND reply_id IS NULL) OR
            (post_id IS NULL AND reply_id IS NOT NULL)
        ),
        UNIQUE(post_id, user_id),
        UNIQUE(reply_id, user_id)
    )
    """)

    # ── forum_bookmarks ───────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_bookmarks (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        UNIQUE(post_id, user_id)
    )
    """)

    # ── forum_follows ─────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_follows (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        UNIQUE(post_id, user_id)
    )
    """)

    # ── forum_reports ─────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_reports (
        id SERIAL PRIMARY KEY,
        reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        post_id INTEGER REFERENCES forum_posts(id) ON DELETE SET NULL,
        reply_id INTEGER REFERENCES forum_replies(id) ON DELETE SET NULL,
        reason TEXT NOT NULL,
        explanation TEXT,
        status TEXT DEFAULT 'pending',
        admin_note TEXT,
        reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        CONSTRAINT fk_report_target CHECK (
            (post_id IS NOT NULL AND reply_id IS NULL) OR
            (post_id IS NULL AND reply_id IS NOT NULL)
        )
    )
    """)

    # ── forum_rate_limits ─────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_rate_limits (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        action TEXT NOT NULL,
        window_start TEXT NOT NULL,
        count INTEGER DEFAULT 1
    )
    """)

    # ── forum_audit_log ───────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_audit_log (
        id SERIAL PRIMARY KEY,
        admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id INTEGER NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # ── Índices ───────────────────────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_user ON forum_posts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_category ON forum_posts(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_book ON forum_posts(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_status ON forum_posts(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_created ON forum_posts(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_category_created ON forum_posts(category_id, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_posts_status_created ON forum_posts(status, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_replies_post ON forum_replies(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_replies_user ON forum_replies(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_likes_post ON forum_likes(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_likes_reply ON forum_likes(reply_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_bookmarks_user ON forum_bookmarks(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_follows_user ON forum_follows(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_follows_post ON forum_follows(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_reports_status ON forum_reports(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_reports_created ON forum_reports(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forum_rate_limits_user_action ON forum_rate_limits(user_id, action, window_start)")

    # ── Seed de categorías iniciales ──────────────────────────────────────
    cursor.execute("SELECT COUNT(*) AS cnt FROM forum_categories")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        for name, desc, icon, color, sort_order in INITIAL_CATEGORIES:
            cursor.execute(
                """INSERT INTO forum_categories (name, description, icon, color, sort_order, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (name, desc, icon, color, sort_order, now),
            )

    conn.commit()
    conn.close()
    print("Migración del foro completada correctamente.")


if __name__ == "__main__":
    migrate()
