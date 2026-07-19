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
        created_at TEXT NOT NULL
    )
    """)

    # ── Tabla de libros ──────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        author_name TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL DEFAULT 0.0,
        cover_image_url TEXT,
        pdf_path TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        average_rating REAL DEFAULT 0.0,
        total_reviews INTEGER DEFAULT 0,
        published INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rayos_transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # ── Índices ──────────────────────────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book ON reviews(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book_user ON reviews(book_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rayos_user ON rayos_transactions(user_id)")

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
