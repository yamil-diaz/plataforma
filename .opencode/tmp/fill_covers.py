#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completa portadas faltantes: UUID del PDF + OpenLibrary + fallback local."""
import os
import re
import json
import urllib.request
import urllib.parse
import hashlib
from storage_config import STORAGE_BOOKS, STORAGE_COVERS

import psycopg2
import psycopg2.extras

DB_URL = os.environ["DATABASE_URL"]
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute(
    """
    SELECT id, title, author_name, pdf_path, cover_image_url
    FROM books
    WHERE published = 1
      AND (
        cover_image_url IS NULL
        OR cover_image_url = ''
        OR cover_image_url LIKE 'https://images.unsplash.com%'
      )
    ORDER BY id
    """
)
todo = cur.fetchall()
print("books_need_cover", len(todo))

covers_on_disk = [f for f in os.listdir(STORAGE_COVERS) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
print("covers_on_disk", len(covers_on_disk))

cover_by_uuid = {}
for f in covers_on_disk:
    m = re.match(r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", f, re.I)
    if m:
        cover_by_uuid[m.group(1).lower()] = f

used = set()
cur.execute("SELECT cover_image_url FROM books WHERE cover_image_url LIKE '/static/covers/%'")
for r in cur.fetchall():
    used.add(os.path.basename(r["cover_image_url"] or ""))
free = [f for f in covers_on_disk if f not in used]
print("free_covers", len(free))
free_i = 0

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


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "AeternumLibrary/1.0 (covers)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def try_openlibrary(title, author):
    q = urllib.parse.quote(f"{title} {author}".strip())
    try:
        data = http_get(f"https://openlibrary.org/search.json?q={q}&limit=3&fields=title,author_name,cover_i,isbn")
        docs = json.loads(data).get("docs") or []
    except Exception as e:
        print("  OL search err", e)
        return None
    for d in docs:
        cover_i = d.get("cover_i")
        if cover_i:
            url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
            try:
                blob = http_get(url)
                if blob and len(blob) > 2000:
                    return blob
            except Exception:
                pass
        isbns = d.get("isbn") or []
        for isbn in isbns[:3]:
            url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            try:
                blob = http_get(url)
                if blob and len(blob) > 2000:
                    return blob
            except Exception:
                pass
    return None


def try_google_books(title, author):
    q = urllib.parse.quote(f"{title} {author}".strip())
    try:
        data = http_get(f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults=3")
        items = json.loads(data).get("items") or []
    except Exception as e:
        print("  GB err", e)
        return None
    for it in items:
        vi = it.get("volumeInfo") or {}
        img = ((vi.get("imageLinks") or {}).get("thumbnail")
               or (vi.get("imageLinks") or {}).get("smallThumbnail")
               or "")
        if img:
            img = img.replace("http://", "https://").replace("&edge=curl", "")
            try:
                blob = http_get(img)
                if blob and len(blob) > 2000:
                    return blob
            except Exception:
                pass
    return None


def save_cover(book_id, blob, title):
    ext = "jpg"
    if blob[:8].startswith(b"\x89PNG"):
        ext = "png"
    name = f"{uuid_hex()}_{re.sub(r'[^a-zA-Z0-9]+','_', title)[:40]}.{ext}"
    path = os.path.join(STORAGE_COVERS, name)
    with open(path, "wb") as f:
        f.write(blob)
    return f"/static/covers/{name}", path


def uuid_hex():
    import uuid
    return uuid.uuid4().hex


ok_uuid = ol_n = gb_n = local_n = ph_n = fail_n = 0

for b in todo:
    bid = b["id"]
    title = (b["title"] or "").strip()
    author = (b["author_name"] or "").strip()
    pdf = b["pdf_path"] or ""
    assigned = None

    # 1) UUID match
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", pdf, re.I)
    if m and m.group(1).lower() in cover_by_uuid:
        assigned = "/static/covers/" + cover_by_uuid[m.group(1).lower()]
        ok_uuid += 1

    # 2) OpenLibrary
    if not assigned:
        blob = try_openlibrary(title, author)
        if blob:
            assigned, _ = save_cover(bid, blob, title)
            ol_n += 1
            print("  OL", bid, title[:40], "->", assigned)

    # 3) Google Books
    if not assigned:
        blob = try_google_books(title, author)
        if blob:
            assigned, _ = save_cover(bid, blob, title)
            gb_n += 1
            print("  GB", bid, title[:40], "->", assigned)

    # 4) cover libre del volumen
    if not assigned and free_i < len(free):
        assigned = "/static/covers/" + free[free_i]
        free_i += 1
        local_n += 1

    # 5) placeholder categoría
    if not assigned:
        assigned = PLACEHOLDERS.get("General", DEFAULT_COVER)
        ph_n += 1

    if not assigned:
        fail_n += 1
        continue

    cur.execute("UPDATE books SET cover_image_url=%s WHERE id=%s", (assigned, bid))

conn.commit()

cur.execute(
    """
    SELECT count(*) AS n FROM books
    WHERE published=1 AND (cover_image_url IS NULL OR cover_image_url=''
       OR cover_image_url LIKE 'https://images.unsplash.com%')
    """
)
print("still_missing_or_placeholder", cur.fetchone()["n"])
cur.execute("SELECT count(*) AS n FROM books WHERE cover_image_url LIKE '/static/covers/%'")
print("local_covers_assigned", cur.fetchone()["n"])
print("stats uuid=%s ol=%s gb=%s local_free=%s placeholder=%s" % (ok_uuid, ol_n, gb_n, local_n, ph_n))

cur.close()
conn.close()
print("DONE")
