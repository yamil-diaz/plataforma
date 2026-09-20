# -*- coding: utf-8 -*-
"""
Comprehensive READ-ONLY Database Audit & PDF Orphan Analysis
for AeternumLibrary. Does NOT modify anything.
"""
import os
import sys
import json
import hashlib
import collections

# ── DB connection ────────────────────────────────────────────────────────────
DB_URL = "postgresql://postgres:yamilpro002@localhost:5432/plataforma_dev"

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

# ── Storage path ─────────────────────────────────────────────────────────────
STORAGE_BOOKS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "backend", "storage", "books"
)

results = {}

# ══════════════════════════════════════════════════════════════════════════════
# PART 1: DATABASE AUDIT
# ══════════════════════════════════════════════════════════════════════════════

# 1. Total books
cur.execute("SELECT COUNT(*) AS cnt FROM books")
total_books = cur.fetchone()["cnt"]
results["total_books"] = total_books

# 2. All books detail
cur.execute("""
    SELECT id, title, author_name, published, page_count,
           pdf_path, source, source_hash, created_at
    FROM books ORDER BY id
""")
all_books = [dict(r) for r in cur.fetchall()]
results["all_books"] = all_books

# 3. Total book_pages
cur.execute("SELECT COUNT(*) AS cnt FROM book_pages")
total_book_pages = cur.fetchone()["cnt"]
results["total_book_pages"] = total_book_pages

# 4. Total chapters
cur.execute("SELECT COUNT(*) AS cnt FROM chapters")
total_chapters = cur.fetchone()["cnt"]
results["total_chapters"] = total_chapters

# 5. Books with pdf_path NOT NULL
cur.execute("SELECT id, title, pdf_path FROM books WHERE pdf_path IS NOT NULL")
books_with_pdf = [dict(r) for r in cur.fetchall()]
results["books_with_pdf_not_null"] = {
    "count": len(books_with_pdf),
    "list": [r["pdf_path"] for r in books_with_pdf],
}

# 6. Books with pdf_path IS NULL
cur.execute("SELECT id, title FROM books WHERE pdf_path IS NULL")
books_no_pdf = [dict(r) for r in cur.fetchall()]
results["books_with_pdf_null"] = {
    "count": len(books_no_pdf),
    "titles": [r["title"] for r in books_no_pdf],
}

# 7. Books with page_count = 0 or NULL
cur.execute("""
    SELECT id, title, page_count FROM books
    WHERE page_count = 0 OR page_count IS NULL
""")
zero_pages = [dict(r) for r in cur.fetchall()]
results["books_page_count_zero_or_null"] = {
    "count": len(zero_pages),
    "list": [{"id": r["id"], "title": r["title"], "page_count": r["page_count"]} for r in zero_pages],
}

# 8. Books where page_count != actual book_pages count
cur.execute("""
    SELECT b.id, b.title, b.page_count AS declared,
           COUNT(bp.id) AS actual
    FROM books b
    LEFT JOIN book_pages bp ON bp.book_id = b.id
    GROUP BY b.id, b.title, b.page_count
    HAVING b.page_count != COUNT(bp.id)
       AND b.page_count IS NOT NULL
""")
mismatched_pages = [dict(r) for r in cur.fetchall()]
results["books_page_count_mismatch"] = {
    "count": len(mismatched_pages),
    "list": mismatched_pages,
}

# 9. Duplicate source_hash
cur.execute("""
    SELECT source_hash, COUNT(*) AS cnt,
           ARRAY_AGG(id ORDER BY id) AS book_ids,
           ARRAY_AGG(title ORDER BY id) AS titles
    FROM books
    WHERE source_hash IS NOT NULL
    GROUP BY source_hash
    HAVING COUNT(*) > 1
""")
dups = [dict(r) for r in cur.fetchall()]
results["duplicate_source_hash"] = {
    "count": len(dups),
    "list": dups,
}

# 10. Books with placeholder content
cur.execute("""
    SELECT id, title, content
    FROM books
    WHERE content = 'Contenido de texto no disponible.'
""")
placeholders = [dict(r) for r in cur.fetchall()]
results["books_placeholder_content"] = {
    "count": len(placeholders),
    "list": [{"id": r["id"], "title": r["title"]} for r in placeholders],
}

