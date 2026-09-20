#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 1 — VERIFICACIÓN POST-ELIMINACIÓN
Solo lectura, no modifica nada.
"""
import os
import sys
import psycopg2
import psycopg2.extras

# Hardcoded for local testing
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/plataforma_dev"

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("=== FASE 1: VERIFICACIÓN POST-ELIMINACIÓN ===")
    print()

    # 1. ID 128 ya no existe
    cursor.execute('SELECT id, title, author_name FROM books WHERE id = 128')
    result = cursor.fetchone()
    print(f"1. ID 128 existe: {result is not None}")
    if result:
        print(f"   Título: {result['title']}, Autor: {result['author_name']}")

    # 2. ID 18 sigue existiendo
    cursor.execute('SELECT id, title, author_name FROM books WHERE id = 18')
    result = cursor.fetchone()
    print(f"2. ID 18 existe: {result is not None}")
    if result:
        print(f"   Título: {result['title']}, Autor: {result['author_name']}")

    # 3. Dependencias huérfanas de ID 128
    cursor.execute("""
        SELECT 
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'books'
          AND ccu.column_name = 'id'
    """)
    fks = cursor.fetchall()

    orphaned = False
    for fk in fks:
        table = fk['table_name']
        column = fk['column_name']
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE {column} = 128")
        cnt = cursor.fetchone()['cnt']
        if cnt > 0:
            orphaned = True
            print(f"3. DEPENDENCIA HUERFANA: {table}.{column} = {cnt}")

    if not orphaned:
        print("3. No hay dependencias huérfanas de ID 128")

    # 4. Duplicados de El Principito
    cursor.execute("""
        SELECT id, title, author_name 
        FROM books 
        WHERE title ILIKE '%principito%' AND author_name ILIKE '%saint-exupery%'
    """)
    dups = cursor.fetchall()
    print(f"4. Libros 'El Principito' de Saint-Exupéry: {len(dups)}")
    for d in dups:
        print(f"   ID {d['id']}: {d['title']} - {d['author_name']}")

    # 5. Todos los libros con detalles
    print()
    print("5. CATÁLOGO COMPLETO:")
    cursor.execute("""
        SELECT 
            b.id, b.title, b.author_name, 
            LENGTH(b.content) as content_len,
            b.page_count,
            (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) as n_book_pages,
            (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) as n_chapters,
            b.pdf_path
        FROM books b
        ORDER BY b.id
    """)
    all_books = cursor.fetchall()
    print(f"   Total libros: {len(all_books)}")
    print()
    for b in all_books:
        pdf_exists = 'N/A'
        if b['pdf_path']:
            path = b['pdf_path'] if os.path.isabs(b['pdf_path']) else os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'storage/books', os.path.basename(b['pdf_path'])
            )
            pdf_exists = 'SÍ' if os.path.isfile(path) else 'NO'
        print(f"   ID {b['id']:3d}: {b['title'][:40]:40s} | Autor: {b['author_name'][:25]:25s} | Chars: {b['content_len']:6d} | Pages: {b['page_count']:3d} | book_pages: {b['n_book_pages']:3d} | chapters: {b['n_chapters']:2d} | PDF: {b['pdf_path'] or '-'} ({pdf_exists})")

    conn.close()

if __name__ == "__main__":
    main()