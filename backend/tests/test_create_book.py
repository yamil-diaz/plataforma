"""Integración: POST /api/books con PDF con/sin capa de texto.

Verifica que un PDF sin capa de texto NO genere páginas vacías: usa el
placeholder y una única página placeholder (equivalente al flujo ZIP).
"""
import io

from pypdf import PdfWriter


def _pdf_bytes_con_texto(texto):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, texto)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _pdf_bytes_sin_texto(num_pages=3):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def _subir_pdf(client, pdf_bytes, filename):
    return client.post(
        "/api/books",
        data={
            "title": "Libro de prueba",
            "author_name": "Autor de prueba",
            "category": "Ficción",
            "price": 0.0,
        },
        files={"pdf_file": (filename, pdf_bytes, "application/pdf")},
    )


def test_create_book_con_pdf_con_texto_conserva_texto_y_paginas(fake_db, as_uploader):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto("Hola mundo de prueba"), "con_texto.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert "Hola mundo de prueba" in book["content"]
    assert book["content"] != "Contenido de texto no disponible."
    assert book["page_count"] == 1
    paginas_guardadas = [p for p in fake_db.state["book_pages"] if p[0] == book_id]
    assert len(paginas_guardadas) == 1
    assert paginas_guardadas[0][2].strip()


def test_create_book_con_pdf_sin_texto_genera_placeholder_y_una_pagina(fake_db, as_uploader):
    resp = _subir_pdf(as_uploader, _pdf_bytes_sin_texto(3), "sin_texto.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["content"] == "Contenido de texto no disponible."
    assert book["page_count"] == 1
    paginas_guardadas = [p for p in fake_db.state["book_pages"] if p[0] == book_id]
    assert len(paginas_guardadas) == 1
    assert paginas_guardadas[0][2] == "Contenido de texto no disponible."
    for p in paginas_guardadas:
        assert p[2].strip(), "no debe haber páginas vacías"


def test_create_book_sin_pdf_genera_placeholder_y_una_pagina(fake_db, as_uploader):
    resp = as_uploader.post(
        "/api/books",
        data={
            "title": "Libro sin pdf",
            "author_name": "Autor",
            "category": "Ficción",
            "price": 0.0,
        },
    )
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["content"] == "Contenido de texto no disponible."
    assert book["page_count"] == 1
    paginas_guardadas = [p for p in fake_db.state["book_pages"] if p[0] == book_id]
    assert len(paginas_guardadas) == 1
    assert paginas_guardadas[0][2] == "Contenido de texto no disponible."


def test_create_book_pdf_sin_texto_de_admin_queda_publicado_con_placeholder(fake_db, as_admin):
    resp = _subir_pdf(as_admin, _pdf_bytes_sin_texto(2), "admin_sin_texto.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["published"] == 1
    assert book["content"] == "Contenido de texto no disponible."
    assert book["page_count"] == 1


def test_create_book_pdf_con_texto_mantiene_page_count_real(fake_db, as_uploader):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto("Una sola página"), "una_pagina.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["page_count"] == 1
    assert book["published"] == 0