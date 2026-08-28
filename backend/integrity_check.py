#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramienta de diagnóstico de integridad SOLO LECTURA.

Comprueba:
- libros sin PDF
- PDF path existente/no existente
- page_count vs COUNT(book_pages)
- páginas duplicadas consecutivas
- páginas vacías
- libros duplicados por hash
- book_pages huérfanas
- chapters huérfanos
- rayos_transactions con book_id inexistente

Uso:
    DATABASE_URL="postgresql://..." python backend/integrity_check.py [--output report.json]
"""

import os
import sys
import json
import hashlib
import argparse
import psycopg2
import psycopg2.extras


CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible."


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    import unicodedata
    import re
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", "", texto.lower())
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _calcular_hash_pdf(pdf_path: str) -> str:
    """Calcula SHA-256 del archivo PDF."""
    h = hashlib.sha256()
    try:
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _resolver_pdf_path(pdf_path, storage_books):
    """Resuelve pdf_path contra almacenamiento local."""
    if not pdf_path:
        return None
    if os.path.isabs(pdf_path) and os.path.isfile(pdf_path):
        return pdf_path
    candidata = os.path.join(storage_books, os.path.basename(pdf_path))
    if os.path.isfile(candidata):
        return candidata
    return None


def main():
    parser = argparse.ArgumentParser(description="Diagnóstico de integridad SOLO LECTURA")
    parser.add_argument("--storage", default=None, help="Directorio de almacenamiento local (para verificar PDFs)")
    parser.add_argument("--output", default=None, help="Archivo JSON para guardar el reporte")
    args = parser.parse_args()

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no está definida en el entorno", file=sys.stderr)
        return 1
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    STORAGE_BOOKS = args.storage or os.path.join(os.path.dirname(__file__), "storage", "books")

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    reporte = {
        "resumen": {},
        "libros_sin_pdf": [],
        "page_count_inconsistente": [],
        "paginas_duplicadas_consecutivas": [],
        "paginas_vacias_cortas": [],
        "libros_duplicados_por_hash": [],
        "book_pages_huerfanas": [],
        "chapters_huerfanos": [],
        "rayos_transactions_huerfanas": [],
    }

    try:
        # 1. LIBROS SIN PDF
        cursor.execute("""
            SELECT id, title, author_name, LENGTH(content) as content_len, pdf_path, page_count, published, created_at,
                   (SELECT COUNT(*) FROM book_pages WHERE book_id = b.id) as bp_count
            FROM books b
            WHERE pdf_path IS NULL
            ORDER BY id
        """)
        libros_sin_pdf = cursor.fetchall()
        reporte["libros_sin_pdf"] = [dict(r) for r in libros_sin_pdf]

        # 2. PAGE_COUNT INCONSISTENTE
        cursor.execute("""
            SELECT b.id, b.title, b.page_count, COUNT(bp.id) as actual_pages
            FROM books b
            LEFT JOIN book_pages bp ON b.id = bp.book_id
            GROUP BY b.id, b.title, b.page_count
            HAVING b.page_count != COUNT(bp.id)
        """)
        inconsistentes = cursor.fetchall()
        reporte["page_count_inconsistente"] = [dict(r) for r in inconsistentes]

        # 3. PÁGINAS DUPLICADAS CONSECUTIVAS
        cursor.execute("""
            SELECT bp1.book_id, b.title, bp1.page_number, bp1.content
            FROM book_pages bp1
            JOIN book_pages bp2 ON bp1.book_id = bp2.book_id AND bp1.page_number = bp2.page_number - 1
            JOIN books b ON bp1.book_id = b.id
            WHERE bp1.content = bp2.content AND bp1.content != ''
            ORDER BY bp1.book_id, bp1.page_number
        """)
        dup_pages = cursor.fetchall()
        reporte["paginas_duplicadas_consecutivas"] = [
            {"book_id": r["book_id"], "title": r["title"], "page_number": r["page_number"], "chars": len(r["content"])}
            for r in dup_pages
        ]

        # 4. PÁGINAS VACÍAS O CORTAS (< 50 chars)
        cursor.execute("""
            SELECT bp.book_id, b.title, bp.page_number, bp.content
            FROM book_pages bp
            JOIN books b ON bp.book_id = b.id
            WHERE LENGTH(bp.content) < 50
            ORDER BY bp.book_id, bp.page_number
        """)
        short_pages = cursor.fetchall()
        reporte["paginas_vacias_cortas"] = [
            {"book_id": r["book_id"], "title": r["title"], "page_number": r["page_number"], "chars": len(r["content"]), "content_preview": r["content"][:100]}
            for r in short_pages
        ]

        # 5. LIBROS DUPLICADOS POR HASH DE PDF
        cursor.execute("SELECT id, title, author_name, pdf_path FROM books WHERE pdf_path IS NOT NULL")
        libros_con_pdf = cursor.fetchall()
        
        # Agrupar por hash de PDF
        hash_map = {}
        for libro in libros_con_pdf:
            resolved = _resolver_pdf_path(libro["pdf_path"], STORAGE_BOOKS)
            if resolved and os.path.isfile(resolved):
                pdf_hash = _calcular_hash_pdf(resolved)
                if pdf_hash:
                    if pdf_hash not in hash_map:
                        hash_map[pdf_hash] = []
                    hash_map[pdf_hash].append({
                        "id": libro["id"],
                        "title": libro["title"],
                        "author_name": libro["author_name"],
                        "pdf_path": libro["pdf_path"],
                        "resolved_path": resolved
                    })

        for pdf_hash, grupo in hash_map.items():
            if len(grupo) > 1:
                reporte["libros_duplicados_por_hash"].append({
                    "pdf_hash": pdf_hash[:16],
                    "libros": grupo
                })

        # 6. BOOK_PAGES HUÉRFANAS
        cursor.execute("""
            SELECT bp.book_id, COUNT(*) as cnt
            FROM book_pages bp
            LEFT JOIN books b ON bp.book_id = b.id
            WHERE b.id IS NULL
            GROUP BY bp.book_id
        """)
        orphan_pages = cursor.fetchall()
        reporte["book_pages_huerfanas"] = [dict(r) for r in orphan_pages]

        # 7. CHAPTERS HUÉRFANOS
        cursor.execute("""
            SELECT c.book_id, COUNT(*) as cnt
            FROM chapters c
            LEFT JOIN books b ON c.book_id = b.id
            WHERE b.id IS NULL
            GROUP BY c.book_id
        """)
        orphan_chapters = cursor.fetchall()
        reporte["chapters_huerfanos"] = [dict(r) for r in orphan_chapters]

        # 8. RAYOS_TRANSACTIONS CON BOOK_ID INEXISTENTE
        cursor.execute("""
            SELECT rt.id, rt.user_id, rt.amount, rt.type, rt.description, rt.book_id, rt.created_at
            FROM rayos_transactions rt
            LEFT JOIN books b ON rt.book_id = b.id
            WHERE rt.book_id IS NOT NULL AND b.id IS NULL
        """)
        orphan_rayos = cursor.fetchall()
        reporte["rayos_transactions_huerfanas"] = [dict(r) for r in orphan_rayos]

        # RESUMEN
        reporte["resumen"] = {
            "total_libros": len(libros_sin_pdf) + len([r for r in cursor.execute("SELECT 1 FROM books WHERE pdf_path IS NOT NULL") or []]),
            "libros_sin_pdf": len(libros_sin_pdf),
            "page_count_inconsistente": len(inconsistentes),
            "pares_paginas_duplicadas": len(dup_pages),
            "paginas_vacias_cortas": len(short_pages),
            "grupos_duplicados_por_hash": len(reporte["libros_duplicados_por_hash"]),
            "book_pages_huerfanas": sum(r["cnt"] for r in orphan_pages),
            "chapters_huerfanos": sum(r["cnt"] for r in orphan_chapters),
            "rayos_transactions_huerfanas": len(orphan_rayos),
        }

        # Output
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
            print(f"Reporte guardado en: {args.output}")

        # Print summary
        print("\n=== DIAGNÓSTICO DE INTEGRIDAD ===")
        print(f"Libros sin PDF: {reporte['resumen']['libros_sin_pdf']}")
        print(f"Page count inconsistente: {reporte['resumen']['page_count_inconsistente']}")
        print(f"Pares páginas duplicadas consecutivas: {reporte['resumen']['pares_paginas_duplicadas']}")
        print(f"Páginas vacías/cortas (<50 chars): {reporte['resumen']['paginas_vacias_cortas']}")
        print(f"Grupos duplicados por hash PDF: {reporte['resumen']['grupos_duplicados_por_hash']}")
        print(f"Book_pages huérfanas: {reporte['resumen']['book_pages_huerfanas']}")
        print(f"Chapters huérfanos: {reporte['resumen']['chapters_huerfanos']}")
        print(f"Rayos_transactions huérfanas: {reporte['resumen']['rayos_transactions_huerfanas']}")

        if reporte["libros_duplicados_por_hash"]:
            print("\n--- DUPLICADOS POR HASH PDF ---")
            for dup in reporte["libros_duplicados_por_hash"]:
                print(f"  Hash {dup['pdf_hash']}...:")
                for l in dup["libros"]:
                    print(f"    ID {l['id']}: {l['title']} / {l['author_name']}")

        if reporte["paginas_duplicadas_consecutivas"]:
            print("\n--- PÁGINAS DUPLICADAS CONSECUTIVAS ---")
            for d in reporte["paginas_duplicadas_consecutivas"][:20]:
                print(f"  ID {d['book_id']} ({d['title']}): Page {d['page_number']} = Page {d['page_number']+1} ({d['chars']} chars)")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())