import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
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
        print("Tabla courses creada.")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_progress (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                completed BOOLEAN DEFAULT TRUE,
                completed_at TEXT NOT NULL,
                UNIQUE(user_id, course_id)
            )
        """)
        print("Tabla course_progress creada.")

        conn.commit()
    except Exception as e:
        print("Error durante la migración de la Fase 2:", e)
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    main()
