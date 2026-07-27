import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content FROM books")
    books = cursor.fetchall()

    for book in books:
        original_content = book['content']
        # Si el contenido es corto, lo multiplicamos para simular un libro completo
        if len(original_content) < 5000: 
            # Crear capítulos falsos repitiendo el texto
            long_content = ""
            for chapter in range(1, 11): # 10 capítulos
                long_content += f"\n\nCAPÍTULO {chapter}\n\n"
                # Repetimos el párrafo base 20 veces por capítulo
                long_content += (original_content + "\n\n") * 20
            
            cursor.execute(
                "UPDATE books SET content = %s WHERE id = %s",
                (long_content, book['id'])
            )
            print(f"Libro actualizado (texto largo generado): {book['title']}")

    conn.commit()
    conn.close()
    print("¡Todos los libros han sido actualizados con texto largo!")

if __name__ == "__main__":
    main()
