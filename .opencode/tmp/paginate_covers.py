#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paginar todos los libros sin book_pages + asignar portadas faltantes."""
import os
import re
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

import lectura
from storage_config import STORAGE_BOOKS, STORAGE_COVERS

DB_URL = os.environ["DATABASE_URL"]
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

# ── 1) Paginar libros sin book_pages ────────────────────────────────────────
cur.execute(
    """
    SELECT b.id, b.title, b.content, b.pdf_path
    FROM books b
    WHERE NOT EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id = b.id)
    ORDER BY b.id
    """
)
todo = cur.fetchall()
print("books_to_paginate", len(todo))

def resolver_pdf(pdf_path):
    if not pdf_path:
        return None
    bn = os.path.basename(pdf_path)
    for c in (pdf_path, os.path.join(STORAGE_BOOKS, bn)):
        if c and os.path.isfile(c):
            return c
    return None

ok = fail = 0
for b in todo:
    bid = b["id"]
    try:
        pdf = resolver_pdf(b["pdf_path"])
        if pdf:
            procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf, fuente="pdf")
        else:
            procesado = lectura.procesar_contenido_para_publicacion(content=b["content"] or "", fuente="content")
        val = procesado.get("validacion") or {}
        if not val.get("valid", False):
            print("SKIP_INVALID", bid, b["title"][:40], val.get("errors"))
            fail += 1
            continue
        paginas = procesado["paginas"]
        capitulos = procesado.get("capitulos") or []
        if not paginas:
            print("SKIP_EMPTY", bid)
            fail += 1
            continue
        cap_ids = {}
        cur.execute("DELETE FROM book_pages WHERE book_id=%s", (bid,))
        cur.execute("DELETE FROM chapters WHERE book_id=%s", (bid,))
        for cap in capitulos:
            cur.execute(
                "INSERT INTO chapters (book_id, title, start_page) VALUES (%s,%s,%s) RETURNING id",
                (bid, cap["title"], cap["page"]),
            )
            cap_ids[cap["page"]] = cur.fetchone()["id"]
        filas = [(bid, i, txt, cap_ids.get(i)) for i, txt in enumerate(paginas, start=1)]
        cur.executemany(
            "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s,%s,%s,%s)",
            filas,
        )
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "UPDATE books SET page_count=%s, paginated_at=%s WHERE id=%s",
            (len(paginas), now, bid),
        )
        conn.commit()
        ok += 1
        if ok % 20 == 0:
            print("paginated", ok)
    except Exception as e:
        conn.rollback()
        fail += 1
        print("ERR", bid, type(e).__name__, str(e)[:120])

print("paginate_done ok=", ok, "fail=", fail)

# ── 2) Portadas faltantes ───────────────────────────────────────────────────
covers_on_disk = [f for f in os.listdir(STORAGE_COVERS) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
print("covers_on_disk", len(covers_on_disk))

# index covers by uuid prefix
cover_by_uuid = {}
for f in covers_on_disk:
    m = re.match(r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", f, re.I)
    if m:
        cover_by_uuid[m.group(1).lower()] = f

# covers already used
cur.execute("SELECT cover_image_url FROM books WHERE cover_image_url IS NOT NULL AND cover_image_url <> ''")
used = set()
for r in cur.fetchall():
    used.add(os.path.basename(r["cover_image_url"] or ""))

# generic placeholders by category
PLACEHOLDERS = {
    "Ficción": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
    "Clásicos": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
    "Ciencia Ficción": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400",
    "Terror": "https://images.unsplash.com/photo-1509248961895-40b907571b87?w=400",
    "Poesía": "https://images.unsplash.com/photo-1474932430478-367dbb6832c1?w=400",
    "Historia": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=400",
    "Filosofía": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400",
    "Autoayuda": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=400",
    "Romance": "https://images.unsplash.com/photo-1474552226712-ac0f0961a954?w=400",
    "Aventura": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400",
    "Ciencia": "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400",
    "Infantil": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=400",
}
DEFAULT_COVER = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"

cur.execute(
    """
    SELECT id, title, author_name, category, pdf_path, cover_image_url
    FROM books
    WHERE cover_image_url IS NULL OR cover_image_url = ''
    ORDER BY id
    """
)
need_cover = cur.fetchall()
print("need_cover", len(need_cover))

free_covers = [f for f in covers_on_disk if f not in used]
print("free_covers", len(free_covers))
free_i = 0
cover_ok = cover_fallback = 0

for b in need_cover:
    bid = b["id"]
    assigned = None
    # 1) match por uuid del pdf
    pdf = b["pdf_path"] or ""
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", pdf, re.I)
    if m and m.group(1).lower() in cover_by_uuid:
        assigned = "/static/covers/" + cover_by_uuid[m.group(1).lower()]
    # 2) cover libre del volumen
    if not assigned and free_i < len(free_covers):
        assigned = "/static/covers/" + free_covers[free_i]
        free_i += 1
    # 3) placeholder de categoría
    if not assigned:
        assigned = PLACEHOLDERS.get(b["category"] or "", DEFAULT_COVER)
        cover_fallback += 1
    else:
        cover_ok += 1
    cur.execute("UPDATE books SET cover_image_url=%s WHERE id=%s", (assigned, bid))

conn.commit()

cur.execute("SELECT count(*) AS n FROM book_pages")
print("book_pages_total", cur.fetchone()["n"])
cur.execute("SELECT count(*) AS n FROM books WHERE cover_image_url IS NULL OR cover_image_url=''")
print("books_without_cover", cur.fetchone()["n"])
cur.execute("SELECT count(*) AS n FROM books b WHERE EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id)")
print("books_with_pages", cur.fetchone()["n"])

cur.close()
conn.close()
print("DONE")
