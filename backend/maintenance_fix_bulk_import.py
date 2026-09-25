# -*- coding: utf-8 -*-
"""
maintenance_fix_bulk_import.py — Fix post-importación masiva defectuosa.

Ejecutar en Render:
  cd /opt/render/project/src/backend
  python maintenance_fix_bulk_import.py --dry-run
  python maintenance_fix_bulk_import.py --execute

Problemas que corrige:
1. Libros duplicados (mismo source_hash)
2. Libros con contenido corrupto (placeholder, vacío, patológico)
3. Archivos PDF huérfanos en storage (sin libro asociado)
4. Lockouts stale en login_attempts (causados por crash del servidor)
"""
import os
import sys
import argparse
from collections import Counter
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage_config import STORAGE_DIR, STORAGE_BOOKS

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no definida.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

CONTENIDO_PLACEHOLDER = "Contenido no disponible"


def _conectar(readonly=False):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    if readonly:
        conn.set_session(readonly=True, autocommit=False)
    return conn


def limpiar_duplicados_hash(cursor, dry_run=True):
    """Encuentra y elimina libros con el mismo source_hash (duplicados reales)."""
    cursor.execute("""
        SELECT source_hash, COUNT(*) as cnt, array_agg(id ORDER BY id) as ids
        FROM books
        WHERE source_hash IS NOT NULL
        GROUP BY source_hash
        HAVING COUNT(*) > 1
    """)
    dupes = cursor.fetchall()
    removed = 0
    for dup in dupes:
        ids = dup["ids"]
        keep_id = min(ids)  # Mantener el primero (más antiguo)
        remove_ids = [i for i in ids if i != keep_id]
        print(f"  [DUP-HASH] Hash {dup['source_hash'][:16]}... duplicado en IDs: {ids}")
        print(f"    Manteniendo ID={keep_id}, eliminando {remove_ids}")
        if not dry_run:
            for rid in remove_ids:
                cursor.execute("DELETE FROM book_pages WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM chapters WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM book_interactions WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM reviews WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM books WHERE id = %s", (rid,))
                removed += 1
    return removed


def limpiar_duplicados_titulo_autor(cursor, dry_run=True):
    """Encuentra libros duplicados por título+autor normalizado."""
    cursor.execute("""
        SELECT
            lower(regexp_replace(regexp_replace(regexp_replace(title, '[^a-zA-Z0-9\\s]', '', 'g'), '\\s+', ' ', 'g'), '^\\s+|\\s+$', '', 'g')) AS title_norm,
            lower(regexp_replace(regexp_replace(regexp_replace(author_name, '[^a-zA-Z0-9\\s]', '', 'g'), '\\s+', ' ', 'g'), '^\\s+|\\s+$', '', 'g')) AS author_norm,
            COUNT(*) as cnt,
            array_agg(id ORDER BY id) as ids
        FROM books
        GROUP BY title_norm, author_norm
        HAVING COUNT(*) > 1
    """)
    dupes = cursor.fetchall()
    removed = 0
    for dup in dupes:
        ids = dup["ids"]
        keep_id = min(ids)
        remove_ids = [i for i in ids if i != keep_id]
        print(f"  [DUP-TITLE] '{dup['title_norm'][:40]}' / '{dup['author_norm'][:30]}' duplicado en IDs: {ids}")
        print(f"    Manteniendo ID={keep_id}, eliminando {remove_ids}")
        if not dry_run:
            for rid in remove_ids:
                cursor.execute("DELETE FROM book_pages WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM chapters WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM book_interactions WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM reviews WHERE book_id = %s", (rid,))
                cursor.execute("DELETE FROM books WHERE id = %s", (rid,))
                removed += 1
    return removed


def limpiar_libros_corruptos(cursor, dry_run=True):
    """Elimina libros con contenido placeholder, vacío o patológico."""
    cursor.execute("""
        SELECT id, title, author_name, content, page_count
        FROM books
        WHERE content IS NULL
           OR length(content) < 50
           OR content LIKE '%Contenido no disponible%'
    """)
    corruptos = cursor.fetchall()
    removed = 0
    for book in corruptos:
        content = book["content"] or ""
        if content.strip() == CONTENIDO_PLACEHOLDER:
            reason = "placeholder"
        elif len(content.strip()) < 50:
            reason = f"contenido vacío ({len(content)} chars)"
        else:
            reason = "contenido no disponible"
        print(f"  [CORRUPTO] ID={book['id']}: '{book['title'][:50]}' — {reason}")
        if not dry_run:
            cursor.execute("DELETE FROM book_pages WHERE book_id = %s", (book["id"],))
            cursor.execute("DELETE FROM chapters WHERE book_id = %s", (book["id"],))
            cursor.execute("DELETE FROM book_interactions WHERE book_id = %s", (book["id"],))
            cursor.execute("DELETE FROM reviews WHERE book_id = %s", (book["id"],))
            cursor.execute("DELETE FROM books WHERE id = %s", (book["id"],))
            removed += 1
    return removed


