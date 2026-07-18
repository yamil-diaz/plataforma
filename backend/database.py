import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre (como un diccionario)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Crear tabla de usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        rayos_balance INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)
    
    # Crear tabla de libros
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author_name TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL DEFAULT 0.0,
        cover_image_url TEXT,
        pdf_path TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        average_rating REAL DEFAULT 0.0,
        total_reviews INTEGER DEFAULT 0,
        published INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)
    
    # Crear tabla de reseñas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(book_id, user_id)
    )
    """)
    
    # Crear tabla de transacciones de Rayos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rayos_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL, -- 'earned', 'spent'
        description TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # Crear índices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book ON reviews(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_book_user ON reviews(book_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rayos_user ON rayos_transactions(user_id)")
    
    # Insertar datos semilla si la tabla de libros está vacía
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        books_seed = [
            (
                "El Principito",
                "Antoine de Saint-Exupéry",
                "Aquí está mi secreto. Es muy simple: no se ve bien sino con el corazón. Lo esencial es invisible a los ojos.\nLos hombres de tu tierra —dijo el principito— cultivan cinco mil rosas en un mismo jardín... y no encuentran lo que buscan.\nY sin embargo, lo que buscan podría encontrarse en una sola rosa o en un poco de agua.\nPero los ojos están ciegos. Hay que buscar con el corazón.",
                "Ficción",
                0.0,
                "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
                None,
                1523,
                342,
                4.5,
                28,
                1,
                now
            ),
            (
                "Cien Años de Soledad",
                "Gabriel García Márquez",
                "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar aquella tarde remota en que su padre lo llevó a conocer el hielo.\nMacondo era entonces una aldea de veinte casas de barro y cañabrava construidas a la orilla de un río de aguas diáfanas que se precipitaban por un lecho de piedras pulidas, blancas y enormes como huevos prehistóricos.\nEl mundo era tan reciente, que muchas cosas carecían de nombre, y para mencionarlas había que señalarlas con el dedo.",
                "Clásicos",
                0.0,
                "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                None,
                1892,
                456,
                4.8,
                35,
                1,
                now
            ),
            (
                "Don Quijote de la Mancha",
                "Miguel de Cervantes",
                "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor.\nUna olla de algo más vaca que carnero, salpicón las más noches, duelos y quebrantos los sábados, lantejas los viernes, algún palomino de añadidura los domingos, consumían las tres partes de su hacienda.",
                "Clásicos",
                0.0,
                "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
                None,
                856,
                178,
                4.2,
                15,
                1,
                now
            ),
            (
                "1984",
                "George Orwell",
                "Era un día luminoso y frío de abril y los relojes daban las trece.\nWinston Smith, con la barbilla clavada en el pecho en su esfuerzo por burlar el azote del viento, se deslizó rápidamente por las puertas de cristal de las Casas de la Victoria, aunque no con la suficiente rapidez para evitar que una ráfaga de polvo arenoso se colara con él.\nEl vestíbulo olía a col hervida y a esteras de esparto. Al fondo, un cartel de colores, demasiado grande para estar colgado en una habitación, estaba pegado a la pared. Representaba sólo un rostro enorme, de más de un metro de anchura: el rostro de un hombre de unos cuarenta y cinco años, con un bigote negro y espeso y facciones toscas pero atractivas.",
                "Ficción",
                0.0,
                "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400",
                None,
                723,
                145,
                4.6,
                22,
                1,
                now
            )
        ]
        cursor.executemany("""
        INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, books_seed)
        
        # También agregamos un usuario administrador semilla
        # Contraseña por defecto: "admin123"
        # Hashed: "$2b$12$ZUXe6118U1i8m5B.QoD0bO51mly1R063q3Lq0aW/R6f1c/7B6W5mC" (bcrypt)
        cursor.execute("""
        INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at)
        VALUES ('Administrador', 'admin@plataforma.com', '$2b$12$ZUXe6118U1i8m5B.QoD0bO51mly1R063q3Lq0aW/R6f1c/7B6W5mC', 'admin', 500, ?)
        """, (now,))
        
        # Y un usuario lector normal de prueba
        # Contraseña: "user123"
        # Hashed: "$2b$12$L7zWw2kZ8jOQ123aM.Z.0e8w/R7z3Lq0aW/R6f1c/7B6W5mC" (simulado/encriptado con bcrypt)
        # Generamos una encriptación real de prueba para el lector
        # bcrypt hash para 'user123': $2b$12$Epy8p8M5J4Z2ZkF72/WbC.O9a7Nn3b3h41gYk/x2XGq26uC9Q40x6
        cursor.execute("""
        INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at)
        VALUES ('Lector de Prueba', 'lector@plataforma.com', '$2b$12$Epy8p8M5J4Z2ZkF72/WbC.O9a7Nn3b3h41gYk/x2XGq26uC9Q40x6', 'user', 100, ?)
        """, (now,))
        
        conn.commit()
        
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")
