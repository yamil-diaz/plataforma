# -*- coding: utf-8 -*-
"""Integración: PUT /api/books/{id}/repaginate (admin, FASE 2, PASO 2).

Secuencia segura: fuente → extracción/paginación → capítulos → detector →
validación → transacción → borrar anteriores → insertar nuevos → actualizar
books → commit. PDF corrupto/ilegible → 422 sin tocar nada; PDF válido sin
capa de texto → placeholder (1 página).
"""
import io

import lectura
import server


def _pdf_bytes_con_texto(texto):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, texto)
    c.showPage()
    c.drawString(72, 700, texto + " página dos")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _pdf_bytes_sin_texto(num_pages=3):
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def test_repagina_contenido_con_capitulos(fake_db, as_admin):
    resp = as_admin.put("/api/books/50/repaginate")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "content"
    assert data["page_count"] >= 4
    assert data["chapters"] == 2
    assert data["diagnostico"]["pathological"] is False
    libro = fake_db.state["books"][50]
    assert libro["page_count"] == data["page_count"]
    assert libro["paginated_at"] is not None
    paginas = sorted([p for p in fake_db.state["book_pages"] if p[0] == 50], key=lambda p: p[1])
    assert len(paginas) == data["page_count"]
    assert paginas[0][2].startswith("CAPÍTULO 1")
    capitulos = [c for c in fake_db.state["chapters"] if c[0] == 50]
    assert len(capitulos) == 2
    assert capitulos[0][1] == "CAPÍTULO 1"
    assert capitulos[1][1] == "CAPÍTULO 2: El segundo"


def test_repagina_contenido_sin_capitulos_y_reemplaza_paginas(fake_db, as_admin):
    resp = as_admin.put("/api/books/52/repaginate")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "content"
    assert data["page_count"] == 1
    assert data["chapters"] == 0
    libro = fake_db.state["books"][52]
    assert libro["page_count"] == 1
    assert libro["paginated_at"] is not None
    paginas = [p for p in fake_db.state["book_pages"] if p[0] == 52]
    assert len(paginas) == 1
    assert paginas[0][2] != "página vieja"
    assert paginas[0][2].strip()


def test_contenido_patologico_rechazado_sin_modificar_y_sin_borrados(fake_db, as_admin):
    resp = as_admin.put("/api/books/51/repaginate")
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["pathological"] is True
    libro = fake_db.state["books"][51]
    assert libro["page_count"] == 2
    assert libro["paginated_at"] is None
    assert sorted([p for p in fake_db.state["book_pages"] if p[0] == 51]) == [
        (51, 1, "página vieja 1"),
        (51, 2, "página vieja 2"),
    ]
    consultas = [q for q, _ in fake_db.state["log"]]
    assert not any("delete from book_pages" in q for q in consultas)
    assert not any("delete from chapters" in q for q in consultas)


def test_repaginacion_doble_idempotente(fake_db, as_admin):
    r1 = as_admin.put("/api/books/52/repaginate")
    assert r1.status_code == 200, r1.text
    r2 = as_admin.put("/api/books/52/repaginate")
    assert r2.status_code == 200, r2.text
    assert r1.json()["page_count"] == r2.json()["page_count"] == 1
    paginas = [p for p in fake_db.state["book_pages"] if p[0] == 52]
    assert len(paginas) == 1
    assert len([c for c in fake_db.state["chapters"] if c[0] == 52]) == 0
    assert fake_db.state["books"][52]["page_count"] == 1


def test_repaginacion_doble_idempotente_con_capitulos(fake_db, as_admin):
    r1 = as_admin.put("/api/books/50/repaginate")
    assert r1.status_code == 200, r1.text
    r2 = as_admin.put("/api/books/50/repaginate")
    assert r2.status_code == 200, r2.text
    paginas = [p for p in fake_db.state["book_pages"] if p[0] == 50]
    assert len(paginas) == r2.json()["page_count"]
    capitulos = [c for c in fake_db.state["chapters"] if c[0] == 50]
    assert len(capitulos) == 2


def test_solo_admin_puede_repaginar(fake_db, as_uploader, as_third_party):
    assert as_uploader.put("/api/books/52/repaginate").status_code == 403
    assert as_third_party.put("/api/books/52/repaginate").status_code == 403
    assert fake_db.state["books"][52]["page_count"] == 1
    assert (52, 1, "página vieja") in fake_db.state["book_pages"]


