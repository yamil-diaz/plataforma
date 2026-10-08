#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completa author_name en libros con Desconocido/vacío: PDF metadata + OpenLibrary."""
import os
import re
import json
import urllib.request
import urllib.parse
from storage_config import STORAGE_BOOKS

import psycopg2
import psycopg2.extras

DB_URL = os.environ["DATABASE_URL"]
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute(
    """
    SELECT id, title, author_name, pdf_path
    FROM books
    WHERE published = 1
      AND (
        author_name IS NULL
        OR TRIM(author_name) = ''
        OR LOWER(TRIM(author_name)) IN ('desconocido', 'desconocida', 'unknown', 'autor', 's/d', 'n/a')
      )
    ORDER BY id
    """
)
todo = cur.fetchall()
print("books_need_author", len(todo))


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "AeternumLibrary/1.0 (authors)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolver_pdf(pdf_path):
    if not pdf_path:
        return None
    bn = os.path.basename(pdf_path)
    for c in (pdf_path, os.path.join(STORAGE_BOOKS, bn)):
        if c and os.path.isfile(c):
            return c
    return None


def author_from_pdf(pdf_path):
    try:
        from pypdf import PdfReader
        r = PdfReader(pdf_path)
        meta = r.metadata or {}
        for key in ("/Author", "Author"):
            a = meta.get(key)
            if a:
                a = str(a).strip()
                if a and a.lower() not in ("unknown", "desconocido", "none", "n/a"):
                    return a[:120]
        # a veces está en la primera página
        if len(r.pages):
            t = r.pages[0].extract_text() or ""
            m = re.search(r"(?i)autor\s*:\s*([^\n]{3,80})", t)
            if m:
                return m.group(1).strip()[:120]
    except Exception:
        pass
    return None


def author_from_openlibrary(title):
    q = urllib.parse.quote(title)
    try:
        data = http_get(f"https://openlibrary.org/search.json?q={q}&limit=5&fields=title,author_name")
        docs = json.loads(data).get("docs") or []
    except Exception:
        return None
    tnorm = re.sub(r"[^a-z0-9áéíóúñü ]", "", (title or "").lower()).strip()
    for d in docs:
        names = d.get("author_name") or []
        dt = re.sub(r"[^a-z0-9áéíóúñü ]", "", (d.get("title") or "").lower()).strip()
        if names and (dt == tnorm or tnorm in dt or dt in tnorm):
            return names[0][:120]
    for d in docs:
        names = d.get("author_name") or []
        if names:
            return names[0][:120]
    return None


ok_pdf = ok_ol = fail = 0
for b in todo:
    bid = b["id"]
    title = (b["title"] or "").strip()
    pdf = resolver_pdf(b["pdf_path"])
    author = None
    if pdf:
        author = author_from_pdf(pdf)
        if author:
            ok_pdf += 1
    if not author:
        author = author_from_openlibrary(title)
        if author:
            ok_ol += 1
    if not author:
        # último recurso: dejar Desconocido pero sin doble espacio raros
        fail += 1
        print("  FAIL", bid, title[:50])
        continue
    cur.execute("UPDATE books SET author_name=%s WHERE id=%s", (author, bid))
    print("  OK", bid, title[:40], "->", author)

conn.commit()

cur.execute(
    """
    SELECT count(*) AS n FROM books
    WHERE published=1 AND (
      author_name IS NULL OR TRIM(author_name)=''
      OR LOWER(TRIM(author_name)) IN ('desconocido','desconocida','unknown')
    )
    """
)
print("still_unknown", cur.fetchone()["n"])
cur.execute("SELECT count(*) AS n FROM books WHERE published=1 AND author_name NOT ILIKE '%desconocid%'")
print("with_real_author", cur.fetchone()["n"])
print("stats pdf=%s ol=%s fail=%s" % (ok_pdf, ok_ol, fail))

# sample
cur.execute(
    """
    SELECT id, title, author_name FROM books
    WHERE id IN (158,159,161,164,167,169,171)
    ORDER BY id
    """
)
for r in cur.fetchall():
    print("sample", r["id"], r["title"][:35], "|", r["author_name"])

cur.close()
conn.close()
print("DONE")
