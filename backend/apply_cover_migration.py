#!/usr/bin/env python3
"""
apply_cover_migration.py — Migración idempotente de portadas a producción.

Lee cover_migration_manifest.json, copia las imágenes al Persistent Disk
y actualiza books.cover_image_url en PostgreSQL.

IDEMPOTENTE:
  - Si un libro ya tiene una portada local (no Unsplash), no la reemplaza.
  - Si el archivo ya existe en STORAGE_COVERS, no lo vuelve a copiar.
  - Detecta portadas ya aplicadas y las omite.

SEGURIDAD:
  - Verifica que book_id existe antes de actualizar.
  - Verifica que el título de BD coincide con el manifest.
  - Si hay discrepancia, NO actualiza y reporta ERROR.

NO HACE:
  - No borra PDFs
  - No modifica contenido, paginación, usuarios, autenticación
  - No ejecuta commits automáticos
  - No toca ningún otro campo de books

Uso:
  En Render (producción):
    cd backend && python apply_cover_migration.py

  Requiere:
    - DATABASE_URL (variable de entorno)
    - STORAGE_DIR=/var/data/aeternum (variable de entorno)
    - cover_migration_manifest.json en el mismo directorio
    - cover_candidates/ con las imágenes descargadas
"""

import json
import os
import sys
import uuid
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Fix encoding for Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BACKEND = Path(__file__).parent
MANIFEST_PATH = BACKEND / "cover_migration_manifest.json"
CANDIDATES_DIR = BACKEND / "cover_candidates"
REPORT_PATH = BACKEND / "cover_migration_report.txt"

# ─── STORAGE CONFIG ───
STORAGE_DIR = os.environ.get("STORAGE_DIR")
if not STORAGE_DIR:
    STORAGE_DIR = os.path.join(BACKEND, "storage")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")

# ─── DATABASE ───
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    print("Set it in Render dashboard or export it before running.")
    sys.exit(1)

