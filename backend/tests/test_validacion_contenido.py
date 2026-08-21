# -*- coding: utf-8 -*-
"""Validación central de contenido (PASO 3): tests A-P.

Cubre la capa de validación reutilizable (lectura.validar_contenido_libro)
aplicada en todos los flujos: subida PDF, importación ZIP, Gutenberg,
repaginación admin y migración. Un libro con contenido inválido
(placeholder, fabricado, basura o insuficiente) NUNCA se publica ni se pagina.
"""
import io
import zipfile

import pytest

import lectura
import migrate_db_fase2_lectura as migracion
import server
from test_create_book import TEXTO_VALIDO, _pdf_bytes_con_texto, _pdf_bytes_sin_texto, _subir_pdf
from support import _contenido_patologico, _contenido_variado

IDS_SEMBRADOS = (10, 20, 30, 40, 50, 51, 52, 53, 54)


@pytest.fixture()
def _storage_temporal(tmp_path, monkeypatch):
    """Redirige el almacenamiento a un directorio temporal por test."""
    monkeypatch.setattr(server, "STORAGE_BOOKS", str(tmp_path))
    monkeypatch.setattr(server, "STORAGE_COVERS", str(tmp_path))
    return tmp_path


@pytest.fixture()
def _zip_env(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORAGE_BOOKS", str(tmp_path / "books"))
    monkeypatch.setattr(server, "STORAGE_COVERS", str(tmp_path / "covers"))
    monkeypatch.setattr(server, "TEMP_DIR", str(tmp_path / "temp"))
    (tmp_path / "books").mkdir(parents=True, exist_ok=True)
    (tmp_path / "covers").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _contenido_fabricado_x200():
    """Mismo patrón que update_books_text.py: 10 capítulos falsos con un
    párrafo repetido 20 veces cada uno (200 repeticiones en total)."""
    parrafo = "Este es el párrafo base que el script fabricador repetía sin límite."
    contenido = ""
    for capitulo in range(1, 11):
        contenido += f"\n\nCAPÍTULO {capitulo}\n\n" + (parrafo + "\n\n") * 20
    return contenido


def _ejecutar_zip(fake_db, _zip_env, archivos, task_id="test-task"):
    zip_path = _zip_env / "lote.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for nombre, datos in archivos:
            z.writestr(nombre, datos)
    server.import_tasks[task_id] = {
        "status": "processing",
        "total": 0,
        "processed": 0,
        "errors": [],
        "message": "",
    }
    server.process_bulk_zip(task_id, str(zip_path), "Ficción", 0.0)
    return server.import_tasks.pop(task_id)


# ── A. PASS: PDF bueno se publica ────────────────────────────────────────────

def test_a_pdf_bueno_se_publica(fake_db, as_uploader, _storage_temporal):
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(TEXTO_VALIDO), "bueno.pdf")
    assert resp.status_code == 200, resp.text
    book_id = int(resp.json()["id"])
    book = fake_db.state["books"][book_id]
    assert book["content"] != lectura.CONTENIDO_NO_DISPONIBLE
    assert "transcurre la acción" in book["content"]
    assert book["page_count"] == 1


# ── B. FAIL: PDF inválido (no es PDF real) ───────────────────────────────────

def test_b_pdf_invalido_rechazado(fake_db, as_uploader, _storage_temporal):
    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
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
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert len(fake_db.state["books"]) == libros_antes
    assert list(_storage_temporal.iterdir()) == []


# ── C. FAIL: PDF válido pero sin capa de texto ───────────────────────────────

def test_c_pdf_sin_texto_rechazado(fake_db, as_uploader, _storage_temporal):
    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
    resp = _subir_pdf(as_uploader, _pdf_bytes_sin_texto(3), "sin_texto.pdf")
    assert resp.status_code == 422, resp.text
    assert "texto" in resp.json()["detail"].lower()
    assert len(fake_db.state["books"]) == libros_antes
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert list(_storage_temporal.iterdir()) == []


# ── D. FAIL: placeholder no es contenido válido ──────────────────────────────

