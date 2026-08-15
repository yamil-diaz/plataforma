"""Pruebas unitarias de extracción de contenido de PDF (lectura.py).

Genera PDFs reales en memoria: con capa de texto (reportlab) y sin capa de
texto (pypdf blank pages). No toca ninguna base de datos.
"""
import io
import os

from pypdf import PdfWriter

import lectura

PAGE_CHARS = lectura.PAGE_CHARS


def _pdf_con_texto(pages_texts, path):
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(path)
    for page_index, texto in enumerate(pages_texts, start=1):
        if texto:
            c.drawString(72, 720, texto)
        c.showPage()
    c.save()
    return path


def _pdf_sin_texto(num_pages, path):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_pdf_con_texto_conserva_paginas_y_contenido(tmp_path):
    path = _pdf_con_texto(["Hola mundo de prueba", "Segunda página de prueba"], str(tmp_path / "con_texto.pdf"))
    content, paginas, capitulos = lectura.extraer_contenido_libro(path)
    assert "Hola mundo de prueba" in content
    assert "Segunda página de prueba" in content
    assert len(paginas) == 2
    assert paginas[0].strip()
    assert paginas[1].strip()
    assert capitulos == []


def test_pdf_sin_texto_usa_placeholder_y_una_pagina(tmp_path):
    path = _pdf_sin_texto(3, str(tmp_path / "sin_texto.pdf"))
    content, paginas, capitulos = lectura.extraer_contenido_libro(path)
    assert content == lectura.CONTENIDO_NO_DISPONIBLE
    assert len(paginas) == 1
    assert paginas[0] == lectura.CONTENIDO_NO_DISPONIBLE
    assert capitulos == []


def test_pdf_solo_espacios_tratado_como_sin_texto(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    path = str(tmp_path / "espacios.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    content, paginas, _ = lectura.extraer_contenido_libro(path)
    assert content == lectura.CONTENIDO_NO_DISPONIBLE
    assert len(paginas) == 1


def test_pdf_inexistente_no_rompe_y_devuelve_placeholder(tmp_path):
    path = str(tmp_path / "no_existe.pdf")
    content, paginas, capitulos = lectura.extraer_contenido_libro(path)
    assert content == lectura.CONTENIDO_NO_DISPONIBLE
    assert len(paginas) == 1
    assert capitulos == []


def test_pdf_con_texto_largo_se_pagina_sin_perder_contenido(tmp_path):
    parrafo = " ".join(["palabra" * 50] * 200)
    path = _pdf_con_texto([parrafo], str(tmp_path / "largo.pdf"))
    content, paginas, _ = lectura.extraer_contenido_libro(path)
    assert "palabra" in content
    assert len(paginas) >= 1
    for pagina in paginas:
        assert pagina.strip()


def test_paginar_desde_contenido_placeholder_genera_una_pagina():
    paginas = lectura.paginar_desde_contenido(lectura.CONTENIDO_NO_DISPONIBLE)
    assert len(paginas) == 1
    assert paginas[0] == lectura.CONTENIDO_NO_DISPONIBLE