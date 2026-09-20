#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storage_config import STORAGE_BOOKS

DATABASE_URL = r'postgresql://postgres:postgres@localhost:5432/plataforma_dev'

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print('=== FASE 1: VERIFICACION POST-ELIMINACION ===')
    print()

    # 1. ID 128 ya no existe
    cursor.execute('SELECT id, title, author_name FROM books WHERE id = 128')
    result = cursor.fetchone()
    print('1. ID 128 existe:', result is not None)
    if result:
        print('   Titulo:', result['title'], '| Autor:', result['author_name'])

    # 2. ID 18 sigue existiendo
    cursor.execute('SELECT id, title, author_name FROM books WHERE id = 18')
    result = cursor.fetchone()
    print('2. ID 18 existe:', result is not None)
    if result:
        print('   Titulo:', result['title'], '| Autor:', result['author_name'])

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
        cursor.execute('SELECT COUNT(*) as cnt FROM %s WHERE %s = 128' % (table, column))
        cnt = cursor.fetchone()['cnt']
        if cnt > 0:
            orphaned = True
            print('3. DEPENDENCIA HUERFANA:', table, '.', column, '=', cnt)

    if not orphaned:
        print('3. No hay dependencias huérfanas de ID 128')

    # 4. Duplicados de El Principito
    cursor.execute("""
        SELECT id, title, author_name 
        FROM books 
        WHERE title ILIKE '%principito%' AND author_name ILIKE '%saint-exupery%'
    """)
    dups = cursor.fetchall()
    print('4. Libros El Principito de Saint-Exupery:', len(dups))
    for d in dups:
        print('   ID', d['id'], ':', d['title'], '-', d['author_name'])

    # 5. Todos los libros con detalles
    print()
    print('5. CATALOGO COMPLETO:')
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
    print('   Total libros:', len(all_books))
    print()
    for b in all_books:
        pdf_exists = 'N/A'
        if b['pdf_path']:
            import os
            path = b['pdf_path'] if os.path.isabs(b['pdf_path']) else os.path.join(STORAGE_BOOKS, os.path.basename(b['pdf_path']))
            pdf_exists = 'SI' if os.path.isfile(path) else 'NO'
        print('   ID %3d: %40s | Autor: %25s | Chars: %6d | Pages: %3d | book_pages: %3d | chapters: %2d | PDF: %s (%s)' % (
            b['id'], b['title'][:40], b['author_name'][:25], b['content_len'], b['page_count'], b['n_book_pages'], b['n_chapters'], b['pdf_path'] or '-', pdf_exists))

    conn.close()

if __name__ == '__main__':
    main()