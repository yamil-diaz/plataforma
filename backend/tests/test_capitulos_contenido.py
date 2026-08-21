# -*- coding: utf-8 -*-
"""Detección de capítulos para libros sin PDF (contenido textual), PASO 2."""
import lectura
from support import _contenido_con_capitulos, _contenido_variado


def test_wrapper_detecta_capitulo_numeral():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "CAPÍTULO 1\n\nTexto de ejemplo para el capítulo uno."
    )
    assert len(paginas) == 1
    assert capitulos == [{"page": 1, "title": "CAPÍTULO 1"}]


def test_wrapper_detecta_capitulo_romano():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "Capítulo I\n\nTexto del primer capítulo del libro."
    )
    assert capitulos == [{"page": 1, "title": "Capítulo I"}]


def test_wrapper_detecta_encabezado_ingles():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "CHAPTER 2\n\nThe second chapter begins here."
    )
    assert capitulos == [{"page": 1, "title": "CHAPTER 2"}]


def test_wrapper_detecta_capitulo_con_titulo():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "CAPÍTULO 3: El regreso\n\nTexto del capítulo tres."
    )
    assert capitulos == [{"page": 1, "title": "CAPÍTULO 3: El regreso"}]


def test_wrapper_sin_encabezados_no_inventa_capitulos():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(_contenido_variado(3000))
    assert len(paginas) >= 1
    assert capitulos == []


def test_wrapper_multi_pagina_detecta_capitulos_por_pagina():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(_contenido_con_capitulos())
    assert len(paginas) >= 4
    assert paginas[0].startswith("CAPÍTULO 1")
    assert capitulos[0] == {"page": 1, "title": "CAPÍTULO 1"}
    assert capitulos[1]["title"] == "CAPÍTULO 2: El segundo"
    assert capitulos[1]["page"] > 1


def test_encabezado_en_posicion_no_valida_no_se_detecta():
    contenido = "\n".join([f"Línea de relleno {i}" for i in range(1, 8)]) + "\nCAPÍTULO 1\n\nTexto real."
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(contenido)
    assert capitulos == []


# ── PASO 3: secciones ampliadas (H-K): PARTE / ACTO / ESCENA / NOCHE ─────────

def test_detecta_parte_romana():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "PARTE I\n\nTexto de la primera parte del libro."
    )
    assert capitulos == [{"page": 1, "title": "PARTE I"}]


def test_detecta_parte_numerada():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "PARTE 1: Los sueños\n\nTexto de la primera parte."
    )
    assert capitulos == [{"page": 1, "title": "PARTE 1: Los sueños"}]


def test_detecta_acto_primero():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "ACTO PRIMERO\n\nLa escena transcurre en un salón."
    )
    assert capitulos == [{"page": 1, "title": "ACTO PRIMERO"}]


def test_detecta_escena_primera():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "ESCENA PRIMERA\n\nEntra el personaje principal."
    )
    assert capitulos == [{"page": 1, "title": "ESCENA PRIMERA"}]


def test_detecta_primera_noche():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "PRIMERA NOCHE\n\nEl narrador comienza su relato."
    )
    assert capitulos == [{"page": 1, "title": "PRIMERA NOCHE"}]


def test_detecta_segunda_noche():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "SEGUNDA NOCHE\n\nContinúa el relato."
    )
    assert capitulos == [{"page": 1, "title": "SEGUNDA NOCHE"}]


def test_capitulo_romano_y_titulo_siguen_funcionando():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "CAPÍTULO II: El viaje\n\nTexto del capítulo."
    )
    assert capitulos == [{"page": 1, "title": "CAPÍTULO II: El viaje"}]


def test_numero_aislado_no_inventa_capitulo():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "1\n\nTexto de la primera página sin encabezados de capítulo."
    )
    assert capitulos == []


def test_prosa_con_parte_no_inventa_capitulo():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        "En la primera parte de la historia el protagonista aún no sabe que "
        "toda la segunda parte cambiará su destino para siempre."
    )
    assert capitulos == []


def test_create_book_sin_pdf_no_crea_capitulos_artificiales(fake_db, as_uploader):
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
    assert fake_db.state["chapters"] == []