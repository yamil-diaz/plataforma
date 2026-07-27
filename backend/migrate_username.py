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

    print("Iniciando migración para añadir username...")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT UNIQUE;")
        print("Columna 'username' añadida.")
        
        # Backfill usernames based on name or id
        cursor.execute("SELECT id, name, email FROM users WHERE username IS NULL")
        users = cursor.fetchall()
        for u in users:
            # Create a simple username from name, lowercase, remove spaces, add id to ensure uniqueness
            base = u["name"].lower().replace(" ", "")
            username = f"{base}{u['id']}"
            cursor.execute("UPDATE users SET username = %s WHERE id = %s", (username, u["id"]))
            
        print("Usernames generados para usuarios existentes.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna 'username' ya existe.")

    conn.commit()
    conn.close()
    print("Migración completada.")

if __name__ == "__main__":
    migrate()
