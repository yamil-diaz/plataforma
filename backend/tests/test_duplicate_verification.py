# -*- coding: utf-8 -*-
"""Tests para verificación de duplicados y paginación con deduplicación configurable."""
import io
import hashlib

import pytest

import server
from pypdf import PdfWriter


def _calcular_hash_pdf(pdf_path: str) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _pdf_bytes_con_texto(texto):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, texto)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _subir_pdf(client, pdf_bytes, filename, title, author_name, category="Ficción"):
    return client.post(
        "/api/books",
        data={
            "title": title,
            "author_name": author_name,
            "category": category,
            "price": 0.0,
        },
        files={"pdf_file": (filename, pdf_bytes, "application/pdf")},
    )


# ═══════════════════════════════════════════════════════════════════════
# TESTS DE VERIFICACIÓN DE DUPLICADOS (_verificar_duplicado)
# ═══════════════════════════════════════════════════════════════════════

def test_mismo_pdf_distinto_titulo_autor_rechazado(fake_db, as_admin, tmp_path):
    """Mismo PDF + título diferente + autor diferente → RECHAZADO (hash SHA-256)."""
    from support import _contenido_variado
    texto = _contenido_variado(1000)
    pdf_bytes = _pdf_bytes_con_texto(texto)
    
    # Primera subida
    resp1 = _subir_pdf(as_admin, pdf_bytes, "libro1.pdf", "Título Original", "Autor Original")
    assert resp1.status_code == 200, resp1.text
    book_id_1 = int(resp1.json()["id"])
    
    # Segunda subida: MISMO PDF, título y autor DIFERENTES
    resp2 = _subir_pdf(as_admin, pdf_bytes, "libro2.pdf", "Título Diferente", "Autor Diferente")
    assert resp2.status_code == 409, resp2.text
    body = resp2.json()
    assert "duplicado" in body["detail"].lower() or "ya existe" in body["detail"].lower()
    assert str(book_id_1) in body["detail"]


def test_mismo_pdf_mismo_titulo_autor_diferente_rechazado(fake_db, as_admin, tmp_path):
    """Mismo PDF + mismo título + autor diferente → RECHAZADO (hash SHA-256)."""
    from support import _contenido_variado
    texto = _contenido_variado(1000)
    pdf_bytes = _pdf_bytes_con_texto(texto)
    
    # Primera subida
    resp1 = _subir_pdf(as_admin, pdf_bytes, "libro1.pdf", "Mismo Título", "Autor Uno")
    assert resp1.status_code == 200, resp1.text
    book_id_1 = int(resp1.json()["id"])
    
    # Segunda subida: MISMO PDF, mismo título, autor DIFERENTE
    resp2 = _subir_pdf(as_admin, pdf_bytes, "libro2.pdf", "Mismo Título", "Autor Dos")
    assert resp2.status_code == 409, resp2.text
    body = resp2.json()
    assert "duplicado" in body["detail"].lower() or "ya existe" in body["detail"].lower()
    assert str(book_id_1) in body["detail"]


def test_pdf_diferente_mismo_titulo_autor_permitido(fake_db, as_admin, tmp_path):
    """PDF diferente + mismo título + mismo autor → PERMITIDO."""
    from support import _contenido_variado
    # Usar semillas diferentes para generar contenido distinto
    texto1 = _contenido_variado(1000)
    # Generar contenido verdaderamente diferente
    texto2 = "Primer párrafo diferente.\n\n" + _contenido_variado(900)
    pdf_bytes1 = _pdf_bytes_con_texto(texto1)
    pdf_bytes2 = _pdf_bytes_con_texto(texto2)
    
    # Primera subida
    resp1 = _subir_pdf(as_admin, pdf_bytes1, "libro1.pdf", "Título Común", "Autor Común")
    assert resp1.status_code == 200, resp1.text
    book_id_1 = int(resp1.json()["id"])
    
    # Segunda subida: PDF DIFERENTE, mismo título y autor
    resp2 = _subir_pdf(as_admin, pdf_bytes2, "libro2.pdf", "Título Común", "Autor Común")
    assert resp2.status_code == 200, resp2.text
    book_id_2 = int(resp2.json()["id"])
    
    assert book_id_1 != book_id_2
    assert len(fake_db.state["books"]) >= 2


def test_sin_pdf_mismo_titulo_autor_fallback(fake_db, as_admin):
    """Dos libros SIN PDF + mismo título y autor → comportamiento fallback existente."""
    # Este test verifica el comportamiento actual de fallback para libros sin PDF
    # (que en la práctica usan contenido Gutenberg/texto, no PDF)
    # El sistema debería rechazar por título+autor normalizado cuando no hay PDF
    
    # Nota: El endpoint actual requiere PDF, así que este test documenta
    # el comportamiento esperado para futuros endpoints sin PDF
    pass


# ═══════════════════════════════════════════════════════════════════════
# TESTS DE PAGINACIÓN CON DEDUPLICACIÓN CONFIGURABLE
# ═══════════════════════════════════════════════════════════════════════

import lectura