def test_no_autenticado_401(client):
    assert client.put("/api/books/52/repaginate").status_code == 401


def test_libro_inexistente_404(as_admin):
    assert as_admin.put("/api/books/999/repaginate").status_code == 404


def test_error_mid_transaccion_hace_rollback(fake_db, as_admin, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado al guardar páginas")

    monkeypatch.setattr(server, "_guardar_paginas_libro", _boom)
    resp = as_admin.put("/api/books/52/repaginate")
    assert resp.status_code == 500
    libro = fake_db.state["books"][52]
    assert libro["page_count"] == 1
    assert libro["paginated_at"] is None
    assert (52, 1, "página vieja") in fake_db.state["book_pages"]


def test_pdf_valido_usa_pdf_y_reemplaza_paginas(fake_db, as_admin, tmp_path):
    ruta = tmp_path / "con_texto.pdf"
    ruta.write_bytes(_pdf_bytes_con_texto("Contenido extraído del PDF para la repaginación"))
    fake_db.state["books"][53]["pdf_path"] = str(ruta)
    resp = as_admin.put("/api/books/53/repaginate")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "pdf"
    assert data["page_count"] == 2
    assert data["chapters"] == 0
    libro = fake_db.state["books"][53]
    assert libro["page_count"] == 2
    assert libro["paginated_at"] is not None
    paginas = sorted([p for p in fake_db.state["book_pages"] if p[0] == 53], key=lambda p: p[1])
    assert len(paginas) == 2
    assert "Contenido extraído del PDF" in paginas[0][2]
    assert "página dos" in paginas[1][2]
    assert all(p[2].strip() for p in paginas)


def test_pdf_sin_capa_de_texto_usa_placeholder_una_pagina(fake_db, as_admin, tmp_path):
    ruta = tmp_path / "sin_texto.pdf"
    ruta.write_bytes(_pdf_bytes_sin_texto(3))
    fake_db.state["books"][53]["pdf_path"] = str(ruta)
    resp = as_admin.put("/api/books/53/repaginate")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "pdf"
    assert data["page_count"] == 1
    assert data["chapters"] == 0
    libro = fake_db.state["books"][53]
    assert libro["page_count"] == 1
    paginas = [p for p in fake_db.state["book_pages"] if p[0] == 53]
    assert len(paginas) == 1
    assert paginas[0][2] == lectura.CONTENIDO_NO_DISPONIBLE


def test_pdf_corrupto_422_sin_modificar_paginas(fake_db, as_admin, tmp_path):
    ruta = tmp_path / "corrupto.pdf"
    ruta.write_bytes(b"esto no es un pdf valido en absoluto \x00\x01\x02\xff")
    fake_db.state["books"][54]["pdf_path"] = str(ruta)
    resp = as_admin.put("/api/books/54/repaginate")
    assert resp.status_code == 422, resp.text
    assert "corrupto" in resp.json()["detail"].lower()
    libro = fake_db.state["books"][54]
    assert libro["page_count"] == 1
    assert libro["paginated_at"] is None
    assert (54, 1, "página vieja corrupto") in fake_db.state["book_pages"]
    consultas = [q for q, _ in fake_db.state["log"]]
    assert not any("delete" in q for q in consultas)


def test_contenido_vacio_rechazado_422(fake_db, as_admin):
    fake_db.state["books"][52]["content"] = ""
    resp = as_admin.put("/api/books/52/repaginate")
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["pathological"] is True
    assert "duplicación" in body["detail"]
    libro = fake_db.state["books"][52]
    assert libro["page_count"] == 1
    assert (52, 1, "página vieja") in fake_db.state["book_pages"]


def test_rechazo_indica_posible_duplicacion_o_corrupcion(fake_db, as_admin):
    resp = as_admin.put("/api/books/51/repaginate")
    assert resp.status_code == 422
    assert "duplicación" in resp.json()["detail"]
    assert "corrupción" in resp.json()["detail"]


def test_repagina_no_toca_otros_libros(fake_db, as_admin):
    resp = as_admin.put("/api/books/52/repaginate")
    assert resp.status_code == 200, resp.text
    for libro_id, page_count in [(10, 1), (20, 1), (40, 1), (50, 0), (51, 2)]:
        assert fake_db.state["books"][libro_id]["page_count"] == page_count
    assert (10, 1, "página del libro publicado") in fake_db.state["book_pages"]
    assert (40, 1, "página del publicado sin uploader") in fake_db.state["book_pages"]