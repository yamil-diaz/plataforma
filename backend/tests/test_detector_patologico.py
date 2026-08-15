# -*- coding: utf-8 -*-
"""Detector de contenido patológico (PASO 2): heurísticas y anti-falsos positivos."""
import lectura
from support import _contenido_patologico, _contenido_variado


def test_contenido_variado_limpio_no_es_patologico():
    info = lectura.detectar_contenido_patologico(_contenido_variado(6000))
    assert info["pathological"] is False
    assert info["reason"] is None
    assert info["repeated_fragment_count"] == 0
    assert info["repetition_ratio"] == 0.0


def test_parrafo_repetido_8_veces_es_patologico():
    info = lectura.detectar_contenido_patologico(_contenido_patologico())
    assert info["pathological"] is True
    assert info["repeated_fragment_count"] >= 2
    assert info["repetition_ratio"] >= 0.25
    assert "Repetición" in info["reason"]


def test_paginas_identicas_consecutivas_patologico():
    paginas = ["página de ejemplo con contenido idéntico de prueba para el detector patológico de la plataforma."] * 10
    info = lectura.detectar_contenido_patologico(_contenido_variado(3000), paginas)
    assert info["pathological"] is True
    assert info["duplicate_consecutive_pages"] == 9
    assert "Páginas consecutivas" in info["reason"]


def test_paginas_casi_identicas_patologico():
    base = (
        "Texto largo idéntico en todas las páginas de ejemplo para detectar "
        "contenido casi duplicado que debe rechazarse por corrupción potencial "
        "de la fuente. Se repite el mismo párrafo con mínimas variaciones. "
    )
    paginas = [base + letra for letra in "abcd"]
    info = lectura.detectar_contenido_patologico(_contenido_variado(3000), paginas)
    assert info["pathological"] is True
    assert info["duplicate_consecutive_pages"] == 0
    assert info["near_duplicate_consecutive_pages"] >= 2


def test_contenido_vacio_patologico():
    info = lectura.detectar_contenido_patologico("")
    assert info["pathological"] is True
    assert "vacío" in info["reason"]


def test_contenido_corto_legitimo_no_patologico():
    info = lectura.detectar_contenido_patologico("Un poema breve de pocas líneas para lectores exigentes.")
    assert info["pathological"] is False
    assert info["short_content"] is True


def test_estribillo_en_minoria_no_falso_positivo():
    contenido = _contenido_variado(4000) + "¡Viva!\n" * 5
    info = lectura.detectar_contenido_patologico(contenido)
    assert info["pathological"] is False


def test_frases_repetidas_con_ratio_bajo_no_patologico():
    frase_a = "A" * 60
    frase_b = "B" * 60
    bloques = []
    for i in range(60):
        bloques.append(f"Párrafo {i}: aquí {i} transcurre la acción {i} del capítulo con detalles {i} únicos sobre el lugar {i} y los personajes {i} del relato. El clima {i} cambió hacia el final {i} de la escena {i} y los acontecimientos {i} marcaron un giro {i} en la historia {i} contada con ritmo pausado en la página {i}.")
        if i < 12:
            bloques.append(frase_a if i % 2 == 0 else frase_b)
    info = lectura.detectar_contenido_patologico("\n\n".join(bloques))
    assert info["repeated_fragment_count"] >= 2
    assert info["repetition_ratio"] < 0.25
    assert info["pathological"] is False


def test_placeholder_no_patologico():
    info = lectura.detectar_contenido_patologico(
        lectura.CONTENIDO_NO_DISPONIBLE, [lectura.CONTENIDO_NO_DISPONIBLE]
    )
    assert info["pathological"] is False
    assert info["short_content"] is True


def test_info_incluye_campos_de_diagnostico():
    info = lectura.detectar_contenido_patologico(_contenido_variado(2000))
    for campo in (
        "pathological",
        "reason",
        "repeated_fragment_count",
        "repetition_ratio",
        "duplicate_consecutive_pages",
        "near_duplicate_consecutive_pages",
        "content_length",
        "short_content",
    ):
        assert campo in info