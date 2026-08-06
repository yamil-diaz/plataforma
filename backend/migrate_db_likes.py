import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no encontrada")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def run_migration():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    # 1. Add dislikes to books
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS dislikes INTEGER DEFAULT 0")
        conn.commit()
        print("Columna 'dislikes' añadida a 'books'")
    except Exception as e:
        conn.rollback()
        print(f"Error añadiendo dislikes: {e}")

    # 2. Create book_interactions
    try:
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
        conn.commit()
        print("Tabla 'book_interactions' creada")
    except Exception as e:
        conn.rollback()
        print(f"Error creando book_interactions: {e}")
        
    conn.close()

if __name__ == "__main__":
    run_migration()
