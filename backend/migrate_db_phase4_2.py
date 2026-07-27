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

    print("Iniciando migración Fase 4.2 (Competencias)...")

    # 1. Tabla de Competencias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competitions (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, active, completed
        created_at TEXT NOT NULL,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
    )
    """)
    print("Tabla 'competitions' verificada.")

    # 2. Tabla de Preguntas de la Competencia
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competition_questions (
        id SERIAL PRIMARY KEY,
        competition_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL, -- 'A', 'B', 'C', 'D'
        FOREIGN KEY(competition_id) REFERENCES competitions(id) ON DELETE CASCADE
    )
    """)
    print("Tabla 'competition_questions' verificada.")

    # 3. Tabla de Participantes (Inscritos y Resultados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competition_participants (
        id SERIAL PRIMARY KEY,
        competition_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        score INTEGER DEFAULT 0,
        time_taken_ms INTEGER DEFAULT 0,
        status TEXT DEFAULT 'registered', -- registered, submitted
        registered_at TEXT NOT NULL,
        FOREIGN KEY(competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(competition_id, user_id)
    )
    """)
    print("Tabla 'competition_participants' verificada.")

    conn.commit()
    conn.close()
    print("Migración Fase 4.2 completada con éxito.")

if __name__ == "__main__":
    migrate()
