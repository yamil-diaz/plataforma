# -*- coding: utf-8 -*-
"""
admin_catalog_tool.py — LIMPIEZA ADMINISTRATIVA DEL CATÁLOGO (PREPARADA).

NO EJECUTAR EN PRODUCCIÓN TODAVÍA: esta fase prohíbe cualquier eliminación.
La herramienta queda preparada para la fase de limpieza aprobada, con
protecciones explícitas contra borrados accidentales o masivos:

  - Dry-run por defecto: `preview` muestra exactamente qué se eliminaría.
  - `delete` requiere --confirm con el texto exacto "BORRAR <ids>".
  - Límite máximo de libros por ejecución (MAX_LIBROS_POR_EJECUCION).
  - Rechaza selecciones que cubran >= 90% del catálogo (anti borrado total).
  - Borrado transaccional en orden de dependencias (book_pages, chapters,
    reading_*, book_interactions, reviews, rayos_transactions, books) y,
    tras el commit, eliminación de los archivos PDF/portada del disco.

Uso (solo lectura):
  python admin_catalog_tool.py list
  python admin_catalog_tool.py diagnose --ids 133,134,135
  python admin_catalog_tool.py preview --ids 133,134,135

Ejecución real (SOLO con aprobación explícita de la fase de limpieza):
  python admin_catalog_tool.py delete --ids 133,134,135 --confirm "BORRAR 133,134,135"
"""
import os
import sys
import argparse
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or os.path.join(BASE_DIR, "storage"))
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")

MAX_LIBROS_POR_EJECUCION = 50
UMBRAL_PROTECCION_MASIVA = 0.9  # >= 90% del catálogo -> operación rechazada

TABLAS_DEPENDIENTES = [
    "book_pages",
    "chapters",
    "reading_daily_pages",
    "reading_progress",
    "reading_sessions",
    "book_interactions",
    "reviews",
    "rayos_transactions",
]


def _conectar():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def _ids_desde_arg(lista):
    ids = []
    for parte in lista.split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            ids.append(int(parte))
        except ValueError:
            raise SystemExit(f"ID inválido: {parte!r}")
    return ids


def _total_libros(cursor):
    cursor.execute("SELECT count(*) AS total FROM books")
    return cursor.fetchone()["total"]


def cmd_list(cursor):
    cursor.execute(
        "SELECT id, title, author_name, published, page_count FROM books ORDER BY id"
    )
    for r in cursor.fetchall():
        print(f"{r['id']:>4} | publicado={r['published']} | páginas={r['page_count']} | {r['title']} — {r['author_name']}")


def cmd_diagnose(cursor, ids, conn_ro=False):
    for libro_id in ids:
        cursor.execute(
            """
            SELECT b.id, b.title, b.author_name, b.published, b.page_count, b.content,
                   b.pdf_path, b.cover_image_url,
                   (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) AS n_pages,
                   (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) AS n_chapters
            FROM books b WHERE b.id = %s
            """,
            (libro_id,),
        )
        book = cursor.fetchone()
        if not book:
            print(f"{libro_id}: NO EXISTE")
            continue
        validacion = lectura.validar_contenido_libro(book["content"] or "", None, fuente="diagnostico")
        pdf = book["pdf_path"] or ""
        ruta = pdf if os.path.isabs(pdf) and os.path.isfile(pdf) else (
            os.path.join(STORAGE_BOOKS, os.path.basename(pdf)) if pdf else None
        )
        existe = bool(ruta and os.path.isfile(ruta))
        print(
            f"{book['id']} | {book['title']} — {book['author_name']}\n"
            f"   publicado={book['published']} page_count={book['page_count']} "
            f"n_pages={book['n_pages']} n_chapters={book['n_chapters']} "
            f"chars={len(book['content'] or '')}\n"
            f"   pdf_path={pdf or '-'} pdf_existe={existe}\n"
            f"   validación: {'VÁLIDO' if validacion['valid'] else 'INVÁLIDO: ' + '; '.join(validacion['errors'])}"
        )


