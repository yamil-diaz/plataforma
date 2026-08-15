# -*- coding: utf-8 -*-
"""
backend/lectura.py — Lógica de lectura (FASE 2).
Port validado de lectura_pura.py (11/11 tests PASS en la fase de validación).
Extracción por páginas, detección de capítulos (no recompensan, solo organizan)
y paginación de respaldo para libros sin PDF.
"""
import re
from difflib import SequenceMatcher

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


CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible."


def extraer_contenido_libro(pdf_path: str):
    """Extrae el contenido completo de un PDF junto con sus páginas y capítulos.

    Comportamiento (equivalente al de ZIP/migración):
    - PDF con capa de texto: content = texto completo, páginas reales.
    - PDF sin capa de texto (texto vacío o solo espacios): content =
      CONTENIDO_NO_DISPONIBLE y una única página placeholder.
    - Error de extracción: mismo placeholder + página placeholder.
    Nunca devuelve páginas vacías.
    Devuelve (content, paginas, capitulos)."""
    content = CONTENIDO_NO_DISPONIBLE
    paginas = []
    capitulos = []
    try:
        paginas = extraer_paginas(pdf_path)
        capitulos = detectar_capitulos(paginas)
        texto = "\n".join(paginas)
        if texto.strip():
            content = texto
        else:
            paginas = []
            capitulos = []
    except Exception:
        paginas = []
        capitulos = []
    if not paginas:
        paginas = paginar_desde_contenido(content)
    return content, paginas, capitulos


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


def paginar_desde_contenido_con_capitulos(content: str):
    """Pagina libros sin PDF desde su contenido textual y detecta capítulos
    sobre las páginas generadas (misma regla que los PDF: encabezados
    reconocibles). Nunca inventa capítulos: si no hay encabezados válidos,
    capitulos = []. Devuelve (paginas, capitulos)."""
    paginas = paginar_desde_contenido(content)
    capitulos = detectar_capitulos(paginas)
    return paginas, capitulos


def extraer_paginas_pdf(pdf_path: str):
    """Extracción estricta para repaginación admin. Distingue:
    - PDF válido con capa de texto → (paginas, capitulos) reales.
    - PDF válido SIN capa de texto → placeholder + una única página (igual que
      el flujo de subida). NUNCA devuelve páginas vacías.
    - PDF corrupto/ilegible/no abrible → lanza la excepción (NO devuelve
      placeholder), para que el endpoint pueda rechazar sin tocar nada."""
    paginas = extraer_paginas(pdf_path)
    capitulos = detectar_capitulos(paginas)
    texto = "\n".join(paginas)
    if not texto.strip():
        paginas = paginar_desde_contenido(CONTENIDO_NO_DISPONIBLE)
        capitulos = []
    return paginas, capitulos


# ── Detector de contenido patológico ──────────────────────────────────────────
FRAGMENTO_LARGO = 60
FRAGMENTO_MAX_APARICIONES = 5
FRAGMENTO_MINIMO_REPETIDOS = 2
FRAGMENTO_RATIO_MINIMO = 0.25
MUESTRAS_MAXIMAS = 300
PAGINAS_PARECIDAS_MIN = 0.98
PARECIDAS_PARA_ALARMA = 2
CONTENIDO_CORTO_CHARS = 200


def _normalizar_para_comparar(texto: str) -> str:
    return " ".join(texto.split())


def detectar_contenido_patologico(content, paginas=None):
    """Detecta contenido posiblemente corrupto/duplicado ANTES de repaginar.

    Heurísticas (bajo índice de falsos positivos: el contenido legítimo con
    estribillos o frases breves repetidas NO se rechaza):
    1) Fragmentos de ~FRAGMENTO_LARGO caracteres: si varios fragmentos
       distintos aparecen > FRAGMENTO_MAX_APARICIONES veces Y la porción
       duplicada supera FRAGMENTO_RATIO_MINIMO del total → sospechoso.
    2) Páginas consecutivas idénticas o casi idénticas (>= PARECIDAS_PARA_ALARMA
       pares casi idénticos o 1 par idéntico) → sospechoso.

    Devuelve info con: pathological, reason, repeated_fragment_count,
    repetition_ratio, duplicate_consecutive_pages,
    near_duplicate_consecutive_pages, content_length, short_content."""
    content = content or ""
    longitud = len(content)
    info = {
        "pathological": False,
        "reason": None,
        "repeated_fragment_count": 0,
        "repetition_ratio": 0.0,
        "duplicate_consecutive_pages": 0,
        "near_duplicate_consecutive_pages": 0,
        "content_length": longitud,
        "short_content": longitud < CONTENIDO_CORTO_CHARS,
    }

    if not content.strip():
        info["pathological"] = True
        info["reason"] = "Contenido vacío o solo espacios"
        return info

    if paginas:
        normalizadas = [_normalizar_para_comparar(p) for p in paginas]
        for a, b in zip(normalizadas, normalizadas[1:]):
            if not a or not b:
                continue
            if a == b:
                info["duplicate_consecutive_pages"] += 1
            elif SequenceMatcher(None, a, b).ratio() >= PAGINAS_PARECIDAS_MIN:
                info["near_duplicate_consecutive_pages"] += 1

    muestras = set()
    ultima_posicion = max(longitud - FRAGMENTO_LARGO, 0)
    stride = max(1, ultima_posicion // MUESTRAS_MAXIMAS)
    for i in range(0, ultima_posicion + 1, stride):
        fragmento = content[i:i + FRAGMENTO_LARGO]
        if fragmento.strip():
            muestras.add(fragmento)

    repetidos = []
    for fragmento in muestras:
        apariciones = content.count(fragmento)
        if apariciones > FRAGMENTO_MAX_APARICIONES:
            repetidos.append((fragmento, apariciones))

    repeticion_extra = sum((n - 1) * FRAGMENTO_LARGO for _, n in repetidos)
    repeticion_ratio = min(1.0, repeticion_extra / longitud) if longitud else 0.0
    info["repeated_fragment_count"] = len(repetidos)
    info["repetition_ratio"] = round(repeticion_ratio, 4)

    if info["duplicate_consecutive_pages"] >= 1 or info["near_duplicate_consecutive_pages"] >= PARECIDAS_PARA_ALARMA:
        info["pathological"] = True
        info["reason"] = (
            f"Páginas consecutivas duplicadas o casi idénticas: "
            f"{info['duplicate_consecutive_pages']} pares idénticos, "
            f"{info['near_duplicate_consecutive_pages']} pares casi idénticos"
        )
    elif info["repeated_fragment_count"] >= FRAGMENTO_MINIMO_REPETIDOS and repeticion_ratio >= FRAGMENTO_RATIO_MINIMO:
        info["pathological"] = True
        info["reason"] = (
            f"Repetición extensa de fragmentos: {info['repeated_fragment_count']} "
            f"fragmentos distintos repetidos más de {FRAGMENTO_MAX_APARICIONES} veces, "
            f"{repeticion_ratio:.1%} del contenido duplicado"
        )
    return info


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