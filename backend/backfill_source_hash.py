#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_source_hash.py — Backfill seguro de source_hash para libros existentes.

Calcula SHA-256 de cada PDF asociado a un libro y actualiza source_hash/source.

Modos:
  --dry-run  : Solo muestra qué haría, NO modifica la DB (default)
  --apply    : Ejecuta el backfill real con transacción segura

Uso:
  python backfill_source_hash.py --dry-run
  python backfill_source_hash.py --apply

SEGURO:
  - Idempotente: solo actualiza libros con source_hash IS NULL
  - Transacción: todo o nada (rollback si falla)
  - Detección de duplicados: aborta si dos PDFs producen el mismo hash
  - No modifica: content, page_count, pdf_path, títulos, autores, etc.
  - Solo actualiza: source_hash y source
"""

import os
import sys
import hashlib
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras


def calcular_hash(filepath):
    """SHA-256 del contenido binario de un archivo por chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_storage_books():
    """Resuelve la ruta de storage_books según el entorno."""
    storage_dir = os.environ.get("STORAGE_DIR")
    if storage_dir:
        return os.path.join(storage_dir, "books")
    # Fallback: backend/storage/books (desarrollo local)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "storage", "books")


def get_db():
    """Conecta a PostgreSQL usando DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL no está definida.")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)


def run_backfill(dry_run=True):
    """Ejecuta el backfill de source_hash."""
    storage_books = get_storage_books()
    print(f"Storage books: {storage_books}")
    print(f"Modo: {'DRY-RUN (sin modificaciones)' if dry_run else 'APPLY (transacción real)'}")
    print("=" * 60)

    conn = get_db()
    cur = conn.cursor()

    # 1. Obtener libros candidatos: pdf_path IS NOT NULL AND source_hash IS NULL
    cur.execute("""
        SELECT id, title, author_name, pdf_path, source, source_hash
        FROM books
        WHERE pdf_path IS NOT NULL AND source_hash IS NULL
        ORDER BY id
    """)
    candidates = cur.fetchall()
    print(f"Libros candidatos: {len(candidates)}")

    if not candidates:
        print("No hay libros para actualizar. Ya están todos con source_hash.")
        conn.close()
        return

    # 2. Calcular hashes en memoria
    hash_to_ids = {}  # hash -> [book_id, ...]
    updates = []  # (book_id, hash, source)
    not_found = []
    errors = []

    for book in candidates:
        book_id = book["id"]
        pdf_path = book["pdf_path"]

        # Resolver ruta del PDF
        filename = os.path.basename(pdf_path)
        full_path = os.path.join(storage_books, filename)

        # Intentar también la ruta absoluta original
        if not os.path.isfile(full_path) and os.path.isabs(pdf_path):
            full_path = pdf_path

        if not os.path.isfile(full_path):
            not_found.append((book_id, filename, pdf_path))
            continue

        try:
            sha256 = calcular_hash(full_path)
            hash_to_ids.setdefault(sha256, []).append(book_id)
            updates.append((book_id, sha256, "import"))
        except Exception as e:
            errors.append((book_id, str(e)))

    # 3. Reporte
    print(f"PDF encontrados: {len(updates)}")
    print(f"PDF faltantes: {len(not_found)}")
    print(f"Errores de hash: {len(errors)}")
    print(f"Hashes únicos calculados: {len(hash_to_ids)}")

    # 4. Detectar duplicados ANTES de cualquier UPDATE
    duplicates = {h: ids for h, ids in hash_to_ids.items() if len(ids) > 1}
    if duplicates:
        print("\n" + "=" * 60)
        print("DUPLICADOS CRÍTICOS DETECTADOS — PROCESO DETENIDO")
        print("=" * 60)
        for h, ids in duplicates.items():
            print(f"  Hash {h[:16]}... → Libros IDs: {ids}")
        print(f"\nTotal hashes duplicados: {len(duplicates)}")
        print("NO se ejecutará ningún UPDATE.")
        print("Resuelve los duplicados manualmente antes de re-ejecutar.")
        conn.close()
        sys.exit(1)

    # 5. Mostrar archivos faltantes
    if not_found:
        print("\nArchivos faltantes:")
        for book_id, filename, original_path in not_found:
            print(f"  ID {book_id}: {filename}")
            print(f"    Path original: {original_path}")

    # 6. Mostrar errores
    if errors:
        print("\nErrores:")
        for book_id, err in errors:
            print(f"  ID {book_id}: {err}")

    # 7. Mostrar plan de actualización
    print(f"\nLibros que serían actualizados: {len(updates)}")
    if updates:
        print("Muestra (primeros 5):")
        for book_id, sha256, source in updates[:5]:
            print(f"  ID {book_id}: hash={sha256[:16]}... source={source}")
        if len(updates) > 5:
            print(f"  ... y {len(updates) - 5} más")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY-RUN completado. No se modificó nada.")
        print("Ejecuta con --apply para aplicar los cambios.")
        conn.close()
        return

    # 8. APPLY: ejecutar UPDATEs dentro de una transacción
    print("\n" + "=" * 60)
    print("APPLY: ejecutando actualizaciones...")

    try:
        start = time.time()
        updated = 0

        for book_id, sha256, source in updates:
            cur.execute(
                "UPDATE books SET source_hash = %s, source = %s WHERE id = %s AND source_hash IS NULL",
                (sha256, source, book_id),
            )
            if cur.rowcount > 0:
                updated += 1

        elapsed = time.time() - start
        conn.commit()

        print(f"Actualizados: {updated}/{len(updates)} ({elapsed:.1f}s)")

        # 9. Verificación post-commit
        cur.execute("SELECT COUNT(*) as cnt FROM books WHERE source_hash IS NOT NULL")
        with_hash = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM books WHERE source_hash IS NULL")
        without_hash = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM books")
        total = cur.fetchone()["cnt"]

        print(f"\nVerificación post-commit:")
        print(f"  Total libros: {total}")
        print(f"  Con source_hash: {with_hash}")
        print(f"  Sin source_hash: {without_hash}")

        # 10. Verificar duplicados post-commit
        cur.execute("""
            SELECT source_hash, COUNT(*) as cnt
            FROM books
            WHERE source_hash IS NOT NULL
            GROUP BY source_hash
            HAVING COUNT(*) > 1
        """)
        post_dupes = cur.fetchall()
        if post_dupes:
            print(f"\nALERTA: {len(post_dupes)} hashes duplicados encontrados post-commit!")
            for row in post_dupes:
                print(f"  Hash {row['source_hash'][:16]}... → {row['cnt']} veces")
        else:
            print("  Sin duplicados de hash: OK")

        print("\nBackfill completado exitosamente.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: Rollback ejecutado. {e}")
        sys.exit(1)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill seguro de source_hash para libros existentes",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Solo mostrar qué haría (default)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Ejecutar el backfill real",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    run_backfill(dry_run=dry_run)


if __name__ == "__main__":
    main()
