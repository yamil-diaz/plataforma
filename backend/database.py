import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

# Render inyecta DATABASE_URL automáticamente cuando enlazas una PostgreSQL DB
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está definida. "
        "Asegúrate de enlazar una base de datos PostgreSQL en Render."
    )

# psycopg2 requiere 'postgresql://' en vez de 'postgres://' (que usa Render por defecto)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    """Crea y devuelve una conexión nueva a PostgreSQL.
    El llamador es responsable de hacer conn.close() cuando termine.
    """
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """Crea las tablas e índices si no existen. Inserta datos semilla si la tabla está vacía."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    # ── Tabla de usuarios ────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        rayos_balance INTEGER DEFAULT 0,
        historical_rayos INTEGER DEFAULT 0,
        username VARCHAR(50) UNIQUE,
        bio TEXT,
        profile_image_url TEXT,
        favorite_genres TEXT,
        reset_token VARCHAR(255),
        reset_token_expiry TIMESTAMP,
        is_banned BOOLEAN DEFAULT FALSE,
        registration_ip TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Migraciones seguras para columnas añadidas posteriormente
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_ip TEXT")
        conn.commit()
    except Exception as e:
        conn.rollback()
        pass

    # ── Tabla de libros ──────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        author_name TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL DEFAULT 0.0,
        pdf_path TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        average_rating REAL DEFAULT 0.0,
        total_reviews INTEGER DEFAULT 0,
        published INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    try:
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS dislikes INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS paginated_at TEXT")
        conn.commit()
    except Exception as e:
        conn.rollback()
        pass

    # ── Tabla de reseñas ─────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(book_id, user_id)
    )
    """)

    # ── Tabla de transacciones Rayos ─────────────────────────────────────────
    # FASE 1: user_id puede ser NULL (la quema del 10% se registra a nivel de
    # sistema); la FK se conserva para el resto de transacciones.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rayos_transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        book_id INTEGER,
        course_id INTEGER,
        competition_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Migraciones idempotentes (compatibles con BDs existentes y deploys frescos)
    try:
        cursor.execute("ALTER TABLE rayos_transactions ADD COLUMN IF NOT EXISTS book_id INTEGER")
        cursor.execute("ALTER TABLE rayos_transactions ADD COLUMN IF NOT EXISTS course_id INTEGER")
        cursor.execute("ALTER TABLE rayos_transactions ADD COLUMN IF NOT EXISTS competition_id INTEGER")
        cursor.execute("ALTER TABLE rayos_transactions ALTER COLUMN user_id DROP NOT NULL")
        conn.commit()
    except Exception as e:
        conn.rollback()
        pass

    # ── Índices ──────────────────────────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book ON reviews(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book_user ON reviews(book_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rayos_user ON rayos_transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rayos_user_type ON rayos_transactions(user_id, type)")

    # ── Cursos (FASE 1: se crean aquí para que un deploy fresco funcione) ────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        instructor TEXT NOT NULL,
        category TEXT NOT NULL,
        video_url TEXT NOT NULL,
        cover_url TEXT NOT NULL,
        reward_amount INTEGER NOT NULL DEFAULT 50,
        views INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        uploader_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS course_progress (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        completed BOOLEAN DEFAULT TRUE,
        started_at TEXT,
        completed_at TEXT,
        UNIQUE(user_id, course_id)
    )
    """)

    try:
        cursor.execute("ALTER TABLE course_progress ADD COLUMN IF NOT EXISTS started_at TEXT")
        cursor.execute("ALTER TABLE course_progress ALTER COLUMN completed_at DROP NOT NULL")
        conn.commit()
    except Exception as e:
        conn.rollback()
        pass

    # ── Notificaciones (FASE 1: necesarias para donaciones en deploy fresco) ─
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        type TEXT,
        content TEXT,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TEXT NOT NULL
    )
    """)

    # ── Tabla de interacciones (Likes/Dislikes) ──────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book_interactions (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        interaction_type TEXT NOT NULL CHECK (interaction_type IN ('like', 'dislike')),
        created_at TEXT NOT NULL,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(book_id, user_id)
    )
    """)

    # ── FASE 2: Lectura por páginas y meta diaria ────────────────────────────
    # Capítulos: solo organización y navegación, NO son unidad de recompensa.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chapters (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        start_page INTEGER NOT NULL,
        UNIQUE(book_id, start_page)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book_pages (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        content TEXT NOT NULL,
        chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
        UNIQUE(book_id, page_number)
    )
    """)

    # Sesiones de lectura: una por usuario y libro (se reactiva al volver).
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        started_at TEXT NOT NULL,
        last_active_at TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        UNIQUE(user_id, book_id)
    )
    """)

    # Última página alcanzada (resume). Solo avanza, nunca retrocede.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_progress (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        reached_at TEXT NOT NULL,
        UNIQUE(user_id, book_id)
    )
    """)

    # Páginas únicas por día (meta diaria anti-farm: una página cuenta una
    # vez por día aunque se vuelva a visitar).
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_daily_pages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        day TEXT NOT NULL,
        UNIQUE(user_id, book_id, page_number, day)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_pages_book ON book_pages(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reading_daily_user_day ON reading_daily_pages(user_id, day)")

    conn.commit()

    # ── Datos semilla ────────────────────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) AS cnt FROM books")
    row = cursor.fetchone()
    count = row["cnt"] if row else 0

    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        books_seed = [
            (
                "El Principito",
                "Antoine de Saint-Exupéry",
                "Aquí está mi secreto. Es muy simple: no se ve bien sino con el corazón. Lo esencial es invisible a los ojos.\nLos hombres de tu tierra —dijo el principito— cultivan cinco mil rosas en un mismo jardín... y no encuentran lo que buscan.\nY sin embargo, lo que buscan podría encontrarse en una sola rosa o en un poco de agua.\nPero los ojos están ciegos. Hay que buscar con el corazón.",
                "Ficción",
                0.0,
                "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
                None,
                1523,
                342,
                4.5,
                28,
                1,
                now,
            ),
            (
                "Cien Años de Soledad",
                "Gabriel García Márquez",
                "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar aquella tarde remota en que su padre lo llevó a conocer el hielo.\nMacondo era entonces una aldea de veinte casas de barro y cañabrava construidas a la orilla de un río de aguas diáfanas que se precipitaban por un lecho de piedras pulidas, blancas y enormes como huevos prehistóricos.",
                "Clásicos",
                0.0,
                "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                None,
                1892,
                456,
                4.8,
                35,
                1,
                now,
            ),
            (
                "Don Quijote de la Mancha",
                "Miguel de Cervantes",
                "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor.",
                "Clásicos",
                0.0,
                "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
                None,
                856,
                178,
                4.2,
                15,
                1,
                now,
            ),
            (
                "1984",
                "George Orwell",
                "Era un día luminoso y frío de abril y los relojes daban las trece.\nWinston Smith, con la barbilla clavada en el pecho en su esfuerzo por burlar el azote del viento, se deslizó rápidamente por las puertas de cristal de las Casas de la Victoria.",
                "Ficción",
                0.0,
                "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400",
                None,
                723,
                145,
                4.6,
                22,
                1,
                now,
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url,
                               pdf_path, views, likes, average_rating, total_reviews, published, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            books_seed,
        )

        # Usuario admin semilla  (contraseña: admin123)
        cursor.execute(
            """
            INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at)
            VALUES (%s, %s, %s, 'admin', 500, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            (
                "Administrador",
                "admin@plataforma.com",
                "$2b$12$ZUXe6118U1i8m5B.QoD0bO51mly1R063q3Lq0aW/R6f1c/7B6W5mC",
                now,
            ),
        )

        # Usuario lector semilla  (contraseña: user123)
        cursor.execute(
            """
            INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at)
            VALUES (%s, %s, %s, 'user', 100, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            (
                "Lector de Prueba",
                "lector@plataforma.com",
                "$2b$12$Epy8p8M5J4Z2ZkF72/WbC.O9a7Nn3b3h41gYk/x2XGq26uC9Q40x6",
                now,
            ),
        )

        conn.commit()

    conn.close()


if __name__ == "__main__":
    init_db()
    print("Base de datos PostgreSQL inicializada correctamente.")
