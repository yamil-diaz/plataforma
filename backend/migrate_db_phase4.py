import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("Iniciando migración Fase 4.1 (Perfiles e Insignias)...")

    # 1. Añadir nuevas columnas a la tabla users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT '';")
        print("Columna 'bio' añadida.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna 'bio' ya existe.")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN favorite_genres TEXT DEFAULT '';")
        print("Columna 'favorite_genres' añadida.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna 'favorite_genres' ya existe.")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image_url TEXT DEFAULT '';")
        print("Columna 'profile_image_url' añadida.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna 'profile_image_url' ya existe.")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN historical_rayos INTEGER DEFAULT 0;")
        print("Columna 'historical_rayos' añadida.")
        
        # Igualar historical_rayos con rayos_balance para los usuarios existentes
        cursor.execute("UPDATE users SET historical_rayos = rayos_balance WHERE historical_rayos = 0;")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna 'historical_rayos' ya existe.")

    # 2. Crear tabla badges
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        icon_url TEXT NOT NULL,
        criteria_type TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    print("Tabla 'badges' verificada.")

    # 3. Crear tabla user_badges
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        badge_id INTEGER NOT NULL,
        awarded_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(badge_id) REFERENCES badges(id) ON DELETE CASCADE,
        UNIQUE(user_id, badge_id)
    )
    """)
    print("Tabla 'user_badges' verificada.")

    # Insertar insignias semilla si no existen
    cursor.execute("SELECT COUNT(*) AS cnt FROM badges")
    if cursor.fetchone()["cnt"] == 0:
        now = datetime.now(timezone.utc).isoformat()
        seed_badges = [
            ("Lector Voraz", "Has leído más de 10 libros", "🏆", "books_read_10", now),
            ("Mecenas", "Has realizado tu primera donación", "💎", "first_donation", now),
            ("Campeón", "Ganaste el primer lugar en una competencia", "👑", "competition_winner", now),
            ("Alma Poética", "Participaste en el torneo de Poesía", "✒️", "poetry_tournament", now),
            ("Embajador", "Invitaste a nuevos usuarios a la plataforma", "🤝", "ambassador", now)
        ]
        cursor.executemany(
            "INSERT INTO badges (name, description, icon_url, criteria_type, created_at) VALUES (%s, %s, %s, %s, %s)",
            seed_badges
        )
        print("Insignias semilla insertadas.")

    conn.commit()
    conn.close()
    print("Migración Fase 4.1 completada con éxito.")

if __name__ == "__main__":
    migrate()
