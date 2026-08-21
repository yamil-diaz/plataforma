# -*- coding: utf-8 -*-
"""Robustez del sistema de Nueva Publicación (fase controlada).

Cubre: atomicidad de create_book (rollback total si falla el guardado de
páginas), validación de PDF por contenido/tamaño (413/422), roles
(autor y admin publican directo, user queda pendiente), acceso al detalle
de libros pendientes y protección de approve/reject (solo admin).
"""
import pytest

import server
from test_create_book import TEXTO_VALIDO, _pdf_bytes_con_texto, _subir_pdf


@pytest.fixture(autouse=True)
def _storage_temporal(tmp_path, monkeypatch):
    """Redirige el almacenamiento a un directorio temporal por test:
    ninguna prueba toca backend/storage real."""
    monkeypatch.setattr(server, "STORAGE_BOOKS", str(tmp_path))
    monkeypatch.setattr(server, "STORAGE_COVERS", str(tmp_path))
    return tmp_path


# ── A. Atomicidad: si _guardar_paginas_libro falla → rollback total ──────────

def test_create_book_rollback_total_si_falla_guardado_de_paginas(fake_db, as_uploader, monkeypatch, _storage_temporal):
    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado al guardar páginas")

    monkeypatch.setattr(server, "_guardar_paginas_libro", _boom)

    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])

    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(TEXTO_VALIDO), "falla.pdf")
    assert resp.status_code == 500, resp.text
    assert "fallo simulado" in resp.json()["detail"]

    # Sin libro fantasma ni páginas huérfanas
    assert len(fake_db.state["books"]) == libros_antes
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert all(b["title"] != "Libro de prueba" for b in fake_db.state["books"].values())

    # Sin archivo PDF huérfano en disco
    assert list(_storage_temporal.iterdir()) == []


# ── B. PDF demasiado grande → 413 ────────────────────────────────────────────

def test_create_book_pdf_demasiado_grande_devuelve_413(fake_db, as_uploader, monkeypatch, _storage_temporal):
    monkeypatch.setattr(server, "MAX_PDF_SIZE_BYTES", 1024)
    libros_antes = len(fake_db.state["books"])

    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto("X" * 5000), "grande.pdf")
    assert resp.status_code == 413, resp.text
    assert "50 MB" in resp.json()["detail"]

    assert len(fake_db.state["books"]) == libros_antes
    assert list(_storage_temporal.iterdir()) == []


# ── C. Archivo que no es PDF → 422 ───────────────────────────────────────────

def test_create_book_archivo_que_no_es_pdf_devuelve_422(fake_db, as_uploader, _storage_temporal):
    libros_antes = len(fake_db.state["books"])

    resp = as_uploader.post(
        "/api/books",
        data={
            "title": "Libro falso",
            "author_name": "Autor",
            "category": "Ficción",
            "price": 0.0,
        },
        files={"pdf_file": ("falso.pdf", b"esto no es un pdf en absoluto", "application/pdf")},
    )
    assert resp.status_code == 422, resp.text
    assert "PDF" in resp.json()["detail"]

    assert len(fake_db.state["books"]) == libros_antes
    assert all(b["title"] != "Libro falso" for b in fake_db.state["books"].values())
    assert list(_storage_temporal.iterdir()) == []


# ── D. Rol autor: crea y publica directamente ────────────────────────────────

def test_autor_puede_crear_y_publica_directamente(fake_db, as_autor):
    resp = _subir_pdf(as_autor, _pdf_bytes_con_texto(TEXTO_VALIDO), "autor.pdf")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["published"] == 1
    assert data["status"] == "published"
    book = fake_db.state["books"][int(data["id"])]
    assert book["published"] == 1
    assert book["uploader_id"] == 4
    assert book["page_count"] == 1


# ── E. Rol admin: crea y publica directamente ────────────────────────────────

def test_admin_puede_crear_y_publica_directamente(fake_db, as_admin):
    resp = _subir_pdf(as_admin, _pdf_bytes_con_texto(TEXTO_VALIDO), "admin.pdf")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["published"] == 1
    assert data["status"] == "published"
    book = fake_db.state["books"][int(data["id"])]
    assert book["published"] == 1
    assert book["uploader_id"] == 1
    assert book["page_count"] == 1


# ── F. Rol user: conserva el comportamiento pendiente ────────────────────────

def test_usuario_normal_crea_y_queda_pendiente(fake_db, as_uploader):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(TEXTO_VALIDO), "user.pdf")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["published"] == 0
    assert data["status"] == "pending"
    book = fake_db.state["books"][int(data["id"])]
    assert book["published"] == 0
    assert book["uploader_id"] == 2
    assert book["page_count"] == 1


# ── G. Detalle de libro pendiente: solo publicado/admin/uploader ─────────────

def test_tercero_no_puede_ver_detalle_de_libro_pendiente(fake_db, as_third_party):
    resp = as_third_party.get("/api/books/20")
    assert resp.status_code == 403, resp.text
    assert "no está publicado" in resp.json()["detail"]


def test_no_autenticado_no_puede_ver_detalle_de_libro_pendiente(fake_db, client):
    resp = client.get("/api/books/20")
    assert resp.status_code == 403, resp.text


def test_uploader_puede_ver_detalle_de_su_libro_pendiente(fake_db, as_uploader):
    resp = as_uploader.get("/api/books/20")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == "20"


def test_admin_puede_ver_detalle_de_libro_pendiente(fake_db, as_admin):
    resp = as_admin.get("/api/books/20")
    assert resp.status_code == 200, resp.text


def test_libro_publicado_sigue_accesible_sin_autenticacion(fake_db, client):
    resp = client.get("/api/books/10")
    assert resp.status_code == 200, resp.text


# ── H. Approve/reject: solo admin ────────────────────────────────────────────

def test_approve_admin_permitido(fake_db, as_admin):
    resp = as_admin.put("/api/books/20/approve")
    assert resp.status_code == 200, resp.text
    assert fake_db.state["books"][20]["published"] == 1


def test_reject_admin_permitido(fake_db, as_admin):
    resp = as_admin.delete("/api/books/20/reject")
    assert resp.status_code == 200, resp.text
    assert 20 not in fake_db.state["books"]


def test_approve_reject_no_admin_403(fake_db, as_uploader, as_autor):
    assert as_uploader.put("/api/books/20/approve").status_code == 403
    assert as_uploader.delete("/api/books/20/reject").status_code == 403
    assert as_autor.put("/api/books/20/approve").status_code == 403
    assert as_autor.delete("/api/books/20/reject").status_code == 403
    assert fake_db.state["books"][20]["published"] == 0