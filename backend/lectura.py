# -*- coding: utf-8 -*-
"""
backend/lectura.py — Lógica de lectura (FASE 2).
Port validado de lectura_pura.py (11/11 tests PASS en la fase de validación).
Extracción por páginas, detección de capítulos (no recompensan, solo organizan)
y paginación de respaldo para libros sin PDF.
"""
import re
from collections import Counter
from difflib import SequenceMatcher

PAGE_CHARS = 1800

# ── Detección de capítulos/secciones (conservadora: NUNCA inventa) ───────────
# Acepta encabezados reales al inicio de línea: CAP[ÍI]TULO / CAPITULO /
# CHAPTER / PARTE / ACTO / ESCENA + numeral (1, I, II..., PRIMERO, UNO, ONE,
# FIRST...) y encabezados tipo "PRIMERA NOCHE", "SEGUNDA PARTE" (ordinal +
# noche/día/mañana/tarde/parte). Un número aislado nunca es un capítulo.
_MARCADOR_SECCION = r"cap[ií]tulo|capitulo|chapter|parte|acto|escena"
_NUMERAL_SECCION = (
    r"\d{1,3}|[ivxlcdm]+|"
    r"primero|primera|segundo|segunda|tercero|tercera|cuarto|cuarta|quinto|quinta|"
    r"sexto|s[eé]ptimo|octavo|noveno|d[eé]cimo|"
    r"uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|first|second|third"
)
_CHAPTER_RE = re.compile(
    r"^\s*(?:" + _MARCADOR_SECCION + r")\s+"
    r"(?:n[uú]mero\s+|n[uú]m\.\s*)?"
    r"(?:" + _NUMERAL_SECCION + r")\b"
    r"(?:\s*(?:[:.\-\u2013]\s*)?(?P<title>[^\n]{0,60}))?$",
    re.IGNORECASE | re.UNICODE,
)
# Encabezados "PRIMERA NOCHE" / "SEGUNDA PARTE" sin marcador previo.
_NOCHE_RE = re.compile(
    r"^\s*(?:primera|segunda|tercera|cuarta|quinta|sexta|s[eé]ptima|octava|novena|d[eé]cima)\s+"
    r"(?:noche|noches|d[ií]a|d[ií]as|ma[nñ]ana|tarde|parte)\b"
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


class PDFSinTextoExtraible(Exception):
    """Excepción para PDFs que no tienen capa de texto extraíble."""
    pass


def extraer_contenido_libro(pdf_path: str):
    """Extrae el contenido completo de un PDF junto con sus páginas y capítulos.

    Comportamiento:
    - PDF con capa de texto: content = texto completo, páginas reales.
    - PDF sin capa de texto (texto vacío o solo espacios): lanza PDFSinTextoExtraible.
    - Error de extracción: lanza la excepción original.
    Devuelve (content, paginas, capitulos)."""
    try:
        paginas = extraer_paginas(pdf_path)
        capitulos = detectar_capitulos(paginas)
        texto = "\n".join(paginas)
        if not texto.strip():
            raise PDFSinTextoExtraible("El PDF no contiene texto extraíble (posiblemente escaneado o protegido)")
        content = texto
    except PDFSinTextoExtraible:
        raise
    except Exception as e:
        raise PDFSinTextoExtraible(f"Error extrayendo texto del PDF: {e}") from e
    return content, paginas, capitulos


def _linea_es_encabezado(linea: str) -> bool:
    """True si la línea es un encabezado de capítulo y es corta (estilo título)."""
    linea = linea.strip()
    if not linea or len(linea) > 100:
        return False
    return bool(_CHAPTER_RE.match(linea) or _NOCHE_RE.match(linea))


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


def paginar_desde_contenido(content: str, deduplicate: bool = False):
    """Fallback para libros sin PDF (p. ej. Gutenberg): genera páginas
    estimadas de ~PAGE_CHARS caracteres, sin perder contenido y sin dividir
    párrafos salvo que un párrafo exceda el tope. Nunca devuelve 0 páginas
    si existe contenido.

    Si deduplicate=True (solo para reparaciones administrativas), elimina
    bloques consecutivos idénticos para evitar páginas duplicadas cuando el
    contenido origen tiene párrafos repetidos (corrupción de datos).
    En flujo normal (deduplicate=False) se conserva TODO el contenido."""
    if not content or not content.strip():
        return []

    bloques = content.split("\n\n")
    paginas = []
    pagina_actual = []
    longitud_actual = 0
    prev_bloque_stripped = None
    bloques_eliminados = 0

    def cerrar_pagina():
        nonlocal pagina_actual, longitud_actual
        if pagina_actual:
            paginas.append("\n\n".join(pagina_actual))
            pagina_actual = []
            longitud_actual = 0

    for bloque in bloques:
        if not bloque.strip():
            continue
        stripped = bloque.strip()
        if deduplicate and prev_bloque_stripped is not None and stripped == prev_bloque_stripped:
            bloques_eliminados += 1
            continue
        prev_bloque_stripped = stripped

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


def paginar_desde_contenido_con_capitulos(content: str, deduplicate: bool = False):
    """Pagina libros sin PDF desde su contenido textual y detecta capítulos
    sobre las páginas generadas (misma regla que los PDF: encabezados
    reconocibles). Nunca inventa capítulos: si no hay encabezados válidos,
    capitulos = []. Devuelve (paginas, capitulos)."""
    paginas = paginar_desde_contenido(content, deduplicate=deduplicate)
    capitulos = detectar_capitulos(paginas)
    return paginas, capitulos


def extraer_paginas_pdf(pdf_path: str):
    """Extracción estricta para repaginación admin. Distingue:
    - PDF válido con capa de texto → (paginas, capitulos) reales.
    - PDF válido SIN capa de texto → lanza PDFSinTextoExtraible.
    - PDF corrupto/ilegible/no abrible → lanza la excepción."""
    paginas = extraer_paginas(pdf_path)
    capitulos = detectar_capitulos(paginas)
    texto = "\n".join(paginas)
    if not texto.strip():
        raise PDFSinTextoExtraible("El PDF no contiene texto extraíble (posiblemente escaneado o protegido)")
    content = texto
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


# ── Validación central de contenido (PASO 3) ─────────────────────────────────
# Se aplica a TODOS los flujos que crean o repaginan libros (subida PDF, ZIP,
# Gutenberg, repaginación admin, migración). Un libro con contenido inválido
# NUNCA se publica ni se pagina: se rechaza con un error claro.
MIN_CONTENIDO_TOTAL = 300
MIN_PAGINA_CHARS = 50
MAX_PAGINAS_VACIAS_RATIO = 0.5
MAX_RACHA_CARACTER = 200
LINEA_REPETIDA_MAX_APARICIONES = 50


def _detectar_basura(content):
    """Detección de contenido degradado o basura de extracción:
    - Racha de MAX_RACHA_CARACTER caracteres idénticos consecutivos (basura
      de extracción embebida, p. ej. "ááá...á" tras el texto real).
    - Una misma línea (corta o larga) repetida más de
      LINEA_REPETIDA_MAX_APARICIONES veces (p. ej. 534 líneas "á").
    - Un único carácter (sin espacios) concentra >35% del texto.
    - Caracteres de control o de sustitución concentran >10%.
    - Más de 5 caracteres de sustitución (U+FFFD) en todo el texto.
    Devuelve True si el contenido parece basura no recuperable."""
    if not content or not content.strip():
        return False
    if re.search(r"(.)\1{%d}" % (MAX_RACHA_CARACTER - 1), content):
        return True
    conteo_lineas = Counter(
        linea.strip() for linea in content.splitlines() if linea.strip()
    )
    if conteo_lineas and conteo_lineas.most_common(1)[0][1] > LINEA_REPETIDA_MAX_APARICIONES:
        return True
    letras = [c for c in content if not c.isspace()]
    if not letras:
        return False
    mas_frecuente = Counter(letras).most_common(1)[0][1]
    if mas_frecuente / len(letras) > 0.35:
        return True
    sospechosos = sum(1 for c in letras if ord(c) < 32 or c == "\ufffd")
    if sospechosos / len(letras) > 0.10:
        return True
    return content.count("\ufffd") > 5


def validar_contenido_libro(content, paginas=None, fuente="pdf"):
    """Validación central ANTES de publicar o paginar (nunca publica basura).

    Reglas (sin umbral rígido de longitud: combina la estructura real con el
    tipo de fuente):
    1. Contenido vacío o solo espacios -> inválido.
    2. Contenido placeholder (extracción fallida) -> inválido.
    3. Contenido patológico (duplicación/fabricación masiva) -> inválido.
    4. Contenido degradado o basura de extracción -> inválido.
    5. Contenido insuficiente (< MIN_CONTENIDO_TOTAL caracteres) -> inválido.
    6. Páginas (si se entregan): no más de MAX_PAGINAS_VACIAS_RATIO vacías y,
       para fuente PDF, al menos una página con texto apreciable.

    Devuelve {"valid": bool, "errors": [str], "detalle": {...}} con toda la
    información de diagnóstico (placeholder, patológico, basura, longitud)."""
    content = content or ""
    errores = []
    detalle = {
        "pathological": False,
        "reason": None,
        "content_length": len(content),
        "short_content": len(content) < CONTENIDO_CORTO_CHARS,
        "es_placeholder": False,
        "es_basura": False,
        "minimo_contenido": MIN_CONTENIDO_TOTAL,
    }

    if not content.strip():
        errores.append("Contenido vacío o solo espacios")

    es_placeholder = content.strip() == CONTENIDO_NO_DISPONIBLE
    if es_placeholder:
        detalle["es_placeholder"] = True
        errores.append(
            "No se pudo extraer texto del documento (contenido no disponible)"
        )

    if not es_placeholder:
        diagnostico = detectar_contenido_patologico(content, paginas)
        detalle.update(
            {
                "pathological": diagnostico["pathological"],
                "reason": diagnostico["reason"],
                "repeated_fragment_count": diagnostico["repeated_fragment_count"],
                "repetition_ratio": diagnostico["repetition_ratio"],
                "duplicate_consecutive_pages": diagnostico["duplicate_consecutive_pages"],
                "near_duplicate_consecutive_pages": diagnostico["near_duplicate_consecutive_pages"],
            }
        )
        if diagnostico["pathological"]:
            errores.append(
                "Posible duplicación o corrupción del contenido: "
                + (diagnostico["reason"] or "repetición patológica")
            )

    if not errores:
        if _detectar_basura(content):
            detalle["es_basura"] = True
            errores.append("Contenido degradado o basura de extracción")
        elif len(content.strip()) < MIN_CONTENIDO_TOTAL:
            errores.append(
                f"Contenido insuficiente (menos de {MIN_CONTENIDO_TOTAL} caracteres)"
            )
        elif paginas is not None:
            if not paginas:
                errores.append("No se generó ninguna página a partir del contenido")
            else:
                vacias = sum(1 for p in paginas if not p.strip())
                if vacias / len(paginas) > MAX_PAGINAS_VACIAS_RATIO:
                    errores.append(
                        f"Demasiadas páginas vacías ({vacias}/{len(paginas)})"
                    )
                elif fuente == "pdf" and not any(
                    len(p.strip()) >= MIN_PAGINA_CHARS for p in paginas
                ):
                    errores.append(
                        "Extracción insuficiente: ninguna página alcanza "
                        f"{MIN_PAGINA_CHARS} caracteres"
                    )

    return {"valid": not errores, "errors": errores, "detalle": detalle}


def procesar_contenido_para_publicacion(pdf_path=None, content=None, fuente="pdf"):
    """Pipeline central de contenido: extracción -> capítulos -> validación.

    - Con pdf_path: extrae el PDF. Si no hay texto extraíble, devuelve validación fallida.
    - Sin pdf_path: pagina desde el contenido textual (Gutenberg, contenido
      previo) y valida.
    Devuelve {"content", "paginas", "capitulos", "validacion"}. El llamador
    decide: si validacion["valid"] es False, NO debe publicar ni paginar."""
    if pdf_path:
        try:
            content, paginas, capitulos = extraer_contenido_libro(pdf_path)
        except PDFSinTextoExtraible as e:
            # PDF sin texto extraíble -> contenido placeholder para validación (que fallará)
            content = CONTENIDO_NO_DISPONIBLE
            paginas = []
            capitulos = []
            validacion = validar_contenido_libro(content, paginas, fuente=fuente)
            return {
                "content": content,
                "paginas": paginas,
                "capitulos": capitulos,
                "validacion": validacion,
            }
    else:
        content = content or ""
        paginas, capitulos = paginar_desde_contenido_con_capitulos(content)
    validacion = validar_contenido_libro(content, paginas, fuente=fuente)
    return {
        "content": content,
        "paginas": paginas,
        "capitulos": capitulos,
        "validacion": validacion,
    }


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