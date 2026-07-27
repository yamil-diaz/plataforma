import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load from ../.env if possible
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("Iniciando migración Fase 4.5 (Email Tokens)...")

    # Add reset_token and reset_token_expiry to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)")
        print("Columna reset_token añadida.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna reset_token ya existe.")
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP")
        print("Columna reset_token_expiry añadida.")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Columna reset_token_expiry ya existe.")
        
    conn.commit()
    conn.close()
    print("Migración de Fase 4.5 completada con éxito.")

if __name__ == "__main__":
    migrate()
