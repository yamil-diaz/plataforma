#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_piloto.py — Descarga 10 obras de dominio público desde Project Gutenberg
y genera PDFs con capa de texto extraíble para probar el importador masivo.
"""
import os
import sys
import hashlib
import urllib.request
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PILOTO_DIR = os.path.dirname(os.path.abspath(__file__))

# 10 obras de dominio público con variedad deliberada:
# - Cortas y largas
# - Con y sin capítulos claros
# - Diferentes autores
# - Diferentes idiomas (español, inglés, francés)
LIBROS = [
    {
        "gutenberg_id": 1342,
        "filename": "pride_and_prejudice.pdf",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "lang": "en",
    },
    {
        "gutenberg_id": 84,
        "filename": "frankenstein.pdf",
        "title": "Frankenstein; or, The Modern Prometheus",
        "author": "Mary Shelley",
        "lang": "en",
    },
    {
        "gutenberg_id": 132,
        "filename": "art_of_war.pdf",
        "title": "The Art of War",
        "author": "Sun Tzu",
        "lang": "en",
    },
    {
        "gutenberg_id": 46,
        "filename": "a_christmas_carol.pdf",
        "title": "A Christmas Carol",
        "author": "Charles Dickens",
        "lang": "en",
    },
    {
        "gutenberg_id": 219,
        "filename": "heart_of_darkness.pdf",
        "title": "Heart of Darkness",
        "author": "Joseph Conrad",
        "lang": "en",
    },
    {
        "gutenberg_id": 11,
        "filename": "alice_in_wonderland.pdf",
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "lang": "en",
    },
    {
        "gutenberg_id": 5200,
        "filename": "metamorphosis.pdf",
        "title": "The Metamorphosis",
        "author": "Franz Kafka",
        "lang": "en",
    },
    {
        "gutenberg_id": 1661,
        "filename": "sherlock_holmes.pdf",
        "title": "The Adventures of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "lang": "en",
    },
    {
        "gutenberg_id": 2701,
        "filename": "moby_dick.pdf",
        "title": "Moby Dick; or, The Whale",
        "author": "Herman Melville",
        "lang": "en",
    },
    {
        "gutenberg_id": 345,
        "filename": "dracula.pdf",
        "title": "Dracula",
        "author": "Bram Stoker",
        "lang": "en",
    },
]

HEADERS = {
    "User-Agent": "AeternumPiloto/1.0 (proyecto educativo; contacto: admin@aeternumlibrary.com)",
    "Accept": "text/plain, text/html, */*",
}


def download_gutenberg_text(book_id):
    """Descarga texto plano desde Project Gutenberg."""
    url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        pass

    url2 = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    try:
        req = urllib.request.Request(url2, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        pass

    url3 = f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"
    try:
        req = urllib.request.Request(url3, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"No se pudo descargar Gutenberg {book_id}: {e}")


def trim_gutenberg(text):
    """Elimina cabecera y pie de Gutenberg."""
    markers_start = ["*** START OF", "*** START THE", "The Project Gutenberg", "Produced by"]
    markers_end = ["*** END OF", "*** END THE", "End of the Project Gutenberg", "End of Project Gutenberg"]

    lines = text.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        for marker in markers_start:
            if marker.lower() in line.lower():
                start_idx = i + 1
                break
        if start_idx > 0:
            break

    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        for marker in markers_end:
            if marker.lower() in lines[i].lower():
                end_idx = i
                break
        if end_idx < len(lines):
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def text_to_pdf(text, filepath, title, author):
    """Genera un PDF con capa de texto extraíble usando reportlab.
    Optimizado: usa Paragraph simple con build por lotes para textos grandes."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    body_style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceBefore=3,
        spaceAfter=3,
    )
    title_style = ParagraphStyle(
        "Title2",
        fontName="Helvetica-Bold",
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(author, ParagraphStyle(
        "Author", fontName="Helvetica", fontSize=12, alignment=TA_CENTER, spaceAfter=30,
    )))

    import re
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


def main():
    results = []
    for i, book in enumerate(LIBROS, 1):
        gid = book["gutenberg_id"]
        fname = book["filename"]
        outpath = os.path.join(PILOTO_DIR, fname)

        print(f"[{i}/10] {book['title']} (Gutenberg #{gid})...")

        try:
            raw = download_gutenberg_text(gid)
            text = trim_gutenberg(raw)
            if len(text) < 500:
                raise RuntimeError(f"Texto demasiado corto ({len(text)} chars)")

            text_to_pdf(text, outpath, book["title"], book["author"])

            fsize = os.path.getsize(outpath)
            sha = sha256_file(outpath)

            from pypdf import PdfReader
            reader = PdfReader(outpath)
            pages = len(reader.pages)

            results.append({
                "filename": fname,
                "title": book["title"],
                "author": book["author"],
                "gutenberg_id": gid,
                "size_bytes": fsize,
                "size_mb": round(fsize / 1024 / 1024, 2),
                "pages": pages,
                "sha256": sha,
                "chars_text": len(text),
                "status": "OK",
                "error": None,
            })
            print(f"  OK: {pages} páginas, {fsize/1024:.0f} KB")

        except Exception as e:
            results.append({
                "filename": fname,
                "title": book["title"],
                "author": book["author"],
                "gutenberg_id": gid,
                "size_bytes": 0,
                "size_mb": 0,
                "pages": 0,
                "sha256": "",
                "chars_text": 0,
                "status": "ERROR",
                "error": str(e),
            })
            print(f"  ERROR: {e}")

        time.sleep(1)

    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(f"\n{'='*60}")
    print(f"RESUMEN: {ok_count}/10 descargados correctamente")
    print(f"{'='*60}")

    import json
    report_path = os.path.join(PILOTO_DIR, "piloto_info.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Información guardada en: {report_path}")

    return 0 if ok_count == 10 else 1


if __name__ == "__main__":
    sys.exit(main())
