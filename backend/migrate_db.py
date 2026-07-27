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

    # Añadir uploader_id a books si no existe
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN uploader_id INTEGER")
        cursor.execute("ALTER TABLE books ADD CONSTRAINT fk_uploader FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE SET NULL")
        print("Columna uploader_id añadida a la tabla books.")
        
        # Asignar los libros existentes al primer admin (id=1 usualmente)
        cursor.execute("UPDATE books SET uploader_id = (SELECT id FROM users WHERE role = 'admin' LIMIT 1)")
        conn.commit()
        print("Libros existentes asignados al admin.")
    except psycopg2.errors.DuplicateColumn:
        print("La columna uploader_id ya existe.")
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    main()