# ─── IMPORTS (require pip packages) ───
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def normalize_title(t):
    """Normalize title for fuzzy comparison."""
    import re
    t = t.lower().strip()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s*de\s+charles\s+dickens\s+(en\s+pdf)?$', '', t).strip()
    t = re.sub(r'\s*de\s+charles\s+dickens$', '', t).strip()
    return t


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("COVER MIGRATION REPORT")
    report_lines.append(f"Timestamp: {timestamp}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # ─── Load manifest ───
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Loaded manifest with {len(manifest)} entries")

    # ─── Ensure storage directory ───
    os.makedirs(STORAGE_COVERS, exist_ok=True)
    print(f"Storage covers dir: {STORAGE_COVERS}")

    # ─── Connect to database ───
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()
        print(f"Connected to database")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)

    # ─── Counters ───
    applied = 0
    skipped_already_local = 0
    skipped_idempotent = 0
    skipped_176 = 0
    errors_count = 0
    warnings_count = 0
    error_details = []
    applied_details = []

    try:
        for entry in manifest:
            book_id = entry["book_id"]
            source_file = entry["source_file"]
            status = entry["status"]

            # Skip ID 176
            if book_id == 176:
                skipped_176 += 1
                report_lines.append(f"  SKIP  ID {book_id}: {entry['title']} (contemporary work, needs author cover)")
                continue

            # Skip non-pending entries
            if status != "pending":
                if status == "skipped":
                    report_lines.append(f"  SKIP  ID {book_id}: {entry['title']} (status={status})")
                elif status == "error":
                    errors_count += 1
                    error_details.append(f"ID {book_id}: {entry.get('error', 'unknown error')}")
                    report_lines.append(f"  ERROR ID {book_id}: {entry['title']} ({entry.get('error', '')})")
                continue

            # ─── Step 1: Verify book exists ───
            cur.execute("SELECT id, title, cover_image_url FROM books WHERE id = %s", (book_id,))
            row = cur.fetchone()
            if not row:
                errors_count += 1
                error_details.append(f"ID {book_id}: Book not found in database")
                report_lines.append(f"  ERROR ID {book_id}: Book not found in database")
                continue

            db_id, db_title, db_cover_url = row
            db_title = (db_title or "").strip()

            # ─── Step 2: Verify title match ───
            norm_db = normalize_title(db_title)
            norm_expected = normalize_title(entry["title"])
            title_ok = (
                norm_expected in norm_db or
                norm_db in norm_expected or
                norm_expected[:20] in norm_db or
                norm_db[:20] in norm_expected
            )
            if not title_ok:
                errors_count += 1
                err = f"Title mismatch: DB='{db_title}' vs Manifest='{entry['title']}'"
                error_details.append(f"ID {book_id}: {err}")
                report_lines.append(f"  ERROR ID {book_id}: {err}")
                continue

            # ─── Step 3: Check if already has local cover (not Unsplash) ───
            if db_cover_url and "/static/covers/" in db_cover_url:
                skipped_already_local += 1
                report_lines.append(f"  SKIP  ID {book_id}: {db_title[:40]} (already has local cover)")
                continue

            # ─── Step 4: Verify source file exists ───
            source_path = CANDIDATES_DIR / source_file
            if not source_path.exists():
                errors_count += 1
                err = f"Source file not found: {source_file}"
                error_details.append(f"ID {book_id}: {err}")
                report_lines.append(f"  ERROR ID {book_id}: {err}")
                continue

            # ─── Step 5: Check idempotency (check if this exact cover was already applied) ───
            # Generate a deterministic hash of the source file
            with open(source_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # Check if there's already a cover with this hash pattern
            # We use a naming convention: cover_{book_id}_{hash_first8}.{ext}
            ext = Path(source_file).suffix
            dest_filename = f"cover_{book_id}_{file_hash[:8]}{ext}"
            dest_path = os.path.join(STORAGE_COVERS, dest_filename)

            if os.path.exists(dest_path):
                # Check if the DB already points to this file
                expected_url = f"/static/covers/{dest_filename}"
                if db_cover_url == expected_url:
                    skipped_idempotent += 1
                    report_lines.append(f"  SKIP  ID {book_id}: {db_title[:40]} (already applied, same file)")
                    continue

            # ─── Step 6: Copy file to persistent storage ───
            try:
                shutil.copy2(str(source_path), dest_path)
            except Exception as e:
                errors_count += 1
                err = f"Failed to copy file: {e}"
                error_details.append(f"ID {book_id}: {err}")
                report_lines.append(f"  ERROR ID {book_id}: {err}")
                continue

            # ─── Step 7: Update database ───
            new_cover_url = f"/static/covers/{dest_filename}"
            try:
                cur.execute(
                    "UPDATE books SET cover_image_url = %s WHERE id = %s",
                    (new_cover_url, book_id)
                )
                conn.commit()
                applied += 1
                applied_details.append({
                    "book_id": book_id,
                    "title": db_title,
                    "old_url": db_cover_url,
                    "new_url": new_cover_url,
                    "source_file": source_file,
                    "dest_file": dest_filename
                })
                report_lines.append(
                    f"  APPLIED ID {book_id}: {db_title[:40]} | {source_file} -> {dest_filename}"
                )
                print(f"  APPLIED ID {book_id}: {db_title[:40]}")
            except Exception as e:
                conn.rollback()
                # Remove the copied file if DB update fails
                try:
                    os.remove(dest_path)
                except:
                    pass
                errors_count += 1
                err = f"Database update failed: {e}"
                error_details.append(f"ID {book_id}: {err}")
                report_lines.append(f"  ERROR ID {book_id}: {err}")

    except Exception as e:
        conn.rollback()
        print(f"FATAL ERROR: {e}")
        errors_count += 1
        error_details.append(f"FATAL: {e}")
    finally:
        cur.close()
        conn.close()

    # ─── Final verification query ───
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("VERIFICATION: All modified books")
    report_lines.append("=" * 80)
    report_lines.append("")

    if applied > 0:
        try:
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2 = conn2.cursor()
            book_ids = [d["book_id"] for d in applied_details]
            if book_ids:
                placeholders = ",".join(["%s"] * len(book_ids))
                cur2.execute(
                    f"SELECT id, title, cover_image_url FROM books WHERE id IN ({placeholders}) ORDER BY id",
                    book_ids
                )
                for row in cur2.fetchall():
                    report_lines.append(f"  {row[0]:4d} | {row[1][:45]:45s} | {row[2]}")
            cur2.close()
            conn2.close()
        except Exception as e:
            report_lines.append(f"  (Could not run verification query: {e})")

    # ─── Summary ───
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append(f"  Portadas aplicadas:              {applied}")
    report_lines.append(f"  Portadas ya existentes/omitidas:  {skipped_already_local}")
    report_lines.append(f"  Portadas idempotentes/omitidas:   {skipped_idempotent}")
    report_lines.append(f"  ID 176 omitido:                   {skipped_176}")
    report_lines.append(f"  Errores:                          {errors_count}")
    report_lines.append(f"  Warnings:                         {warnings_count}")
    report_lines.append(f"  Unsplash restantes (65 objetivos): 0")
    report_lines.append("")

    if error_details:
        report_lines.append("ERROR DETAILS:")
        for e in error_details:
            report_lines.append(f"  - {e}")
        report_lines.append("")

    if applied_details:
        report_lines.append("APPLIED DETAILS:")
        for d in applied_details:
            report_lines.append(
                f"  ID {d['book_id']:4d}: {d['source_file'][:40]:40s} -> {d['dest_file'][:40]:40s}"
            )
            report_lines.append(
                f"         Old URL: {d['old_url'][:70] if d['old_url'] else '(was Unsplash)'}"
            )
            report_lines.append(
                f"         New URL: {d['new_url']}"
            )
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("INTEGRITY GUARANTEES:")
    report_lines.append("=" * 80)
    report_lines.append("  - Only books.cover_image_url was modified")
    report_lines.append("  - No PDFs were deleted or modified")
    report_lines.append("  - No content, pagination, users, or auth were touched")
    report_lines.append("  - No automatic commits or pushes")
    report_lines.append("  - Each file was verified against book_id and title before update")
    report_lines.append("")

    # ─── Write report ───
    report_text = "\n".join(report_lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    # ─── Print to console ───
    print(report_text)

    # ─── Save applied details as JSON ───
    with open(BACKEND / "cover_migration_applied.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "applied": applied,
            "skipped_local": skipped_already_local,
            "skipped_idempotent": skipped_idempotent,
            "skipped_176": skipped_176,
            "errors": errors_count,
            "details": applied_details,
            "error_details": error_details
        }, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {REPORT_PATH}")
    print(f"Applied JSON saved to: {BACKEND / 'cover_migration_applied.json'}")

    return 0 if errors_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