def cmd_preview(cursor, ids):
    total = _total_libros(cursor)
    for libro_id in ids:
        cursor.execute(
            "SELECT id, title, author_name, pdf_path, cover_image_url FROM books WHERE id = %s",
            (libro_id,),
        )
        book = cursor.fetchone()
        if not book:
            print(f"{libro_id}: NO EXISTE")
            continue
        detalle = []
        for tabla in TABLAS_DEPENDIENTES:
            cursor.execute(f"SELECT count(*) AS n FROM {tabla} WHERE book_id = %s", (libro_id,))
            n = cursor.fetchone()["n"]
            if n:
                detalle.append(f"{tabla}: {n}")
        archivos = []
        pdf = book["pdf_path"] or ""
        ruta_pdf = pdf if os.path.isabs(pdf) and os.path.isfile(pdf) else (
            os.path.join(STORAGE_BOOKS, os.path.basename(pdf)) if pdf else None
        )
        if ruta_pdf and os.path.isfile(ruta_pdf):
            archivos.append(ruta_pdf)
        cover = book["cover_image_url"] or ""
        if cover.startswith("/static/covers/"):
            ruta_cover = os.path.join(STORAGE_COVERS, os.path.basename(cover))
            if os.path.isfile(ruta_cover):
                archivos.append(ruta_cover)
        print(
            f"{book['id']} | {book['title']} — {book['author_name']}\n"
            f"   se eliminará: registro books + {detalle or 'sin dependencias'}\n"
            f"   archivos en disco: {archivos or 'ninguno'}"
        )
    print(f"Total catálogo: {total} libros.")


def cmd_delete(conn, ids, confirm):
    cursor = conn.cursor()
    total = _total_libros(cursor)
    if len(ids) > MAX_LIBROS_POR_EJECUCION:
        raise SystemExit(
            f"RECHAZADO: {len(ids)} libros supera el límite de {MAX_LIBROS_POR_EJECUCION} por ejecución."
        )
    if total and len(ids) / total >= UMBRAL_PROTECCION_MASIVA:
        raise SystemExit(
            f"RECHAZADO: la selección cubre {len(ids)}/{total} del catálogo "
            f"(>= {UMBRAL_PROTECCION_MASIVA:.0%}): operación bloqueada para evitar un borrado masivo."
        )
    esperado = "BORRAR " + ",".join(str(i) for i in ids)
    if confirm != esperado:
        raise SystemExit(
            f"RECHAZADO: confirmación incorrecta. Usa exactamente: --confirm \"{esperado}\""
        )

    archivos = []
    try:
        for libro_id in ids:
            cursor.execute(
                "SELECT pdf_path, cover_image_url FROM books WHERE id = %s", (libro_id,)
            )
            book = cursor.fetchone()
            if not book:
                print(f"{libro_id}: NO EXISTE (se omite)")
                continue
            for tabla in TABLAS_DEPENDIENTES:
                cursor.execute(f"DELETE FROM {tabla} WHERE book_id = %s", (libro_id,))
            cursor.execute("DELETE FROM books WHERE id = %s", (libro_id,))
            pdf = book["pdf_path"] or ""
            ruta_pdf = pdf if os.path.isabs(pdf) and os.path.isfile(pdf) else (
                os.path.join(STORAGE_BOOKS, os.path.basename(pdf)) if pdf else None
            )
            if ruta_pdf:
                archivos.append(ruta_pdf)
            cover = book["cover_image_url"] or ""
            if cover.startswith("/static/covers/"):
                ruta_cover = os.path.join(STORAGE_COVERS, os.path.basename(cover))
                if os.path.isfile(ruta_cover):
                    archivos.append(ruta_cover)
            print(f"  - libro {libro_id} eliminado")
        conn.commit()
        for ruta in archivos:
            try:
                os.remove(ruta)
                print(f"  - archivo eliminado: {ruta}")
            except OSError as e:
                print(f"  ! no se pudo eliminar {ruta}: {e}")
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"ERROR: operación revertida. {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Limpieza admin del catálogo (PREPARADA; NO ejecutar aún en producción)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("list", help="Listar todos los libros (solo lectura)")
    p_diag = sub.add_parser("diagnose", help="Estado de validación por libro (solo lectura)")
    p_diag.add_argument("--ids", required=True, help="IDs separados por coma")
    p_prev = sub.add_parser("preview", help="Mostrar qué se eliminaría (dry-run, solo lectura)")
    p_prev.add_argument("--ids", required=True, help="IDs separados por coma")
    p_del = sub.add_parser("delete", help="Eliminar libros (protegido; requiere --confirm)")
    p_del.add_argument("--ids", required=True, help="IDs separados por coma")
    p_del.add_argument("--confirm", required=True, help='Texto exacto "BORRAR <ids>"')

    args = parser.parse_args()
    ids = _ids_desde_arg(args.ids) if hasattr(args, "ids") else []

    conn = _conectar()
    try:
        if args.comando == "list":
            cmd_list(conn.cursor())
        elif args.comando == "diagnose":
            cmd_diagnose(conn.cursor(), ids)
        elif args.comando == "preview":
            cmd_preview(conn.cursor(), ids)
        elif args.comando == "delete":
            print("ADVERTENCIA: operación destructiva.")
            cmd_delete(conn, ids, args.confirm)
    finally:
        conn.close()


if __name__ == "__main__":
    main()