def test_d_placeholder_invalido():
    v = lectura.validar_contenido_libro(lectura.CONTENIDO_NO_DISPONIBLE)
    assert v["valid"] is False
    assert v["detalle"]["es_placeholder"] is True
    assert v["errors"]


# ── E. FAIL: párrafo repetido ×200 (fabricado) ───────────────────────────────

def test_e_contenido_fabricado_x200_invalido():
    v = lectura.validar_contenido_libro(_contenido_fabricado_x200())
    assert v["valid"] is False
    assert v["detalle"]["pathological"] is True


def test_e_pdf_con_parrafo_repetido_rechazado(fake_db, as_uploader, _storage_temporal):
    libros_antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
    resp = _subir_pdf(as_uploader, _pdf_bytes_con_texto(_contenido_fabricado_x200()), "fabricado.pdf")
    assert resp.status_code == 422, resp.text
    assert "duplicación" in resp.json()["detail"]
    assert len(fake_db.state["books"]) == libros_antes
    assert len(fake_db.state["book_pages"]) == paginas_antes
    assert list(_storage_temporal.iterdir()) == []


# ── F. PASS: contenido normal largo ──────────────────────────────────────────

def test_f_contenido_largo_valido():
    v = lectura.validar_contenido_libro(_contenido_variado(6000))
    assert v["valid"] is True
    assert v["errors"] == []


# ── G. PASS: contenido corto pero legítimo (poema breve) ─────────────────────

def test_g_poema_breve_legitimo_valido():
    poema = (
        "En la noche callada se posa la luna sobre el agua serena del viejo estanque.\n"
        "Los sauces murmuran secretos de verano entre las ramas altas del sendero.\n"
        "Una brisa ligera despierta las campanas del pueblo dormido y el eco responde.\n"
        "El caminante recuerda la casa de su infancia, el pan caliente y la voz de su madre.\n"
        "El tiempo pasa lento como el humo del fuego que arde en la chimenea antigua.\n"
        "Las estrellas se encienden una a una sobre los campos verdes de la colina.\n"
        "Mañana volverá el sol y con él la rutina, pero esta noche el mundo es solo silencio."
    )
    v = lectura.validar_contenido_libro(poema, None, fuente="gutenberg")
    assert v["valid"] is True
    assert v["errors"] == []


# ── L. PASS: sin capítulos, chapters vacío y el lector funciona ──────────────

def test_l_sin_capitulos_chapters_vacio_y_libro_funciona(fake_db, as_admin):
    resp = as_admin.put("/api/books/52/repaginate")
    assert resp.status_code == 200, resp.text
    assert resp.json()["chapters"] == 0
    assert resp.json()["page_count"] >= 1
    assert [c for c in fake_db.state["chapters"] if c[0] == 52] == []


# ── M. PASS: ZIP con PDF válido se importa ───────────────────────────────────

def test_m_zip_con_pdf_valido_importa(fake_db, _zip_env):
    antes = len(fake_db.state["books"])
    resultado = _ejecutar_zip(fake_db, _zip_env, [("libro.pdf", _pdf_bytes_con_texto(TEXTO_VALIDO))])
    assert resultado["processed"] == 1
    assert resultado["errors"] == []
    nuevos = [b for b in fake_db.state["books"].values() if b["id"] not in IDS_SEMBRADOS]
    assert len(nuevos) == 1
    libro = nuevos[0]
    assert libro["published"] == 1
    assert "transcurre la acción" in libro["content"]
    assert libro["page_count"] == 1
    assert len(fake_db.state["books"]) == antes + 1


# ── N. FAIL: ZIP con falso .pdf no se importa ────────────────────────────────

def test_n_zip_con_falso_pdf_no_importa(fake_db, _zip_env):
    antes = len(fake_db.state["books"])
    resultado = _ejecutar_zip(fake_db, _zip_env, [("falso.pdf", b"esto no es un pdf en absoluto")])
    assert resultado["processed"] == 0
    assert any("PDF" in e and "magic" in e for e in resultado["errors"])
    assert len(fake_db.state["books"]) == antes


# ── O. FAIL: extracción fallida en ZIP no publica ────────────────────────────

