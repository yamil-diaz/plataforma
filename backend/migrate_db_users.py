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
        cursor.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
        print("Columna is_banned añadida a la tabla users.")
        conn.commit()
    except psycopg2.errors.DuplicateColumn:
        print("La columna is_banned ya existe.")
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    main()
