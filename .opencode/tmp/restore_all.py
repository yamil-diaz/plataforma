#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restaura schema, admin y catálogo en Hetzner desde production_books.json + volumen."""
import json
import os
import re
import sys
from datetime import datetime, timezone

import psycopg2

from storage_config import STORAGE_BOOKS, STORAGE_COVERS, STORAGE_DIR

DB_URL = os.environ["DATABASE_URL"]
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

for cand in (
    "/app/production_books.json",
    "/root/plataforma/backend/production_books.json",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_books.json"),
):
    if os.path.exists(cand):
        PROD_JSON = cand
        break
else:
    PROD_JSON = "/app/production_books.json"

ADMIN_HASH = "$2b$12$ZUXe6118U1i8m5B.QoD0bO51mly1R063q3Lq0aW/R6f1c/7B6W5mC"  # admin123
NOW = datetime.now(timezone.utc).isoformat()

print("STORAGE_DIR=", STORAGE_DIR)
print("STORAGE_BOOKS=", STORAGE_BOOKS)
print("STORAGE_COVERS=", STORAGE_COVERS)
print("PROD_JSON=", PROD_JSON, "exists=", os.path.exists(PROD_JSON))

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

# ── 1) Schema ────────────────────────────────────────────────────────────────
print("=== schema ===")
cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS cover_image_url TEXT")
cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS uploader_id INTEGER")
cur.execute(
    """
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_books_uploader') THEN
        ALTER TABLE books ADD CONSTRAINT fk_books_uploader
          FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE SET NULL;
      END IF;
    END $$;
    """
)
conn.commit()
print("schema OK")

# ── 2) Admin ─────────────────────────────────────────────────────────────────
print("=== admin ===")
cur.execute(
    """
    INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at)
    VALUES (%s, %s, %s, 'admin', 500, %s)
    ON CONFLICT (email) DO NOTHING
    RETURNING id, email, role
    """,
    ("Administrador", "admin@plataforma.com", ADMIN_HASH, NOW),
)
row = cur.fetchone()
if row:
    print("admin created", row)
else:
    cur.execute("SELECT id, email, role FROM users WHERE email=%s", ("admin@plataforma.com",))
    print("admin already exists", cur.fetchone())
conn.commit()

cur.execute("SELECT id FROM users WHERE email=%s", ("admin@plataforma.com",))
admin_id = cur.fetchone()[0]
print("admin_id=", admin_id)

# ── 3) Helpers ───────────────────────────────────────────────────────────────
def basename(p):
    return os.path.basename(p or "")


