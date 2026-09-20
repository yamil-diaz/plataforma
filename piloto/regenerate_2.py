#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenera dracula.pdf y pride_and_prejudice.pdf sin marcadores problemáticos."""
import os, sys, hashlib, re, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

PILOTO_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/plain, text/html, */*",
}

LIBROS = [
    {"gutenberg_id": 345, "filename": "dracula.pdf", "title": "Dracula", "author": "Bram Stoker"},
    {"gutenberg_id": 1342, "filename": "pride_and_prejudice.pdf", "title": "Pride and Prejudice", "author": "Jane Austen"},
    {"gutenberg_id": 11, "filename": "alice_in_wonderland.pdf", "title": "Alice's Adventures in Wonderland", "author": "Lewis Carroll"},
    {"gutenberg_id": 2701, "filename": "moby_dick.pdf", "title": "Moby Dick; or, The Whale", "author": "Herman Melville"},
]


def download_gutenberg_text(book_id):
    for url in [
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    ]:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            continue
    raise RuntimeError(f"No se pudo descargar Gutenberg {book_id}")


def trim_gutenberg(text):
    markers_start = ["*** START OF", "*** START THE", "The Project Gutenberg", "Produced by"]
    markers_end = ["*** END OF", "*** END THE", "End of the Project Gutenberg", "End of Project Gutenberg"]
    lines = text.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        for m in markers_start:
            if m.lower() in line.lower():
                start_idx = i + 1
                break
        if start_idx > 0:
            break
    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        for m in markers_end:
            if m.lower() in lines[i].lower():
                end_idx = i
                break
        if end_idx < len(lines):
            break
    return "\n".join(lines[start_idx:end_idx]).strip()


def clean_problematic_lines(text):
    """Elimina SOLO marcadores editoriales problemáticos. NO toca contenido narrativo."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Eliminar separadores de escena: líneas que SON solo asteriscos
        # (ej. "* * * * *", "* * * * * * *") pero NO líneas con asteriscos en medio de texto
        if re.match(r'^[\*\s]+$', stripped) and '*' in stripped and len(stripped) > 5:
            continue
        # Eliminar marcadores [Illustration] y todas las variantes: [Illustration:], [Illustration: text]
        if re.match(r'^\[Illustration', stripped, re.IGNORECASE):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def text_to_pdf(text, filepath, title, author):
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm,
    )
    body_style = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=13, spaceBefore=3, spaceAfter=3)
    title_style = ParagraphStyle("Title2", fontName="Helvetica-Bold", fontSize=18, alignment=TA_CENTER, spaceAfter=20)
    author_style = ParagraphStyle("Author", fontName="Helvetica", fontSize=12, alignment=TA_CENTER, spaceAfter=30)

    story = [Paragraph(title, title_style), Paragraph(author, author_style)]
    paragraphs = re.split(r'\n\s*\n', text)
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        clean = " ".join(para.split())
        if not clean:
            continue
        safe = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if len(safe) > 4000:
            safe = safe[:4000]
        story.append(Paragraph(safe, body_style))
    doc.build(story)


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


for book in LIBROS:
    gid = book["gutenberg_id"]
    fname = book["filename"]
    outpath = os.path.join(PILOTO_DIR, fname)

    print(f"Regenerando {fname} (Gutenberg #{gid})...")
    raw = download_gutenberg_text(gid)
    text = trim_gutenberg(raw)
    cleaned = clean_problematic_lines(text)
    print(f"  Texto original: {len(text)} chars -> limpio: {len(cleaned)} chars (eliminados {len(text)-len(cleaned)} chars de marcadores)")

    text_to_pdf(cleaned, outpath, book["title"], book["author"])

    from pypdf import PdfReader
    reader = PdfReader(outpath)
    sha = sha256_file(outpath)
    size = os.path.getsize(outpath)
    print(f"  OK: {len(reader.pages)} paginas, {size/1024:.0f} KB, SHA-256: {sha[:16]}...")
    time.sleep(1)

print("\nListo.")
