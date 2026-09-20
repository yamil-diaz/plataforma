# -*- coding: utf-8 -*-
"""
FASE 5 — IMPORTACION PILOTO (1 libro)
Ejecutar en Render Shell: python test_import_piloto.py

Reutiliza EXACTAMENTE las mismas funciones del pipeline real.
NO modifica autenticacion. NO crea bypass. NO expone DATABASE_URL.
"""
import os
import sys
import uuid
import shutil
from datetime import datetime, timezone

# Backend path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lectura
from storage_config import STORAGE_BOOKS, STORAGE_COVERS, STORAGE_DIR
from database import get_db

TITLE = "El Hobbit"
AUTHOR = "J.R.R. Tolkien"
CATEGORY = "Ficcion"
PRICE = 0.0


def crear_pdf_prueba():
    """Crea un PDF de prueba de 5 paginas con texto extraible."""
    from fpdf import FPDF
    pdf_path = os.path.join(STORAGE_DIR, "_test_piloto_temp.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    texts = [
        ("El Hobbit", "J.R.R. Tolkien",
         "En un agujero en el suelo vivia un hobbit. No un agujero sucio, hedoroso, con el fondo baboso y lleno de gusanos de la tierra, ni tampoco un agujero seco, arenoso, sin nada en el que sentarse ni en el que beber: era un agujero-hogar, y eso significa comodidad."),
        ("Capitulo 1: Un festin inesperado", None,
         "En un agujero en el suelo vivia un hobbit. Tenia una puerta redonda, como una ventanilla, con un cristal de color verde en el centro, una cacerola de cobre llena de azulejos, y un canon de hierro con llave. El hogar era un agujero muy comodo, con suelos de ladrillo y alfombras."),
        ("Capitulo 2: Consejos inoportunos", None,
         "Gandalf el Mago se acerco a la puerta del agujero de Bilbo y la golpeo con su baston. La puerta se abrio de par en par, y Bilbo aparecio con una cara de asombro. Buenos dias -dijo Bilbo, y le parecio que era una manana muy buena para el. El sol brillaba, y la hierba estaba verde."),
        ("Capitulo 3: Una reunion corta", None,
         "Esa noche Bilbo se sento junto a la chimenea y leyo un libro de historia, pensando en las aventuras, sin saber que pronto el mismo seria parte de una. De repente, la campana de la puerta sono con fuerza. Bilbo se levanto, y al abrir, se encontro con un grupo de enanos."),
        ("Capitulo 4: Hacia la montana solitaria", None,
         "Al dia siguiente partieron hacia el este. El camino los paso por colinas verdes, bosques oscuros y rios caudalosos. Bilbo, aunque cansado, sentia una emocion que nunca antes habia experimentado. El aroma de las hierbas, el canto de los pajaros, y el viento fresco lo llenaban de vida. FIN"),
    ]

    for i, (title, subtitle, body) in enumerate(texts):
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16 if i > 0 else 24)
        pdf.cell(0, 10, title, ln=True, align='C' if i == 0 else 'L')
        if subtitle:
            pdf.set_font('Arial', '', 14)
            pdf.cell(0, 10, subtitle, ln=True, align='C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 8, body)

    pdf.output(pdf_path)
    return pdf_path


def main():
    print("=" * 60)
    print("FASE 5 - IMPORTACION PILOTO (1 libro)")
    print("=" * 60)
    print(f"STORAGE_DIR: {STORAGE_DIR}")
    print(f"STORAGE_BOOKS: {STORAGE_BOOKS}")

    # === VERIFICAR ESTADO PREVIO ===
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as n FROM books")
    books_before = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) as n FROM book_pages")
    pages_before = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) as n FROM chapters")
    chapters_before = cursor.fetchone()["n"]
    db.close()

    print(f"\nPre-import: books={books_before}, book_pages={pages_before}, chapters={chapters_before}")
    if books_before != 0 or pages_before != 0 or chapters_before != 0:
        print("ERROR: Database is not clean. Aborting.")
        return 1

    # === CREAR PDF DE PRUEBA ===
    print("\n--- Creating test PDF ---")
    pdf_path = crear_pdf_prueba()
    pdf_size = os.path.getsize(pdf_path)
    print(f"  PDF created: {pdf_path} ({pdf_size} bytes)")

    # === PIPELINE REAL ===
    print("\n--- Running pipeline ---")

    # 1. Validate PDF (misma funcion que el endpoint)
    lectura.validar_archivo_pdf(pdf_path)
    print("  [1/5] PDF validation: OK")

    # 2. Process content (misma funcion que el endpoint)
    procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf_path, fuente="pdf")
    validacion = procesado["validacion"]
    if not validacion["valid"]:
        print(f"  ERROR: Content rejected: {'; '.join(validacion['errors'])}")
        return 1

    content = procesado["content"]
    paginas = procesado["paginas"]
    capitulos = procesado["capitulos"]
    print(f"  [2/5] Content extraction: OK ({len(content)} chars, {len(paginas)} pages)")
    print(f"  [3/5] Chapters detected: {len(capitulos)}")
    for cap in capitulos:
        print(f"    - '{cap['title']}' at page {cap['page']}")

    # 3. Copy PDF to Persistent Disk (misma logica que el endpoint)
    unique_pdf_name = f"{uuid.uuid4()}_test_piloto.pdf"
    pdf_dest = os.path.join(STORAGE_BOOKS, unique_pdf_name)
    shutil.copy2(pdf_path, pdf_dest)
    print(f"  [4/5] PDF persisted: {pdf_dest}")

    # 4. Insert into books + pages + chapters (misma SQL que el endpoint)
    db = get_db()
    cursor = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"

    cursor.execute(
        """INSERT INTO books (title, author_name, content, category, price, cover_image_url,
                           pdf_path, views, likes, average_rating, total_reviews, published,
                           created_at, uploader_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, 1, %s, NULL)
        RETURNING id""",
        (TITLE, AUTHOR, content, CATEGORY, PRICE, cover_url, pdf_dest, now),
    )
    book_id = cursor.fetchone()["id"]
    print(f"  [5/5] Book inserted: ID={book_id}")

    # Save chapters
    capitulo_ids = {}
    for cap in capitulos:
        cursor.execute(
            "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
            (book_id, cap["title"], cap["page"]),
        )
        capitulo_ids[cap["page"]] = cursor.fetchone()["id"]

    # Save pages
    filas = [
        (book_id, i, texto, capitulo_ids.get(i))
        for i, texto in enumerate(paginas, start=1)
    ]
    if filas:
        cursor.executemany(
            "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
            filas,
        )

    # Update page_count
    cursor.execute(
        "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
        (len(paginas), now, book_id),
    )
    db.commit()
    print(f"\n  Pages saved: {len(paginas)}")
    print(f"  Chapters saved: {len(capitulos)}")

    # Clean up temp PDF
    try:
        os.remove(pdf_path)
    except OSError:
        pass

    # === VERIFICACION ===
    print("\n--- Verification ---")

    cursor.execute("SELECT id, title, author_name, pdf_path, page_count, published FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()
    print(f"  Book: ID={book['id']}, title='{book['title']}', author='{book['author_name']}'")
    print(f"  pdf_path: {book['pdf_path']}")
    print(f"  page_count: {book['page_count']}")
    print(f"  published: {book['published']}")

    cursor.execute("SELECT COUNT(*) as n, MIN(page_number) as min_p, MAX(page_number) as max_p FROM book_pages WHERE book_id = %s", (book_id,))
    pages = cursor.fetchone()
    print(f"  book_pages: {pages['n']} (range: {pages['min_p']}-{pages['max_p']})")

    cursor.execute("SELECT title, start_page FROM chapters WHERE book_id = %s ORDER BY start_page", (book_id,))
    chaps = cursor.fetchall()
    print(f"  chapters: {len(chaps)}")
    for ch in chaps:
        print(f"    - '{ch['title']}' at page {ch['start_page']}")

    pdf_exists = os.path.isfile(book["pdf_path"])
    pdf_actual_size = os.path.getsize(book["pdf_path"]) if pdf_exists else 0
    print(f"  PDF on disk: exists={pdf_exists}, size={pdf_actual_size}")

    cursor.execute("SELECT page_number, content FROM book_pages WHERE book_id = %s ORDER BY page_number", (book_id,))
    all_pages = cursor.fetchall()
    unique_contents = set(p["content"] for p in all_pages)
    print(f"  Content: {len(all_pages)} pages, {len(unique_contents)} unique contents")

    is_pathological = (len(unique_contents) == 1 and len(all_pages) > 1)
    has_placeholder = any(p["content"].strip() == "Contenido de texto no disponible." for p in all_pages)
    print(f"  Pathological: {is_pathological}, Placeholder: {has_placeholder}")

    cursor.execute("SELECT COUNT(*) as n FROM books")
    total_books = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) as n FROM book_pages")
    total_pages = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) as n FROM chapters")
    total_chapters = cursor.fetchone()["n"]
    db.close()

    print(f"\n  Final: books={total_books}, book_pages={total_pages}, chapters={total_chapters}")

    all_ok = (
        book["id"] == book_id
        and book["title"] == TITLE
        and book["author_name"] == AUTHOR
        and book["page_count"] == len(paginas)
        and book["published"] == 1
        and pages["n"] == len(paginas)
        and pdf_exists
        and not is_pathological
        and not has_placeholder
        and total_books == 1
    )
    print(f"\n  RESULT: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