def test_o_zip_con_extraccion_fallida_no_publica(fake_db, _zip_env):
    antes = len(fake_db.state["books"])
    paginas_antes = len(fake_db.state["book_pages"])
    resultado = _ejecutar_zip(fake_db, _zip_env, [("vacio.pdf", _pdf_bytes_sin_texto(3))])
    assert resultado["processed"] == 0
    assert any("rechazado" in e for e in resultado["errors"])
    assert len(fake_db.state["books"]) == antes
    assert len(fake_db.state["book_pages"]) == paginas_antes


# ── P. FAIL: la migración no procesa contenido inválido ──────────────────────

def test_p_migracion_no_procesa_contenido_invalido():
    assert migracion._validar_libro_para_migracion({"content": _contenido_patologico()})["valid"] is False
    assert migracion._validar_libro_para_migracion({"content": _contenido_fabricado_x200()})["valid"] is False
    assert migracion._validar_libro_para_migracion({"content": lectura.CONTENIDO_NO_DISPONIBLE})["valid"] is False
    assert migracion._validar_libro_para_migracion({"content": ""})["valid"] is False
    assert migracion._validar_libro_para_migracion({"content": _contenido_variado(6000)})["valid"] is True


# ── Reglas unitarias de la validación central ────────────────────────────────

def test_basura_racha_larga_detectada():
    assert lectura._detectar_basura(_contenido_variado(3000) + "á" * 300) is True


def test_basura_linea_repetida_detectada():
    assert lectura._detectar_basura(_contenido_variado(3000) + "\n" + "\n".join(["á"] * 534)) is True


def test_basura_sustitucion_detectada():
    assert lectura._detectar_basura("texto normal " * 30 + "\ufffd" * 6) is True


def test_contenido_insuficiente_rechazado():
    v = lectura.validar_contenido_libro("Texto muy corto")
    assert v["valid"] is False
    assert any("insuficiente" in e for e in v["errors"])


def test_paginas_vacias_en_exceso_rechazadas():
    v = lectura.validar_contenido_libro(_contenido_variado(2000), ["", "", "", "hola"], fuente="pdf")
    assert v["valid"] is False
    assert any("vacías" in e for e in v["errors"])


def test_pdf_sin_pagina_con_texto_suficiente_rechazado():
    v = lectura.validar_contenido_libro(
        _contenido_variado(500), ["abc", "def", "ghi", "jkl", "mno"], fuente="pdf"
    )
    assert v["valid"] is False
    assert any("Extracción insuficiente" in e for e in v["errors"])


def test_validacion_devuelve_detalle_completo():
    v = lectura.validar_contenido_libro(_contenido_variado(6000))
    for campo in (
        "pathological",
        "content_length",
        "short_content",
        "es_placeholder",
        "es_basura",
        "minimo_contenido",
    ):
        assert campo in v["detalle"]


def test_procesar_contenido_para_publicacion_pipeline():
    resultado = lectura.procesar_contenido_para_publicacion(
        content=_contenido_variado(6000), fuente="content"
    )
    assert resultado["validacion"]["valid"] is True
    assert resultado["paginas"]
    assert resultado["capitulos"] == []


def test_gutenberg_invalido_rechazado(fake_db, as_admin, monkeypatch):
    """El endpoint de Gutenberg no puede publicar texto fabricado/placeholder."""

    class FalsaRespuesta:
        def __init__(self, datos):
            self._datos = datos

        def read(self):
            return self._datos

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    import json
    import urllib.request

    def _fake_urlopen(url, headers=None):
        destino = url.full_url if hasattr(url, "full_url") else str(url)
        if "gutendex.com" in destino:
            return FalsaRespuesta(
                json.dumps(
                    {
                        "title": "Libro corrupto",
                        "authors": [{"name": "Autor"}],
                        "formats": {"text/plain; charset=utf-8": "http://texto"},
                    }
                ).encode()
            )
        return FalsaRespuesta(lectura.CONTENIDO_NO_DISPONIBLE.encode())

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    resp = as_admin.post("/api/admin/gutenberg/fetch", data={"book_id": 1234})
    assert resp.status_code == 422, resp.text
    assert "rechazado" in resp.json()["detail"]
    assert len(fake_db.state["books"]) == len(IDS_SEMBRADOS)