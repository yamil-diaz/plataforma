import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("Iniciando migración Fase 4.3 (Social & Notificaciones)...")

    # 1. Tabla Notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        content TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    print("Tabla 'notifications' verificada.")

    # 2. Tabla Followers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        follower_id INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (follower_id, following_id),
        FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(following_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    print("Tabla 'followers' verificada.")

    # 3. Alterar Competitions: cambiar book_id (integer) por book_title (text)
    try:
        cursor.execute("ALTER TABLE competitions ADD COLUMN book_title TEXT DEFAULT 'Libro Desconocido';")
        print("Columna 'book_title' añadida a competitions.")
        
        # Migrar datos si los hay
        cursor.execute("UPDATE competitions SET book_title = (SELECT title FROM books WHERE books.id = competitions.book_id) WHERE book_id IS NOT NULL;")
        
        # Opcional: hacer book_id nullable para no romper la tabla inmediatamente
        cursor.execute("ALTER TABLE competitions ALTER COLUMN book_id DROP NOT NULL;")
        print("Migración de datos a book_title completada.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("La columna 'book_title' ya existe en competitions.")
        
    conn.commit()
    conn.close()
    print("Migración Fase 4.3 completada con éxito.")

if __name__ == "__main__":
    migrate()
