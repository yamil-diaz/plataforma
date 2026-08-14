# -*- coding: utf-8 -*-
"""
Migración FASE 2 (Lectura por páginas y meta diaria).

1. Crea las tablas de lectura (idempotente, seguro en deploys frescos).
2. Backfill: libros sin páginas registradas se paginan ahora mismo:
   - Con pdf_path en disco -> re-extracción real con pypdf + detección de capítulos.
   - Sin PDF (Gutenberg, semillas) -> paginación estimada desde books.content.

Los capítulos detectados no dan recompensas: son solo organización y navegación.
"""
import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_BOOKS = os.path.join(BASE_DIR, "storage", "books")


def _crear_tablas(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chapters (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        start_page INTEGER NOT NULL,
        UNIQUE(book_id, start_page)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book_pages (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        content TEXT NOT NULL,
        chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
        UNIQUE(book_id, page_number)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        started_at TEXT NOT NULL,
        last_active_at TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        UNIQUE(user_id, book_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_progress (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        reached_at TEXT NOT NULL,
        UNIQUE(user_id, book_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_daily_pages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        day TEXT NOT NULL,
        UNIQUE(user_id, book_id, page_number, day)
    )
    """)
    cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS paginated_at TEXT")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_pages_book ON book_pages(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reading_daily_user_day ON reading_daily_pages(user_id, day)")


def _guardar_estructura(cursor, book_id, paginas, capitulos):
    capitulo_ids = {}
    for cap in capitulos:
        cursor.execute(
            "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
            (book_id, cap["title"], cap["page"]),
        )
        capitulo_ids[cap["page"]] = cursor.fetchone()["id"]
    for i, texto in enumerate(paginas, start=1):
        cursor.execute(
            "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
            (book_id, i, texto, capitulo_ids.get(i)),
        )
    cursor.execute("UPDATE books SET page_count = %s WHERE id = %s", (len(paginas), book_id))


def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("Iniciando migración FASE 2 (Lectura por páginas)...")
    _crear_tablas(cursor)
    conn.commit()

    cursor.execute(
        """
        SELECT id, title, pdf_path, content FROM books
        WHERE paginated_at IS NULL
          AND NOT EXISTS (SELECT 1 FROM book_pages WHERE book_id = books.id)
        ORDER BY id
        """
    )
    libros = cursor.fetchall()
    print(f"Libros sin paginar: {len(libros)}")

    ok = 0
    for libro in libros:
        book_id = libro["id"]
        try:
            paginas = []
            pdf_path = libro["pdf_path"]
            if pdf_path and not os.path.isabs(pdf_path):
                pdf_path = os.path.join(STORAGE_BOOKS, pdf_path)
            if pdf_path and os.path.exists(pdf_path):
                paginas = lectura.extraer_paginas(pdf_path)
                capitulos = lectura.detectar_capitulos(paginas)
            else:
                paginas = lectura.paginar_desde_contenido(libro["content"])
                capitulos = []
            if not paginas:
                paginas = lectura.paginar_desde_contenido(libro["content"])
                capitulos = []
            now = datetime.now(timezone.utc).isoformat()
            if paginas:
                _guardar_estructura(cursor, book_id, paginas, capitulos)
            cursor.execute(
                "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
                (len(paginas), now, book_id),
            )
            conn.commit()
            ok += 1
            print(f"  + libro {book_id} ({libro['title']}): {len(paginas)} páginas, {len(capitulos)} capítulos")
        except Exception as e:
            conn.rollback()
            print(f"  ! libro {book_id} ({libro['title']}) falló: {e}")

    conn.close()
    print(f"Migración FASE 2 completada: {ok}/{len(libros)} libros paginados.")


if __name__ == "__main__":
    migrate()
