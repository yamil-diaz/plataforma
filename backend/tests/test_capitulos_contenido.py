# -*- coding: utf-8 -*-
"""Detección de capítulos para libros sin PDF (contenido textual), PASO 2."""
import lectura
from support import _contenido_con_capitulos, _contenido_variado


def _contenido_con_capitulo_largo(texto_capitulo, texto_cuerpo):
    """Genera contenido con capítulo + cuerpo largo suficiente para pasar validación (>300 chars).
    Usa texto variado para no disparar el detector patológico."""
    # Generar párrafos completamente variados sin repetición de patrones
    parrafos = [
        "El amanecer pintaba de oro las cumbres lejanas mientras el viento susurraba entre los pinos centenarios.",
        "Una niebla ligera cubría el valle, ocultando senderos que solo los antiguos conocían de memoria.",
        "El protagonista avanzaba con paso decidido, cargando el peso de promesas hechas bajo otra luna.",
        "Los pájaros cantaban en la copa de los robles, ajenos a las sombras que se alargaban al sur.",
        "En su bolsillo guardaba la carta sellada con cera roja, testigo mudo de un juramento antiguo.",
        "El río serpenteaba entre piedras pulidas por mil inviernos, cantando su canción eterna.",
        "Una torre en ruinas se alzaba al fondo, vigilante silenciosa de batallas olvidadas.",
        "El aire olía a tierra húmeda y a hierbas medicinales que su abuela le enseñó a reconocer.",
        "Cada paso resonaba en el silencio, eco de decisiones que no podían deshacerse ya.",
        "El cielo se tiñó de carmín y violeta, anunciando una noche que traería revelaciones.",
        "Lejos, una campana doblaba despacio, marcando el fin de un día y el inicio de otro.",
        "Sus manos, curtidas por el trabajo y el viaje, temblaban apenas al tocar el pergamino.",
        "Las estrellas surgían una a una, testigos fríos de historias que el tiempo no borra.",
        "Mañana cruzaría el puente de cuerda, y nada volvería a ser como antes para él.",
        "El viento traía olor a lluvia lejana, promesa de tormentas que limpian el aire.",
    ]
    cuerpo_largo = "\n\n".join(parrafos)
    return f"{texto_capitulo}\n\n{cuerpo_largo}"


def test_wrapper_detecta_capitulo_numeral():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("CAPÍTULO 1", "Texto de ejemplo para el capítulo uno.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "CAPÍTULO 1"}]


def test_wrapper_detecta_capitulo_romano():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("Capítulo I", "Texto del primer capítulo del libro.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "Capítulo I"}]


def test_wrapper_detecta_encabezado_ingles():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("CHAPTER 2", "The second chapter begins here.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "CHAPTER 2"}]


def test_wrapper_detecta_capitulo_con_titulo():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("CAPÍTULO 3: El regreso", "Texto del capítulo tres.")
    )
    assert len(paginas) >= 1
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
        _contenido_con_capitulo_largo("PARTE I", "Texto de la primera parte del libro.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "PARTE I"}]


def test_detecta_parte_numerada():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("PARTE 1: Los sueños", "Texto de la primera parte.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "PARTE 1: Los sueños"}]


def test_detecta_acto_primero():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("ACTO PRIMERO", "La escena transcurre en un salón.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "ACTO PRIMERO"}]


def test_detecta_escena_primera():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("ESCENA PRIMERA", "Entra el personaje principal.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "ESCENA PRIMERA"}]


def test_detecta_primera_noche():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("PRIMERA NOCHE", "El narrador comienza su relato.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "PRIMERA NOCHE"}]


def test_detecta_segunda_noche():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("SEGUNDA NOCHE", "Continúa el relato.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "SEGUNDA NOCHE"}]


def test_capitulo_romano_y_titulo_siguen_funcionando():
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(
        _contenido_con_capitulo_largo("CAPÍTULO II: El viaje", "Texto del capítulo.")
    )
    assert len(paginas) >= 1
    assert capitulos == [{"page": 1, "title": "CAPÍTULO II: El viaje"}]


def test_numero_aislado_no_inventa_capitulo():
    # Contenido largo para pasar validación, pero solo número aislado
    contenido = _contenido_con_capitulo_largo("1", "Texto de la primera página sin encabezados de capítulo.")
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(contenido)
    assert len(paginas) >= 1
    assert capitulos == []


def test_prosa_con_parte_no_inventa_capitulo():
    contenido = _contenido_variado(500) + "\n\nEn la primera parte de la historia el protagonista aún no sabe que toda la segunda parte cambiará su destino para siempre."
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(contenido)
    assert len(paginas) >= 1
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