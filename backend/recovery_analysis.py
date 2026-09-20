#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramienta DRY-RUN de análisis y recuperación de libros afectados.
SOLO LECTURA - No modifica la base de datos ni archivos.

Uso:
  DATABASE_URL="postgresql://..." python backend/recovery_analysis.py [--ids 133,134,135]

Clasifica cada libro en:
- RECUPERABLE: PDF existe y permite extracción de texto válido
- DUPLICADO: Mismo título/autor normalizado que otro libro
- PLACEHOLDER: content == "Contenido de texto no disponible."
- SIN_PDF: pdf_path es NULL o vacío
- PDF_SIN_TEXTO: PDF existe pero no tiene capa de texto extraíble
- VALIDO: Libro con contenido real y páginas válidas
- REQUIERE_REVISION: Caso ambiguo que necesita decisión manual
"""

import os
import sys
import hashlib
import argparse
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura

# Importar configuración centralizada de storage
from storage_config import STORAGE_BOOKS

CONTENIDO_NO_DISPONIBLE = lectura.CONTENIDO_NO_DISPONIBLE


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    import unicodedata
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    import re
    texto = re.sub(r"[^\w\s]", "", texto.lower())
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _calcular_hash_contenido(content: str, pdf_path: str = None) -> str:
    h = hashlib.sha256()
    if content and content != CONTENIDO_NO_DISPONIBLE:
        h.update(content.encode("utf-8"))
    elif pdf_path and os.path.isfile(pdf_path):
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    else:
        h.update(b"empty")
    return h.hexdigest()


def _resolver_pdf_path(pdf_path, STORAGE_BOOKS):
    if not pdf_path:
        return None
    if os.path.isabs(pdf_path) and os.path.isfile(pdf_path):
        return pdf_path
    candidata = os.path.join(STORAGE_BOOKS, os.path.basename(pdf_path))
    if os.path.isfile(candidata):
        return candidata
    return None


def analizar_libro(cursor, book_id, STORAGE_BOOKS, libros_por_titulo_autor):
    """Analiza un libro individual y retorna su clasificación y detalles."""
    cursor.execute("""
        SELECT id, title, author_name, content, pdf_path, page_count, paginated_at, created_at, uploader_id
        FROM books WHERE id = %s
    """, (book_id,))
    libro = cursor.fetchone()
    if not libro:
        return {"id": book_id, "clasificacion": "NO_EXISTE", "error": "Libro no encontrado en BD"}

    # Contar book_pages
    cursor.execute("SELECT COUNT(*) as cnt, MAX(page_number) as max_page FROM book_pages WHERE book_id = %s", (book_id,))
    bp = cursor.fetchone()
    n_book_pages = bp["cnt"] if bp else 0
    max_page = bp["max_page"] if bp else 0

    # Contar chapters
    cursor.execute("SELECT COUNT(*) as cnt FROM chapters WHERE book_id = %s", (book_id,))
    ch = cursor.fetchone()
    n_chapters = ch["cnt"] if ch else 0

    # Resolver PDF
    pdf_resuelto = _resolver_pdf_path(libro["pdf_path"], STORAGE_BOOKS)
    pdf_existe = pdf_resuelto is not None
    pdf_size = os.path.getsize(pdf_resuelto) if pdf_existe else 0

    # Extraer texto del PDF si existe
    pdf_texto_longitud = 0
    pdf_paginas_extraibles = 0
    pdf_error = None
    if pdf_existe:
        try:
            paginas = lectura.extraer_paginas(pdf_resuelto)
            pdf_paginas_extraibles = len(paginas)
            texto = "\n".join(paginas)
            pdf_texto_longitud = len(texto.strip())
        except Exception as e:
            pdf_error = str(e)

    # Verificar placeholder
    es_placeholder = libro["content"] and libro["content"].strip() == CONTENIDO_NO_DISPONIBLE
    content_length = len(libro["content"] or "")

    # Verificar duplicado por título+autor normalizado
    title_norm = _normalizar_texto(libro["title"])
    author_norm = _normalizar_texto(libro["author_name"])
    clave_dup = (title_norm, author_norm)
    grupo_duplicado = libros_por_titulo_autor.get(clave_dup, [])
    es_duplicado = len(grupo_duplicado) > 1
    duplicado_ids = [g["id"] for g in grupo_duplicado if g["id"] != book_id]

    # Determinar clasificación
    clasificacion = "REQUIERE_REVISION"
    razones = []

    if es_placeholder:
        clasificacion = "PLACEHOLDER"
        razones.append(f"content = '{CONTENIDO_NO_DISPONIBLE}'")
    elif not pdf_existe:
        if content_length >= lectura.MIN_CONTENIDO_TOTAL:
            clasificacion = "VALIDO"
            razones.append(f"Contenido textual válido ({content_length} chars), sin PDF")
        else:
            clasificacion = "SIN_PDF"
            razones.append(f"Sin PDF y content_length={content_length} < {lectura.MIN_CONTENIDO_TOTAL}")
    elif pdf_error:
        clasificacion = "PDF_CORRUPTO"
        razones.append(f"Error leyendo PDF: {pdf_error}")
    elif pdf_texto_longitud == 0:
        clasificacion = "PDF_SIN_TEXTO"
        razones.append(f"PDF existe ({pdf_size} bytes) pero extracción = 0 chars")
    elif pdf_texto_longitud < lectura.MIN_CONTENIDO_TOTAL:
        clasificacion = "PDF_TEXTO_INSUFICIENTE"
        razones.append(f"PDF texto extraído ({pdf_texto_longitud} chars) < mínimo ({lectura.MIN_CONTENIDO_TOTAL})")
    else:
        # PDF tiene texto válido
        if n_book_pages > 0 and libro["page_count"] == n_book_pages:
            clasificacion = "VALIDO"
            razones.append(f"PDF válido ({pdf_texto_longitud} chars), {n_book_pages} páginas OK")
        else:
            clasificacion = "RECUPERABLE"
            razones.append(f"PDF válido ({pdf_texto_longitud} chars, {pdf_paginas_extraibles} págs) pero paginación inconsistente (page_count={libro['page_count']}, book_pages={n_book_pages})")

    if es_duplicado:
        if clasificacion == "VALIDO":
            clasificacion = "DUPLICADO"
        else:
            clasificacion += "_DUPLICADO"
        razones.append(f"Duplicado de: {duplicado_ids}")

    # Verificar consistencia page_count vs book_pages
    page_count_ok = (libro["page_count"] or 0) == n_book_pages
    paginated_at_ok = libro["paginated_at"] is not None if n_book_pages > 0 else True

    return {
        "id": libro["id"],
        "title": libro["title"],
        "author_name": libro["author_name"],
        "created_at": libro["created_at"],
        "pdf_path": libro["pdf_path"],
        "pdf_resuelto": pdf_resuelto,
        "pdf_existe": pdf_existe,
        "pdf_size": pdf_size,
        "pdf_texto_longitud": pdf_texto_longitud,
        "pdf_paginas_extraibles": pdf_paginas_extraibles,
        "pdf_error": pdf_error,
        "content_length": content_length,
        "es_placeholder": es_placeholder,
        "n_book_pages": n_book_pages,
        "max_page": max_page,
        "n_chapters": n_chapters,
        "page_count": libro["page_count"],
        "page_count_ok": page_count_ok,
        "paginated_at": libro["paginated_at"],
        "paginated_at_ok": paginated_at_ok,
        "uploader_id": libro["uploader_id"],
        "es_duplicado": es_duplicado,
        "duplicado_ids": duplicado_ids,
        "clasificacion": clasificacion,
        "razones": razones,
    }


def main():
    parser = argparse.ArgumentParser(description="Análisis DRY-RUN de libros afectados")
    parser.add_argument("--ids", help="Lista de IDs separados por coma (ej: 133,134,135)")
    parser.add_argument("--all", action="store_true", help="Analizar todos los libros publicados")
    parser.add_argument("--output", help="Archivo JSON de salida")
    parser.add_argument("--storage", default=None, help="Directorio STORAGE_BOOKS (default: backend/storage/books)")
    args = parser.parse_args()

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: Define DATABASE_URL")
        sys.exit(1)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    storage_books = args.storage or STORAGE_BOOKS

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    try:
        # Obtener IDs a analizar
        if args.ids:
            ids = [int(x.strip()) for x in args.ids.split(",")]
        elif args.all:
            cursor.execute("SELECT id FROM books WHERE published = 1 ORDER BY id")
            ids = [row["id"] for row in cursor.fetchall()]
        else:
            # Por defecto: los IDs del problema conocido
            ids = [
                133,134,135,136,137,138,139,140,141,142,143,144,
                147,148,150,151,152,153,154,155,156,157,
                159,160,161,162,163,164,165,166,168,169,170,
                22, 91, 82, 145
            ]

        print(f"Analizando {len(ids)} libros...")
        print(f"STORAGE_BOOKS: {storage_books}")
        print()

        # Pre-cargar todos los libros para detectar duplicados título+autor
        cursor.execute("SELECT id, title, author_name FROM books WHERE id IN %s", (tuple(ids),))
        todos_libros = cursor.fetchall()
        libros_por_titulo_autor = {}
        for lb in todos_libros:
            clave = (_normalizar_texto(lb["title"]), _normalizar_texto(lb["author_name"]))
            if clave not in libros_por_titulo_autor:
                libros_por_titulo_autor[clave] = []
            libros_por_titulo_autor[clave].append({"id": lb["id"], "title": lb["title"], "author_name": lb["author_name"]})

        # Analizar cada libro
        resultados = []
        for book_id in ids:
            r = analizar_libro(cursor, book_id, storage_books, libros_por_titulo_autor)
            resultados.append(r)

        # Imprimir resumen
        from collections import Counter
        stats = Counter(r["clasificacion"] for r in resultados)
        
        print("=" * 100)
        print("RESUMEN DE CLASIFICACIONES")
        print("=" * 100)
        for clasif, count in stats.most_common():
            print(f"  {clasif:30s}: {count}")

        print()
        print("=" * 100)
        print("DETALLE POR LIBRO")
        print("=" * 100)
        
        for r in resultados:
            print(f"\nID {r['id']:3d} | {r['clasificacion']}")
            print(f"  Título: {r['title']}")
            print(f"  Autor:  {r['author_name']}")
            print(f"  Creado: {r['created_at']}")
            print(f"  PDF:    {'SÍ (' + str(r['pdf_size']) + ' bytes)' if r['pdf_existe'] else 'NO'}")
            if r['pdf_resuelto']:
                print(f"  Path:   {r['pdf_resuelto']}")
            if r['pdf_error']:
                print(f"  Error:  {r['pdf_error']}")
            print(f"  Texto PDF: {r['pdf_texto_longitud']} chars, {r['pdf_paginas_extraibles']} págs extraíbles")
            print(f"  Content: {r['content_length']} chars {'(PLACEHOLDER)' if r['es_placeholder'] else ''}")
            print(f"  Pages:   book_pages={r['n_book_pages']}, page_count={r['page_count']}, max_page={r['max_page']} {'✓' if r['page_count_ok'] else '✗'}")
            print(f"  Chapters: {r['n_chapters']}")
            print(f"  Paginated_at: {r['paginated_at'] or 'NULL'} {'✓' if r['paginated_at_ok'] else '✗'}")
            if r['es_duplicado']:
                print(f"  ⚠ DUPLICADO de IDs: {r['duplicado_ids']}")
            print(f"  Razones: {'; '.join(r['razones'])}")

        # Guardar JSON si se pidió
        if args.output:
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
            print(f"\nResultado guardado en {args.output}")

        # Recomendaciones
        print()
        print("=" * 100)
        print("RECOMENDACIONES POR CLASIFICACIÓN")
        print("=" * 100)
        
        for clasif in ["RECUPERABLE", "DUPLICADO", "PLACEHOLDER", "SIN_PDF", "PDF_SIN_TEXTO", "PDF_TEXTO_INSUFICIENTE", "PDF_CORRUPTO", "VALIDO", "REQUIERE_REVISION"]:
            items = [r for r in resultados if r["clasificacion"].startswith(clasif)]
            if not items:
                continue
            print(f"\n--- {clasif} ({len(items)} libros) ---")
            for r in items:
                if clasif == "RECUPERABLE":
                    print(f"  ID {r['id']}: Repaginar con PDF (ejecutar /repaginate o migración)")
                elif clasif == "DUPLICADO":
                    print(f"  ID {r['id']}: ELIMINAR (conservar el de created_at más antiguo o el VALIDO)")
                elif clasif == "PLACEHOLDER":
                    if r['pdf_existe'] and r['pdf_texto_longitud'] > 0:
                        print(f"  ID {r['id']}: Repaginar desde PDF (tiene texto extraíble)")
                    else:
                        print(f"  ID {r['id']}: Marcar unpublished / eliminar / recuperar PDF original")
                elif clasif in ("PDF_SIN_TEXTO", "PDF_TEXTO_INSUFICIENTE", "PDF_CORRUPTO"):
                    print(f"  ID {r['id']}: Recuperar PDF original / marcar unpublished")
                elif clasif == "SIN_PDF":
                    if r['content_length'] >= lectura.MIN_CONTENIDO_TOTAL:
                        print(f"  ID {r['id']}: Repaginar desde content (texto válido)")
                    else:
                        print(f"  ID {r['id']}: Contenido insuficiente, marcar unpublished")
                elif clasif == "VALIDO":
                    print(f"  ID {r['id']}: OK - No requiere acción")

    finally:
        conn.close()


if __name__ == "__main__":
    main()