def limpiar_archivos_orphan(dry_run=True):
    """Elimina PDFs en storage que no están referenciados por ningún libro."""
    db = _conectar(readonly=True)
    cursor = db.cursor()
    cursor.execute("SELECT pdf_path FROM books WHERE pdf_path IS NOT NULL")
    db_paths = set()
    for row in cursor.fetchall():
        if row["pdf_path"]:
            basename = os.path.basename(row["pdf_path"])
            db_paths.add(basename)
    db.close()

    orphan_files = []
    if os.path.isdir(STORAGE_BOOKS):
        for fname in os.listdir(STORAGE_BOOKS):
            if fname.endswith(".pdf") and fname not in db_paths:
                orphan_files.append(fname)

    print(f"  [ORPHAN] {len(orphan_files)} archivos PDF sin libro asociado en storage")
    for f in orphan_files[:20]:
        print(f"    - {f}")
    if len(orphan_files) > 20:
        print(f"    ... y {len(orphan_files) - 20} más")

    if not dry_run:
        removed = 0
        for f in orphan_files:
            fpath = os.path.join(STORAGE_BOOKS, f)
            try:
                os.remove(fpath)
                removed += 1
            except OSError:
                pass
        print(f"  [ORPHAN] Eliminados {removed} archivos huérfanos")
        return removed
    return len(orphan_files)


def limpiar_lockouts_stale(dry_run=True):
    """Elimina lockouts expirados en login_attempts que bloquean el login."""
    db = _conectar(readonly=False)
    cursor = db.cursor()
    cursor.execute("""
        DELETE FROM login_attempts
        WHERE lockout_until IS NOT NULL
          AND lockout_until::timestamp < NOW() - INTERVAL '1 hour'
        RETURNING ip_address, attempts, lockout_until
    """)
    stale = cursor.fetchall()
    if not dry_run:
        db.commit()
    else:
        db.rollback()
    db.close()

    print(f"  [LOCKOUT] {len(stale)} lockouts stale encontrados")
    for row in stale:
        print(f"    - {row['ip_address']}: {row['attempts']} intentos, lockout hasta {row['lockout_until']}")
    return len(stale)


def main():
    parser = argparse.ArgumentParser(description="Fix post-importación masiva defectuosa")
    parser.add_argument("--dry-run", action="store_true", help="Solo analizar, no modificar")
    parser.add_argument("--execute", action="store_true", help="Ejecutar limpieza real")
    parser.add_argument("--skip-duplicates", action="store_true", help="No limpiar duplicados")
    parser.add_argument("--skip-corrupt", action="store_true", help="No limpiar corruptos")
    parser.add_argument("--skip-orphan", action="store_true", help="No limpiar archivos huérfanos")
    parser.add_argument("--skip-lockouts", action="store_true", help="No limpiar lockouts")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("Especifica --dry-run o --execute")

    dry_run = not args.execute

    mode = "DRY-RUN" if dry_run else "EJECUTANDO"
    print(f"{'='*70}")
    print(f"MAINTENANCE: Fix post-importación masiva — Modo: {mode}")
    print(f"{'='*70}")

    total_removed = 0

    if not args.skip_duplicates:
        print(f"\n--- 1. Duplicados por source_hash ---")
        db = _conectar(readonly=dry_run)
        cursor = db.cursor()
        removed = limpiar_duplicados_hash(cursor, dry_run)
        if not dry_run:
            db.commit()
        db.close()
        total_removed += removed

        print(f"\n--- 2. Duplicados por título+autor ---")
        db = _conectar(readonly=dry_run)
        cursor = db.cursor()
        removed = limpiar_duplicados_titulo_autor(cursor, dry_run)
        if not dry_run:
            db.commit()
        db.close()
        total_removed += removed

    if not args.skip_corrupt:
        print(f"\n--- 3. Libros corruptos (placeholder/vacío) ---")
        db = _conectar(readonly=dry_run)
        cursor = db.cursor()
        removed = limpiar_libros_corruptos(cursor, dry_run)
        if not dry_run:
            db.commit()
        db.close()
        total_removed += removed

    if not args.skip_orphan:
        print(f"\n--- 4. Archivos PDF huérfanos ---")
        limpiar_archivos_orphan(dry_run)

    if not args.skip_lockouts:
        print(f"\n--- 5. Lockouts stale en login_attempts ---")
        limpiar_lockouts_stale(dry_run)

    print(f"\n{'='*70}")
    if dry_run:
        print(f"DRY-RUN COMPLETADO. No se modificó nada.")
        print(f"Para ejecutar: python maintenance_fix_bulk_import.py --execute")
    else:
        print(f"LIMPIEZA COMPLETADA. {total_removed} libros eliminados.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
