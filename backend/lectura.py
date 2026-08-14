# -*- coding: utf-8 -*-
"""
backend/lectura.py — Lógica de lectura (FASE 2).
Port validado de lectura_pura.py (11/11 tests PASS en la fase de validación).
Extracción por páginas, detección de capítulos (no recompensan, solo organizan)
y paginación de respaldo para libros sin PDF.
"""
import re

PAGE_CHARS = 1800

# Acepta: CAP[ÍI]TULO / CAPITULO / CHAPTER + numeral (1, I, II...) o numeral
# escrito (PRIMERO, UNO, ONE, FIRST...). El encabezado debe iniciar la línea.
_CHAPTER_RE = re.compile(
    r"^\s*(cap[ií]tulo|capitulo|chapter)\s+"
    r"(?:n[uú]mero\s+|n[uú]m\.\s*)?"
    r"(?:\d{1,3}|[ivxlcdm]+|"
    r"primero|primera|segundo|segunda|tercero|tercera|cuarto|cuarta|quinto|quinta|"
    r"sexto|s[eé]ptimo|octavo|noveno|d[eé]cimo|"
    r"uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|first|second|third)\b"
    r"(?:\s*(?:[:.\-\u2013]\s*)?(?P<title>[^\n]{0,60}))?$",
    re.IGNORECASE | re.UNICODE,
)


def extraer_paginas(pdf_path: str):
    """Extrae el texto de TODAS las páginas del PDF, sin ningún límite.
    Devuelve una lista de str, índice 0 = página 1."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    paginas = []
    for i in range(total):
        texto = reader.pages[i].extract_text() or ""
        paginas.append(texto)
    return paginas


def _linea_es_encabezado(linea: str) -> bool:
    """True si la línea es un encabezado de capítulo y es corta (estilo título)."""
    linea = linea.strip()
    if not linea or len(linea) > 100:
        return False
    return bool(_CHAPTER_RE.match(linea))


def detectar_capitulos(paginas):
    """Detecta capítulos reales por página (1-based). NO inventa capítulos:
    exige encabezados reconocibles al inicio de una línea, en la parte alta de
    la página o tras una línea vacía (layout típico de inicio de capítulo)."""
    capitulos = []
    for idx, texto in enumerate(paginas, start=1):
        lineas = texto.split("\n")
        for n_linea, linea in enumerate(lineas):
            if not _linea_es_encabezado(linea):
                continue
            precedida_vacio = n_linea > 0 and not lineas[n_linea - 1].strip()
            if n_linea <= 5 or precedida_vacio:
                capitulos.append({"page": idx, "title": linea.strip()})
                break
    return capitulos


def paginar_desde_contenido(content: str):
    """Fallback para libros sin PDF (p. ej. Gutenberg): genera páginas
    estimadas de ~PAGE_CHARS caracteres, sin perder contenido y sin dividir
    párrafos salvo que un párrafo exceda el tope. Nunca devuelve 0 páginas
    si existe contenido."""
    if not content or not content.strip():
        return []

    bloques = content.split("\n\n")
    paginas = []
    pagina_actual = []
    longitud_actual = 0

    def cerrar_pagina():
        nonlocal pagina_actual, longitud_actual
        if pagina_actual:
            paginas.append("\n\n".join(pagina_actual))
            pagina_actual = []
            longitud_actual = 0

    for bloque in bloques:
        if not bloque.strip():
            continue
        if longitud_actual + len(bloque) + 2 > PAGE_CHARS and pagina_actual:
            cerrar_pagina()
        if len(bloque) > PAGE_CHARS:
            cerrar_pagina()
            trozos = []
            resto = bloque
            while len(resto) > PAGE_CHARS:
                corte = resto.rfind(" ", 0, PAGE_CHARS)
                if corte == -1:
                    corte = PAGE_CHARS
                trozos.append(resto[:corte])
                resto = resto[corte:].lstrip()
            if resto:
                trozos.append(resto)
            for t in trozos:
                paginas.append(t)
            continue
        pagina_actual.append(bloque)
        longitud_actual += len(bloque) + 2

    cerrar_pagina()
    return paginas


def construir_estructura(paginas, capitulos=None):
    """Une páginas y capítulos: page_number 1..N, contenido por página y
    capítulo opcional persistente hasta el siguiente encabezado.
    No duplica ni pierde páginas."""
    capitulos = capitulos or []
    mapa = {c["page"]: c["title"] for c in capitulos}
    estructura = []
    cap_actual = None
    for i, texto in enumerate(paginas, start=1):
        if i in mapa:
            cap_actual = mapa[i]
        estructura.append(
            {"page_number": i, "content": texto, "chapter_title": cap_actual}
        )
    return estructura