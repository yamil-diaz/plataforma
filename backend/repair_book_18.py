#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de reparación controlada para El Principito (ID 18).

Este script:
1. Consulta el contenido actual de ID 18
2. Guarda métricas antes de modificar
3. VALIDA que el contenido NO sea patológico antes de reparar
4. Elimina únicamente sus registros de book_pages
5. Vuelve a generar las páginas usando la función corregida (deduplicate=True explícito)
6. Actualiza page_count
7. Comprueba que no existen páginas consecutivas idénticas
8. Comprueba que el número de páginas coincide con COUNT(book_pages)
9. Utiliza una transacción
10. Hace rollback si alguna validación falla

NO se ejecuta automáticamente. Debe ejecutarse manualmente cuando se autorice.
"""

import os
import sys
import psycopg2
import psycopg2.extras

# Añadir el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura


def get_database_url():
    """Obtiene DATABASE_URL del entorno."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL no está definida en el entorno")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def main():
    DATABASE_URL = get_database_url()
    
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    BOOK_ID = 18
    
    try:
        # 1. Consultar el libro actual
        print("=== REPARACIÓN EL PRINCIPITO (ID 18) ===")
        print()
        
        cursor.execute("""
            SELECT id, title, content, page_count, paginated_at, LENGTH(content) as content_len
            FROM books WHERE id = %s
        """, (BOOK_ID,))
        book = cursor.fetchone()
        
        if not book:
            print(f"ERROR: Libro ID {BOOK_ID} no encontrado")
            return False
        
        print(f"Libro: {book['title']} (ID {book['id']})")
        print(f"Content length: {book['content_len']}")
        print(f"Page count actual: {book['page_count']}")
        print(f"Paginated at: {book['paginated_at']}")
        
        # 2. MÉTRICAS Y VALIDACIÓN PREVIA OBLIGATORIA
        print("\n--- Validación previa obligatoria ---")
        
        # Detectar contenido patológico ANTES de reparar
        diagnostico = lectura.detectar_contenido_patologico(book['content'])
        print(f"Contenido patológico: {diagnostico['pathological']}")
        if diagnostico['pathological']:
            print(f"  RAZÓN: {diagnostico['reason']}")
            print(f"  Repetition ratio: {diagnostico['repetition_ratio']:.1%}")
            print(f"  Repeated fragments: {diagnostico['repeated_fragment_count']}")
            print(f"  Duplicados consecutivos: {diagnostico['duplicate_consecutive_pages']}")
            print("  ABORTANDO: El contenido es patológico. No se puede reparar automáticamente.")
            print("  ACCIÓN REQUERIDA: Re-cargar desde fuente original (Gutenberg/PDF limpio).")
            return False
        
        print("✓ Contenido NO patológico - apto para reparación")
        
        # Métricas antes - book_pages actuales
        cursor.execute("""
            SELECT page_number, content FROM book_pages WHERE book_id = %s ORDER BY page_number
        """, (BOOK_ID,))
        old_pages = cursor.fetchall()
        
        print(f"\nPáginas actuales en book_pages: {len(old_pages)}")
        
        # Verificar duplicados actuales
        dup_count = 0
        for i in range(len(old_pages) - 1):
            if old_pages[i]['content'] == old_pages[i+1]['content']:
                dup_count += 1
                print(f"  DUPLICADO: Page {old_pages[i]['page_number']} = Page {old_pages[i+1]['page_number']} ({len(old_pages[i]['content'])} chars)")
        
        print(f"Total pares consecutivos duplicados ANTES: {dup_count}")
        
        # 3. Generar nuevas páginas con deduplicate=True (explícito para reparación admin)
        print("\n--- Generando nuevas páginas con deduplicate=True (reparación admin) ---")
        new_pages = lectura.paginar_desde_contenido(book['content'], deduplicate=True)
        new_capitulos = lectura.detectar_capitulos(new_pages)
        
        print(f"Nuevas páginas generadas: {len(new_pages)}")
        for i, p in enumerate(new_pages):
            print(f"  Page {i+1}: {len(p)} chars")
        
        # Verificar que no hay duplicados consecutivos en las nuevas
        new_dups = 0
        for i in range(len(new_pages) - 1):
            if new_pages[i] == new_pages[i+1]:
                new_dups += 1
                print(f"  ERROR: Page {i+1} = Page {i+2} ({len(new_pages[i])} chars)")
        
        if new_dups > 0:
            print(f"FALLO: Las nuevas páginas tienen {new_dups} duplicados consecutivos. ABORTANDO.")
            return False
        
        print(f"✓ Nuevas páginas SIN duplicados consecutivos")
        
        # Validar contenido
        validacion = lectura.validar_contenido_libro(book['content'], new_pages, fuente='content')
        print(f"Validación: {'VÁLIDA' if validacion['valid'] else 'INVÁLIDA'}")
        if not validacion['valid']:
            print(f"  Errores: {validacion['errors']}")
            print("  ABORTANDO: El contenido no pasa validación tras reparación.")
            return False
        
        # 4. Transacción: borrar páginas viejas e insertar nuevas
        print("\n--- Iniciando transacción ---")
        
        # Borrar book_pages existentes
        cursor.execute("DELETE FROM book_pages WHERE book_id = %s", (BOOK_ID,))
        deleted = cursor.rowcount
        print(f"Borradas {deleted} páginas antiguas")
        
        # Borrar chapters existentes
        cursor.execute("DELETE FROM chapters WHERE book_id = %s", (BOOK_ID,))
        deleted_ch = cursor.rowcount
        print(f"Borrados {deleted_ch} capítulos antiguos")
        
        # Insertar nuevos capítulos
        capitulo_ids = {}
        for cap in new_capitulos:
            cursor.execute(
                "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
                (BOOK_ID, cap['title'], cap['page']),
            )
            capitulo_ids[cap['page']] = cursor.fetchone()['id']
        
        print(f"Insertados {len(capitulo_ids)} capítulos nuevos")
        
        # Insertar nuevas book_pages
        filas = [
            (BOOK_ID, i, texto, capitulo_ids.get(i))
            for i, texto in enumerate(new_pages, start=1)
        ]
        
        if filas:
            cursor.executemany(
                "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
                filas,
            )
        
        print(f"Insertadas {len(filas)} páginas nuevas")
        
        # Actualizar books.page_count y paginated_at
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        cursor.execute(
            "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
            (len(new_pages), now, BOOK_ID),
        )
        
        print(f"Actualizado books.page_count = {len(new_pages)}")
        print(f"Actualizado books.paginated_at = {now}")
        
        # 5. Verificaciones post-transacción
        print("\n--- Verificaciones post-reparación ---")
        
        # Verificar page_count coincide
        cursor.execute("SELECT COUNT(*) as cnt FROM book_pages WHERE book_id = %s", (BOOK_ID,))
        actual_count = cursor.fetchone()['cnt']
        print(f"COUNT(book_pages): {actual_count}")
        print(f"books.page_count: {len(new_pages)}")
        print(f"Coinciden: {'✓' if actual_count == len(new_pages) else '✗ FALLO'}")
        
        if actual_count != len(new_pages):
            raise Exception("page_count no coincide con COUNT(book_pages)")
        
        # Verificar que no hay duplicados consecutivos en BD
        cursor.execute("""
            SELECT bp1.page_number, bp1.content
            FROM book_pages bp1
            JOIN book_pages bp2 ON bp1.book_id = bp2.book_id AND bp1.page_number = bp2.page_number - 1
            WHERE bp1.book_id = %s AND bp1.content = bp2.content
        """, (BOOK_ID,))
        db_dups = cursor.fetchall()
        
        print(f"Duplicados consecutivos en BD: {len(db_dups)}")
        if db_dups:
            for d in db_dups:
                print(f"  Page {d['page_number']} = Page {d['page_number']+1}")
            raise Exception("Quedan duplicados consecutivos en BD")
        
        print("✓ Sin duplicados consecutivos en BD")
        
        # Verificar integridad del contenido (concatenación)
        cursor.execute("SELECT content FROM book_pages WHERE book_id = %s ORDER BY page_number", (BOOK_ID,))
        final_pages = cursor.fetchall()
        concatenated = ''.join(p['content'] for p in final_pages)
        print(f"Contenido concatenado de páginas: {len(concatenated)} chars")
        print(f"books.content original: {book['content_len']} chars")
        if concatenated != book['content']:
            print("⚠ DIFIEREN: Se eliminaron bloques duplicados consecutivos (esperado con deduplicate=True)")
        else:
            print("✓ Contenido idéntico al original")
        
        # Commit
        conn.commit()
        print("\n=== REPARACIÓN COMPLETADA CON ÉXITO ===")
        print(f"Páginas finales: {len(new_pages)}")
        print(f"Duplicados consecutivos: 0")
        print(f"page_count actualizado: {len(new_pages)}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n=== ERROR: {e} ===")
        print("ROLLBACK ejecutado. No se modificó nada.")
        return False
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)