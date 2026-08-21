"""Integración: POST /api/books con PDF con/sin capa de texto.

PASO 3: un PDF cuya extracción falla (placeholder) se RECHAZA con 422: no se
publica, no quedan páginas ni archivos huérfanos. Un PDF con texto real y
suficiente se publica normalmente.
"""
import io

import pytest

import server
from pypdf import PdfWriter
from support import _contenido_variado

TEXTO_VALIDO = _contenido_variado(2200)


@pytest.fixture(autouse=True)
def _storage_temporal(tmp_path, monkeypatch):
    """Redirige el almacenamiento a un directorio temporal por test:
    ninguna prueba toca backend/storage real."""
    monkeypatch.setattr(server, "STORAGE_BOOKS", str(tmp_path))
    monkeypatch.setattr(server, "STORAGE_COVERS", str(tmp_path))
    return tmp_path


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


def test_create_book_con_pdf_con_texto_conserva_texto_y_paginas(fake_db, as_uploader, tmp_path):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(TEXTO_VALIDO), "con_texto.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert "transcurre la acción" in book["content"]
    assert book["content"] != "Contenido de texto no disponible."
    assert book["page_count"] == 1
    paginas_guardadas = [p for p in fake_db.state["book_pages"] if p[0] == book_id]
    assert len(paginas_guardadas) == 1
    assert paginas_guardadas[0][2].strip()


def test_create_book_con_pdf_sin_texto_rechazado_422(fake_db, as_uploader, _storage_temporal):
    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
    resp = _subir_pdf(as_uploader, _pdf_bytes_sin_texto(3), "sin_texto.pdf")
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "no pudo procesarse" in body["detail"]
    assert len(fake_db.state["books"]) == libros_antes
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert list(_storage_temporal.iterdir()) == []


def test_create_book_sin_pdf_devuelve_422(fake_db, as_uploader):
    resp = as_uploader.post(
        "/api/books",
        data={
            "title": "Libro sin pdf",
            "author_name": "Autor",
            "category": "Ficción",
            "price": 0.0,
        },
    )
    assert resp.status_code == 422, resp.text
    assert "PDF" in resp.json()["detail"]
    assert fake_db.state["books"] == {k: v for k, v in fake_db.state["books"].items() if v["title"] != "Libro sin pdf"}


def test_create_book_pdf_sin_texto_de_admin_tambien_rechazado_422(fake_db, as_admin, _storage_temporal):
    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
    resp = _subir_pdf(as_admin, _pdf_bytes_sin_texto(2), "admin_sin_texto.pdf")
    assert resp.status_code == 422, resp.text
    assert len(fake_db.state["books"]) == libros_antes
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert list(_storage_temporal.iterdir()) == []


def test_create_book_pdf_con_texto_mantiene_page_count_real(fake_db, as_uploader):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(TEXTO_VALIDO), "una_pagina.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["page_count"] == 1
    assert book["published"] == 0