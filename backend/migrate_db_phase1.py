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
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL
            )
        """)
        print("Tabla notifications creada.")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Insert default settings if empty
        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO settings (key, value) VALUES ('LOAN_DAYS', '365')")
            cursor.execute("INSERT INTO settings (key, value) VALUES ('AETHERS_REWARD', '10')")
        print("Tabla settings creada y poblada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used BOOLEAN DEFAULT FALSE
            )
        """)
        print("Tabla password_resets creada.")
        
        # Note: We will handle login attempts in memory for now to avoid DB spam, 
        # or we could use a simple table. Let's use a table for persistence.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip_address TEXT PRIMARY KEY,
                attempts INTEGER DEFAULT 0,
                lockout_until TEXT
            )
        """)
        print("Tabla login_attempts creada.")

        conn.commit()
    except Exception as e:
        print("Error durante la migración:", e)
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    main()