# 11-14. Books by source
for src in ("import", "seed", "upload", "gutenberg"):
    cur.execute("SELECT COUNT(*) AS cnt FROM books WHERE source = %s", (src,))
    cnt = cur.fetchone()["cnt"]
    results[f"books_source_{src}"] = cnt

# 15. Users count
cur.execute("SELECT COUNT(*) AS cnt FROM users")
results["total_users"] = cur.fetchone()["cnt"]

# 16. Books where book_pages has identical content (duplicate pages within same book)
cur.execute("""
    SELECT book_id, content, COUNT(*) AS dup_count
    FROM book_pages
    GROUP BY book_id, content
    HAVING COUNT(*) > 1
""")
dup_content_pages = [dict(r) for r in cur.fetchall()]
results["books_with_identical_page_content"] = {
    "count": len(dup_content_pages),
    "list": dup_content_pages,
}

# 17. Per-book comparison: book_pages rows vs page_count field
cur.execute("""
    SELECT b.id, b.title, b.page_count AS declared,
           COUNT(bp.id) AS actual_book_pages
    FROM books b
    LEFT JOIN book_pages bp ON bp.book_id = b.id
    GROUP BY b.id, b.title, b.page_count
    ORDER BY b.id
""")
page_comparison = [dict(r) for r in cur.fetchall()]
results["page_count_comparison"] = {
    "total_books": len(page_comparison),
    "books_with_pages": [r for r in page_comparison if r["actual_book_pages"] > 0],
    "books_without_pages": [r for r in page_comparison if r["actual_book_pages"] == 0],
}

# ══════════════════════════════════════════════════════════════════════════════
# PART 2: PDF ORPHAN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

# Get all pdf_path values from DB (normalise: use just filename)
cur.execute("SELECT id, title, pdf_path FROM books WHERE pdf_path IS NOT NULL")
db_pdf_rows = [dict(r) for r in cur.fetchall()]

# Build set of pdf_path values for matching
db_pdf_paths = set()
for row in db_pdf_rows:
    p = row["pdf_path"]
    if p:
        # Store full path and just filename
        db_pdf_paths.add(p.strip())
        db_pdf_paths.add(os.path.basename(p.strip()))

# Also build a mapping: filename -> book info
filename_to_book = {}
for row in db_pdf_rows:
    p = row["pdf_path"]
    if p:
        fname = os.path.basename(p.strip())
        filename_to_book.setdefault(fname, []).append({
            "book_id": row["id"],
            "title": row["title"],
            "pdf_path": p,
        })

# List all files on disk
pdf_files_on_disk = []
if os.path.isdir(STORAGE_BOOKS):
    for fname in os.listdir(STORAGE_BOOKS):
        fpath = os.path.join(STORAGE_BOOKS, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            pdf_files_on_disk.append({"filename": fname, "path": fpath, "size": size})

# Categorize
associated = []
orphan = []
total_disk_size = 0
associated_size = 0
orphan_size = 0

for f in pdf_files_on_disk:
    total_disk_size += f["size"]
    if f["filename"] in filename_to_book or f["filename"] in db_pdf_paths:
        associated.append(f)
        associated_size += f["size"]
    else:
        orphan.append(f)
        orphan_size += f["size"]

# Check: books whose pdf_path points to a missing file on disk
missing_files = []
for row in db_pdf_rows:
    p = row["pdf_path"]
    if p:
        # Check various path forms
        fname = os.path.basename(p.strip())
        disk_path = os.path.join(STORAGE_BOOKS, fname)
        if not os.path.exists(disk_path):
            missing_files.append({
                "book_id": row["id"],
                "title": row["title"],
                "pdf_path": p,
            })

results["pdf_disk_analysis"] = {
    "storage_path": STORAGE_BOOKS,
    "total_files_on_disk": len(pdf_files_on_disk),
    "total_disk_size_bytes": total_disk_size,
    "total_disk_size_mb": round(total_disk_size / (1024 * 1024), 2),
    "associated_count": len(associated),
    "associated_size_bytes": associated_size,
    "associated_size_mb": round(associated_size / (1024 * 1024), 2),
    "orphan_count": len(orphan),
    "orphan_size_bytes": orphan_size,
    "orphan_size_mb": round(orphan_size / (1024 * 1024), 2),
    "orphan_files": [{"filename": o["filename"], "size": o["size"]} for o in orphan],
    "missing_from_disk_count": len(missing_files),
    "missing_from_disk": missing_files,
}

conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
# Print structured results
print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