def resolve_pdf(pdf_path):
    if not pdf_path:
        return None
    bn = basename(pdf_path)
    candidates = [
        pdf_path,
        os.path.join(STORAGE_BOOKS, bn),
        os.path.join("/data/aeternum/books", bn),
        os.path.join("/var/data/aeternum/books", bn),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            # normalizar a ruta del container
            return os.path.join(STORAGE_BOOKS, bn)
    return os.path.join(STORAGE_BOOKS, bn) if bn else None


def resolve_cover(cover_url):
    if not cover_url:
        return None
    if cover_url.startswith("/static/covers/"):
        bn = cover_url.split("/static/covers/")[-1]
    else:
        bn = basename(cover_url)
    if not bn:
        return None
    local = os.path.join(STORAGE_COVERS, bn)
    if os.path.isfile(local):
        return f"/static/covers/{bn}"
    return None


def title_from_filename(fn):
    # UUID_nombre.pdf -> nombre
    name = re.sub(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_", "", fn)
    name = re.sub(r"\.pdf$", "", name, flags=re.I)
    return name.strip() or fn


# ── 4) Import production_books.json ─────────────────────────────────────────
print("=== import production_books.json ===")
with open(PROD_JSON, "r", encoding="utf-8") as f:
    books = json.load(f)
print("json books=", len(books))

inserted = 0
skipped = 0
errors = 0
for b in books:
    try:
        title = (b.get("title") or "").strip() or "Sin título"
        author = (b.get("author_name") or b.get("author") or "").strip() or "Desconocido"
        content = b.get("content") or ""
        category = (b.get("category") or "General").strip() or "General"
        price = b.get("price") or 0.0
        pdf_path = resolve_pdf(b.get("pdf_path"))
        cover = resolve_cover(b.get("cover_image_url"))
        source_hash = b.get("source_hash")
        source = b.get("source") or "import"
        page_count = b.get("page_count") or 0
        published = 1 if b.get("published", 1) else 0
        views = b.get("views") or 0
        likes = b.get("likes") or 0
        dislikes = b.get("dislikes") or 0
        avg = b.get("average_rating") or 0.0
        reviews = b.get("total_reviews") or 0
        created_at = b.get("created_at") or NOW
        paginated_at = b.get("paginated_at")

        # dedup por source_hash o por pdf basename
        pdf_bn = basename(pdf_path) if pdf_path else None
        cur.execute(
            """
            SELECT id FROM books
            WHERE (source_hash IS NOT NULL AND source_hash = %s)
               OR (pdf_path IS NOT NULL AND pdf_path = %s)
            LIMIT 1
            """,
            (source_hash, pdf_path) if source_hash else (None, pdf_path),
        )
        if source_hash is None and pdf_path is None:
            cur.execute(
                "SELECT id FROM books WHERE title=%s AND author_name=%s LIMIT 1",
                (title, author),
            )
        if cur.fetchone():
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO books (
                title, author_name, content, category, price, cover_image_url,
                pdf_path, views, likes, dislikes, average_rating, total_reviews,
                published, created_at, page_count, paginated_at,
                source, source_hash, uploader_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                title, author, content, category, float(price), cover,
                pdf_path, int(views), int(likes), int(dislikes), float(avg), int(reviews),
                int(published), created_at, int(page_count), paginated_at,
                source, source_hash, admin_id,
            ),
        )
        inserted += 1
        if inserted % 25 == 0:
            print("  inserted", inserted)
    except Exception as e:
        errors += 1
        conn.rollback()
        print("ERROR book", b.get("id"), b.get("title"), type(e).__name__, e)
        # reabrir transacción
        cur = conn.cursor()

print(f"production import: inserted={inserted} skipped={skipped} errors={errors}")
conn.commit()

# ── 5) PDFs en volumen sin fila en DB ───────────────────────────────────────
print("=== disk-only PDFs ===")
if os.path.isdir(STORAGE_BOOKS):
    files = [f for f in os.listdir(STORAGE_BOOKS) if f.lower().endswith(".pdf")]
else:
    files = []
print("pdfs on disk=", len(files))

cur.execute("SELECT pdf_path FROM books WHERE pdf_path IS NOT NULL")
known = set()
for (p,) in cur.fetchall():
    if p:
        known.add(basename(p))
        known.add(p)

disk_inserted = 0
for fn in files:
    if fn in known:
        continue
    full = os.path.join(STORAGE_BOOKS, fn)
    title = title_from_filename(fn)
    try:
        cur.execute(
            """
            INSERT INTO books (
                title, author_name, content, category, price, cover_image_url,
                pdf_path, views, likes, dislikes, average_rating, total_reviews,
                published, created_at, page_count, source, uploader_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,0,0.0,0,1,%s,0,'disk',%s)
            """,
            (title, "Desconocido", "", "General", 0.0, None, full, NOW, admin_id),
        )
        disk_inserted += 1
    except Exception as e:
        conn.rollback()
        print("ERROR disk", fn, e)
        cur = conn.cursor()

print("disk_inserted=", disk_inserted)
conn.commit()

# ── 6) Resumen ───────────────────────────────────────────────────────────────
cur.execute("SELECT count(*) FROM books")
total_books = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM users")
total_users = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM books WHERE cover_image_url IS NOT NULL")
with_cover = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM books WHERE pdf_path IS NOT NULL")
with_pdf = cur.fetchone()[0]
print("=== SUMMARY ===")
print("books=", total_books, "users=", total_users, "with_cover=", with_cover, "with_pdf=", with_pdf)

conn.commit()
cur.close()
conn.close()
print("DONE")