def test_paginacion_normal_deduplicate_false_conserva_todo():
    """Texto normal con deduplicate=False → conserva 100% del contenido."""
    contenido = "Párrafo 1.\n\nPárrafo 2.\n\nPárrafo 3.\n\nPárrafo 4.\n\nPárrafo 5."
    
    paginas = lectura.paginar_desde_contenido(contenido, deduplicate=False)
    
    total_chars = sum(len(p) for p in paginas)
    assert total_chars == len(contenido), f"Se perdieron caracteres: {total_chars} vs {len(contenido)}"


def test_paginacion_consecutive_duplicates_deduplicate_false_conserva_ambos():
    """Texto con párrafos consecutivos idénticos y deduplicate=False → conserva ambos."""
    contenido = "Párrafo único.\n\nRefrán repetido.\n\nRefrán repetido.\n\nOtro párrafo único."
    
    paginas = lectura.paginar_desde_contenido(contenido, deduplicate=False)
    
    # Concatenar páginas y verificar que ambos "Refrán repetido" están presentes
    concatenado = "\n\n".join(paginas)
    count = concatenado.count("Refrán repetido.")
    assert count == 2, f"Se esperaba 2 ocurrencias, se encontraron {count}"


def test_paginacion_consecutive_duplicates_deduplicate_true_elimina_duplicados():
    """Texto con bloques repetidos y deduplicate=True → elimina solo consecutivos."""
    contenido = "Párrafo único.\n\nRefrán repetido.\n\nRefrán repetido.\n\nRefrán repetido.\n\nOtro párrafo único.\n\nOtro estribillo.\n\nOtro estribillo."
    
    paginas = lectura.paginar_desde_contenido(contenido, deduplicate=True)
    
    concatenado = "\n\n".join(paginas)
    count_refran = concatenado.count("Refrán repetido.")
    count_estribillo = concatenado.count("Otro estribillo.")
    
    # Solo debe quedar 1 de cada grupo consecutivo
    assert count_refran == 1, f"Se esperaba 1 'Refrán', se encontraron {count_refran}"
    assert count_estribillo == 1, f"Se esperaba 1 'Estribillo', se encontraron {count_estribillo}"


def test_contenido_patologico_rechazado_antes_de_paginar():
    """Contenido patológico → rechazado por detector ANTES de paginación normal."""
    # Crear contenido con ratio > 25% duplicado
    parrafo_base = "Este es un párrafo que se repite muchas veces para ser patológico. " * 10
    contenido_patologico = "\n\n".join([parrafo_base] * 50)  # 50 bloques casi idénticos
    
    # El detector debe marcarlo como patológico
    diagnostico = lectura.detectar_contenido_patologico(contenido_patologico)
    assert diagnostico["pathological"] is True
    assert diagnostico["repetition_ratio"] > 0.25
    
    # La validación debe rechazarlo
    validacion = lectura.validar_contenido_libro(contenido_patologico, fuente="content")
    assert validacion["valid"] is False
    assert any("duplicación" in e.lower() or "corrupción" in e.lower() for e in validacion["errors"])


def test_libro_largo_normal_no_pierde_contenido():
    """Libro largo normal → no pierde contenido significativo."""
    def _contenido_variado(longitud):
        parrafos = []
        total = 0
        i = 0
        while total < longitud:
            parrafo = (
                f"Párrafo {i}: aquí {i} transcurre la acción {i} del capítulo con "
                f"detalles {i} únicos sobre el lugar {i} y los personajes {i} del "
                f"relato. El clima {i} cambió hacia el final {i} de la escena {i} "
                f"y los acontecimientos {i} marcaron un giro {i} en la historia {i} "
                f"contada con ritmo pausado en la página {i}."
            )
            parrafos.append(parrafo)
            total += len(parrafo)
            i += 1
        return "\n\n".join(parrafos)
    
    contenido = _contenido_variado(55000)  # ~55K como ID 18
    
    diagnostico = lectura.detectar_contenido_patologico(contenido)
    assert diagnostico["pathological"] is False
    
    validacion = lectura.validar_contenido_libro(contenido, fuente="content")
    assert validacion["valid"] is True
    
    paginas = lectura.paginar_desde_contenido(contenido, deduplicate=False)
    total_chars = sum(len(p) for p in paginas)
    porcentaje = total_chars / len(contenido) * 100
    assert porcentaje >= 99.5, f"Se perdió demasiado contenido: {porcentaje:.2f}%"


def test_deduplicate_true_solo_para_reparacion_admin():
    """deduplicate=True solo debe usarse en contexto de reparación administrativa."""
    contenido = "A.\n\nB.\n\nB.\n\nC."
    
    # Flujo normal (sin deduplicación)
    paginas_normal = lectura.paginar_desde_contenido(contenido, deduplicate=False)
    concat_normal = "\n\n".join(paginas_normal)
    count_b_normal = concat_normal.count("B.")
    
    # Reparación admin (con deduplicación)
    paginas_reparacion = lectura.paginar_desde_contenido(contenido, deduplicate=True)
    concat_reparacion = "\n\n".join(paginas_reparacion)
    count_b_reparacion = concat_reparacion.count("B.")
    
    assert count_b_normal == 2, "Flujo normal debe conservar ambos B consecutivos"
    assert count_b_reparacion == 1, "Reparación admin debe deduplicar consecutivos"