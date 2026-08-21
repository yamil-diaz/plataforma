# -*- coding: utf-8 -*-
"""
diag_catalog.py — DIAGNÓSTICO READ-ONLY DEL CATÁLOGO (PASO 4) + VERIFICACIÓN
FÍSICA DE PDFs (PASO APROBADO: diagnóstico físico de producción).

Clasificación ACTUAL (esquema previo):
  SALVAR / SALVAR_REPROCESANDO / REPROCESAR / REVISAR / ELIMINAR

Clasificación FINAL preliminar (esquema aprobado):
  SALVAR
  REPROCESAR_DESDE_PDF          -> el PDF físico existe y es fuente utilizable.
  REPROCESAR_DESDE_CONTENIDO    -> sin PDF utilizable, pero books.content (o
                                   seed_books.py en el repo) es obra completa
                                   y confiable.
  REVISAR                       -> caso ambiguo o duplicado (no borrar).
  ELIMINAR                      -> irrecuperable: placeholder/fabricado sin
                                   ninguna fuente verificable.

En modo BD (producción) verifica FÍSICAMENTE cada pdf_path registrado:
  [ -f ] equivalente (os.path.isfile), tamaño (os.path.getsize), tipo real por
  magic bytes (%PDF) y extracción real de texto (procesar_contenido_para_publicacion).
  Un pdf_path registrado NUNCA se considera prueba de que el PDF existe.

SOLO LECTURA: conexión con default_transaction_read_only. Nunca INSERT/UPDATE/
DELETE. No borra, no repagina, no publica.

Modos:
  python diag_catalog.py                       # BD (requiere DATABASE_URL y STORAGE_DIR)
  python diag_catalog.py --snapshot diag_result.json   # analiza el snapshot guardado
  python diag_catalog.py --resumen             # solo conteos por clasificación
  python diag_catalog.py --libro 133           # detalle de un libro
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura

DATABASE_URL = os.getenv("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or os.path.join(BASE_DIR, "storage"))
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")

CLASIFICACIONES = ("SALVAR", "SALVAR_REPROCESANDO", "REPROCESAR", "REVISAR", "ELIMINAR")

CLASIFICACIONES_FINAL = (
    "SALVAR",
    "REPROCESAR_DESDE_PDF",
    "REPROCESAR_DESDE_CONTENIDO",
    "REVISAR",
    "ELIMINAR",
)

# En modo --snapshot no existe pdf_path por libro: la existencia física del
# PDF no puede verificarse y las decisiones que dependen de ella quedan
# marcadas como "verificación pendiente" en lugar de ELIMINAR.
SIN_INFO_PDF = False

# Libros 5-130: sembrados por seed_books.py (120 obras reales de dominio
# público con contenido original completo en el repo). El snapshot confirma
# el patrón fabricado (párrafo repetido 200 veces) y los títulos coinciden
# con seed_books.py. Su fuente verificable es seed_books.py (mismo repo).
RANGO_SEEDS = range(5, 131)


def _es_seed(book):
    return book["estado"].get("pathological") and book["id"] in RANGO_SEEDS


def _estado_contenido(content, paginas=None):
    """Estado de validación de un contenido (solo lectura)."""
    content = content or ""
    info = {
        "placeholder": content.strip() == lectura.CONTENIDO_NO_DISPONIBLE,
        "pathological": False,
        "basura": False,
        "vacío": not content.strip(),
    }
    if not info["placeholder"] and not info["vacío"]:
        info["pathological"] = lectura.detectar_contenido_patologico(content, paginas)["pathological"]
        info["basura"] = lectura._detectar_basura(content)
    validacion = lectura.validar_contenido_libro(content, paginas, fuente="diagnostico")
    info["errors"] = validacion["errors"]
    info["content_length"] = validacion["detalle"]["content_length"]
    info["short_content"] = validacion["detalle"]["short_content"]
    info["repetition_ratio"] = validacion["detalle"].get("repetition_ratio")
    return info


def clasificar(book, pdf_existe, duplicados_ids):
    """Clasificación final de un libro según contenido + fuente disponible."""
    info = book["estado"]
    libro_id = book["id"]
    fuente = None
    motivo = []

    if info["vacío"] or info["placeholder"]:
        if pdf_existe:
            return "REPROCESAR", "PDF", ["Contenido placeholder/vacío con PDF físico disponible"]
        if book["pdf_path"]:
            return "REVISAR", None, ["Contenido placeholder/vacío y pdf_path sin archivo físico"]
        if SIN_INFO_PDF:
            return "REPROCESAR", "PDF (verificación pendiente)", [
                "Contenido placeholder/vacío; verificar PDF físico (modo BD) "
                "antes de decidir. Sin PDF -> ELIMINAR."
            ]
        return "ELIMINAR", None, ["Contenido placeholder/vacío sin ninguna fuente"]

    if info["pathological"] or info["basura"]:
        if _es_seed(book):
            return "SALVAR_REPROCESANDO", "seed_books.py", [
                "Contenido sembrado (seed_books.py, obra real de dominio "
                "público verificable en el repo) con paginación patológica; "
                "reprocesar paginación/capítulos desde books.content"
            ]
        if pdf_existe:
            return "REPROCESAR", "PDF", ["Contenido fabricado/basura con PDF físico disponible"]
        if book["pdf_path"]:
            return "REVISAR", None, ["Contenido fabricado/basura y pdf_path sin archivo físico"]
        if SIN_INFO_PDF:
            return "REVISAR", None, [
                "Contenido contaminado (obra real con basura añadida o patrón "
                "de repetición); verificar PDF en modo BD -> REPROCESAR desde "
                "PDF, o limpiar books.content manualmente"
            ]
        return "ELIMINAR", None, ["Contenido fabricado/basura sin ninguna fuente"]

    if info["content_length"] is not None and info["content_length"] < lectura.MIN_CONTENIDO_TOTAL:
        if pdf_existe:
            return "REPROCESAR", "PDF", ["Contenido insuficiente con PDF físico disponible"]
        if book["pdf_path"]:
            return "REVISAR", None, ["Contenido insuficiente y pdf_path sin archivo físico"]
        return "ELIMINAR", None, ["Contenido insuficiente sin ninguna fuente"]

    # Contenido no vacío, no placeholder, no patológico, no basura y de
    # longitud razonable: contenido confiable.
    if info["errors"]:
        return "REVISAR", None, ["Contenido aparentemente válido con anomalías: " + "; ".join(info["errors"])]
    if libro_id in duplicados_ids:
        return "REVISAR", None, ["Contenido válido pero duplicado (verificar copia superior)"]
    if book["pdf_path"]:
        if pdf_existe:
            return "SALVAR_REPROCESANDO", "PDF", ["Contenido confiable; re-procesar desde PDF para paginación/capítulos reales"]
        return "REVISAR", None, ["Contenido confiable pero pdf_path sin archivo físico"]
    if not book["page_count"]:
        return "SALVAR_REPROCESANDO", "books.content", ["Contenido confiable sin paginar aún"]
    return "SALVAR", None, ["Contenido completo y confiable, paginado"]


def _resolver_pdf(book):
    pdf_path = book.get("pdf_path") or ""
    if not pdf_path:
        return None, False
    if os.path.isabs(pdf_path) and os.path.isfile(pdf_path):
        return pdf_path, True
    candidata = os.path.join(STORAGE_BOOKS, os.path.basename(pdf_path))
    return (candidata, True) if os.path.isfile(candidata) else (pdf_path, False)


def _info_pdf_fisico(book):
    """Verificación FÍSICA del PDF: [ -f ] + tamaño + tipo real (magic bytes).
    Un pdf_path registrado NO se considera prueba de existencia."""
    pdf_path = book.get("pdf_path") or ""
    if not pdf_path:
        return {"ruta": None, "existe": False, "tamano": None, "tipo": "SIN_PDF_PATH", "magic_pdf": False}
    ruta, existe = _resolver_pdf(book)
    if not existe:
        return {"ruta": ruta, "existe": False, "tamano": None, "tipo": "NO_EXISTE", "magic_pdf": False}
    tamano = None
    tipo = None
    magic_pdf = False
    try:
        tamano = os.path.getsize(ruta)
        with open(ruta, "rb") as f:
            cabecera = f.read(5)
        magic_pdf = cabecera.startswith(b"%PDF")
        ext = os.path.splitext(ruta)[1].lower() or "sin-ext"
        tipo = "PDF_MAGIC_OK" if magic_pdf else f"NO_MAGIC_PDF({ext})"
    except OSError as e:
        tipo = f"ERROR_LECTURA:{e}"
    return {"ruta": ruta, "existe": True, "tamano": tamano, "tipo": tipo, "magic_pdf": magic_pdf}


def _info_extraccion(pdf_path):
    """Extracción REAL de texto del PDF (solo lectura del archivo)."""
    try:
        procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf_path, fuente="pdf")
        validacion = procesado["validacion"]
        return {
            "ok": bool(validacion["valid"]),
            "longitud": validacion["detalle"].get("content_length"),
            "errores": validacion["errors"],
        }
    except Exception as e:
        return {"ok": False, "longitud": None, "errores": [f"Excepción al procesar PDF: {e}"]}


def _puntaje_copia_superior(book):
    """Heurística (no destructiva) de 'copia superior' en grupos duplicados."""
    score = 0
    if book["pdf_existe"]:
        score += 100
    if book["pdf_fisico"].get("tamano"):
        score += 10
    score += (book.get("page_count") or 0)
    score += (book.get("content_length") or 0) // 1000
    if book.get("published"):
        score += 50
    return score


def clasificar_final(book, duplicados_ids):
    """Clasificación FINAL preliminar según las 10 reglas aprobadas.

    Depende de la verificación física (book['pdf_fisico']) y de la validación
    real del contenido (book['estado']). Nunca escribe nada."""
    info = book["estado"]
    fisico = book["pdf_fisico"]
    extraccion = book["extraccion"]
    pdf_existe = fisico["existe"]
    libro_id = book["id"]
    es_seed = _es_seed(book)
    fuente = None
    motivo = []

    # Regla 7: duplicados exactos (mismo título+autor) -> REVISAR, nunca
    # eliminación automática; se indica la copia superior aparente.
    if libro_id in duplicados_ids:
        sup = book.get("copia_superior_id")
        detalle = f"; copia superior aparente: id {sup}" if sup and sup != libro_id else ""
        return "REVISAR", None, [
            "Duplicado exacto de título+autor (regla 7): no eliminar aún; "
            "elegir la copia superior manualmente" + detalle
        ]

    if pdf_existe:
        if extraccion["ok"]:
            # Regla 1: PDF existe, es válido y extrae texto correctamente.
            return "REPROCESAR_DESDE_PDF", "PDF", [
                f"PDF físico OK ({fisico['tamano']} bytes, {fisico['tipo']}); "
                f"extracción real OK ({extraccion['longitud']} chars) -> reprocesar desde el PDF"
            ]
        if info["placeholder"]:
            # Regla 3: placeholder + PDF físico existe -> reprocesar desde PDF.
            return "REPROCESAR_DESDE_PDF", "PDF", [
                f"PDF físico OK ({fisico['tamano']} bytes) pero sin capa de texto "
                "extraíble; reprocesar desde el PDF (puede requerir OCR/decisión)"
            ]
        if es_seed:
            # Regla 5: fuente verificable en el repo (seed_books.py) > PDF que no extrae.
            return "REPROCESAR_DESDE_CONTENIDO", "seed_books.py", [
                "PDF físico existe pero no extrae texto; fuente más confiable: "
                "seed_books.py (obra original en el repo)"
            ]
        if not info["pathological"] and not info["basura"] and not info["errors"]:
            # Regla 2: contenido ya confiable; el PDF no aporta más.
            return "REPROCESAR_DESDE_CONTENIDO", "books.content", [
                "Contenido confiable y PDF físico no extraíble; reprocesar desde books.content"
            ]
        if info["pathological"] or info["basura"]:
            # Regla 8 (145/158 y similares): PDF existe pero no reconstruye el contenido.
            return "REVISAR", "PDF (sin extracción)", [
                "Contenido contaminado y el PDF físico no extrae texto; "
                "requiere revisión manual (no eliminable sin más evidencia)"
            ]
        # Regla 4 salvedad: cualquier otro caso con PDF físico -> intentar desde PDF.
        return "REPROCESAR_DESDE_PDF", "PDF", [
            f"PDF físico OK ({fisico['tamano']} bytes); reprocesar desde el PDF"
        ]

    # ── Sin PDF físico ────────────────────────────────────────────────────────
    if es_seed:
        # Reglas 5 y 9: fabricado x200 pero con fuente real verificable en el repo.
        return "REPROCESAR_DESDE_CONTENIDO", "seed_books.py", [
            "Contenido sembrado (seed_books.py, obra real de dominio público "
            "verificable en el repo) con paginación patológica; reprocesar "
            "paginación/capítulos desde books.content"
        ]

    if info["placeholder"] or info["vacío"]:
        if SIN_INFO_PDF:
            # Sin información física no puede aplicarse la regla 4: falta
            # confirmar que el PDF NO existe (requiere modo BD).
            return "REVISAR", None, [
                "Contenido placeholder/vacío; verificación física del PDF "
                "pendiente (ejecutar en modo BD): sin PDF -> ELIMINAR (regla 4)"
            ]
        # Regla 4: placeholder y PDF NO existe -> ELIMINAR (salvo otra fuente
        # verificable, que no existe para estos).
        return "ELIMINAR", None, [
            "Contenido placeholder/vacío y sin PDF físico; sin otra fuente "
            "verificable (regla 4)"
        ]

    if info["pathological"] or info["basura"]:
        if SIN_INFO_PDF:
            # Sin verificación física no puede aplicarse la regla 6: falta
            # confirmar que no hay PDF ni otra fuente.
            return "REVISAR", None, [
                "Contenido fabricado/repetido; verificación física del PDF y de "
                "fuentes pendiente (modo BD): sin fuente -> ELIMINAR (regla 6)"
            ]
        ratio = info.get("repetition_ratio")
        if ratio is None or ratio < 0.9:
            # 145/158 y similares: obra real contaminada con basura añadida,
            # reconstruible. Regla 8: sin PDF físico -> REVISAR (no ELIMINAR).
            return "REVISAR", "books.content (requiere limpieza)", [
                "Contenido de obra real contaminado con repeticiones "
                f"(ratio duplicación {ratio}); sin PDF físico; limpiar "
                "books.content o conseguir PDF (regla 8)"
            ]
        # Regla 6: fabricado x200 (ratio ~100%) sin ninguna fuente recuperable.
        return "ELIMINAR", None, [
            "Contenido fabricado/repetido (ratio duplicación "
            f"{ratio}) sin PDF físico ni otra fuente verificable (regla 6)"
        ]

    if info["errors"]:
        return "REVISAR", None, [
            "Contenido con anomalías de validación: " + "; ".join(info["errors"])
        ]

    # Contenido completo y confiable (regla 2).
    paginas_ok = (book.get("n_book_pages") or 0) > 0 and (
        book.get("n_book_pages") == (book.get("page_count") or 0)
    )
    if not paginas_ok:
        return "REPROCESAR_DESDE_CONTENIDO", "books.content", [
            "Contenido completo y confiable pero paginación ausente/descuadrada; "
            "reprocesar paginación desde books.content (regla 2)"
        ]
    return "SALVAR", None, ["Contenido completo, confiable y paginado; sin acciones"]


def _clasificar_libros(libros, duplicados_ids):
    # 1) Verificación física barata de todos los PDFs (isfile/getsize/magic).
    for book in libros:
        ruta, existe = _resolver_pdf(book)
        book["pdf_path_resuelto"] = ruta
        book["pdf_existe"] = existe
        book["pdf_fisico"] = _info_pdf_fisico(book)
        book["extraccion"] = {"ok": False, "longitud": None, "errores": []}

    # 2) Copia superior aparente por grupo duplicado (regla 7, heurística).
    for book in libros:
        grupo = [b for b in libros if b["id"] in book.get("grupo_duplicados", [])]
        if len(grupo) > 1:
            mejor = max(grupo, key=_puntaje_copia_superior)
            book["copia_superior_id"] = mejor["id"]
        else:
            book["copia_superior_id"] = None

    # 3) Extracción real de texto (solo si el PDF existe) + clasificación.
    for book in libros:
        if book["pdf_existe"]:
            book["extraccion"] = _info_extraccion(book["pdf_path_resuelto"])
        book["clasificacion"], book["fuente"], book["motivo"] = clasificar(
            book, book["pdf_existe"], duplicados_ids
        )
        book["clasificacion_final"], book["fuente_final"], book["motivo_final"] = clasificar_final(
            book, duplicados_ids
        )
    return libros


def _reporte_json(libros, resumen_only=False, libro_id=None):
    for book in libros:
        if libro_id is not None and book["id"] != libro_id:
            continue
        entry = {
            "id": book["id"],
            "titulo": book.get("title", ""),
            "autor": book.get("author_name", ""),
            "published": book.get("published"),
            "page_count": book.get("page_count"),
            "content_length": book["estado"]["content_length"],
            "pdf_path": book.get("pdf_path"),
            "pdf_existe": book["pdf_existe"],
            "book_pages": book.get("n_book_pages"),
            "chapters": book.get("n_chapters"),
            "placeholder": book["estado"]["placeholder"],
            "pathological": book["estado"]["pathological"],
            "basura": book["estado"]["basura"],
            "errores_validacion": book["estado"]["errors"],
            "clasificacion": book["clasificacion"],
            "clasificacion_final": book["clasificacion_final"],
            "fuente": book["fuente_final"] or book["fuente"],
            "motivo": book["motivo_final"] or book["motivo"],
        }
        if not resumen_only:
            print(json.dumps(entry, ensure_ascii=False, default=str))
        else:
            print(f"- {entry['clasificacion_final']} id={entry['id']} '{entry['titulo']}'")
    if resumen_only:
        from collections import Counter

        conteos = Counter(b["clasificacion"] for b in libros)
        conteos_final = Counter(b["clasificacion_final"] for b in libros)
        print(
            json.dumps(
                {"resumen_actual": dict(conteos), "resumen_final": dict(conteos_final), "total": len(libros)},
                ensure_ascii=False,
                default=str,
            )
        )


def _celda(valor):
    """Convierte un valor para la tabla TSV, escapando tabuladores/nuevas líneas."""
    if valor is None:
        return ""
    texto = str(valor)
    return texto.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _reporte_completo(libros):
    """Informe completo de verificación física + clasificación FINAL (A-G)."""
    from collections import Counter

    print("=" * 100)
    print("A. VERIFICACIÓN FÍSICA DE PDFs (por libro, [ -f ] real + tamaño + tipo)")
    print("=" * 100)
    for b in libros:
        f = b["pdf_fisico"]
        ext = b["extraccion"]
        estado_extraccion = (
            f"OK({ext['longitud']} chars)" if ext["ok"] else ("NO(texto insuficiente)" if ext["errores"] else "NO(no aplica)")
        )
        print(
            "\t".join(
                _celda(v)
                for v in (
                    b["id"],
                    b.get("title", ""),
                    "YES" if f["existe"] else "NO",
                    f["ruta"] or "",
                    f["tamano"],
                    f["tipo"],
                    estado_extraccion,
                )
            )
        )

    print()
    print("=" * 100)
    print("B. TABLA COMPLETA: id|title|author|published|page_count|content_length|"
          "pdf_path|pdf_existe|pdf_size|pdf_tipo|book_pages|chapters|clasif_actual|"
          "clasif_final|fuente|accion")
    print("=" * 100)
    cabecera = [
        "id", "title", "author", "published", "page_count", "content_length",
        "pdf_path", "pdf_existe", "pdf_size", "pdf_tipo", "book_pages", "chapters",
        "clasif_actual", "clasif_final", "fuente", "accion",
    ]
    print("\t".join(cabecera))
    for b in libros:
        f = b["pdf_fisico"]
        accion = b["motivo_final"][0][:120] if b["motivo_final"] else ""
        print(
            "\t".join(
                _celda(v)
                for v in (
                    b["id"],
                    b.get("title", ""),
                    b.get("author_name", ""),
                    b.get("published"),
                    b.get("page_count"),
                    b["estado"].get("content_length") or b.get("content_length"),
                    b.get("pdf_path") or "",
                    "YES" if f["existe"] else "NO",
                    f["tamano"],
                    f["tipo"],
                    b.get("n_book_pages"),
                    b.get("n_chapters"),
                    b["clasificacion"],
                    b["clasificacion_final"],
                    b["fuente_final"] or "",
                    accion,
                )
            )
        )

    def _lista(etiqueta, clase):
        seleccion = [b for b in libros if b["clasificacion_final"] == clase]
        print()
        print(f"C/D/E. {etiqueta} ({len(seleccion)}):")
        for b in seleccion:
            motivo = (b["motivo_final"] or [""])[0][:160]
            print(f"  {etiqueta} id={b['id']} '{b.get('title', '')}' -> {motivo}")

    _lista("ELIMINAR", "ELIMINAR")
    _lista("REPROCESAR_DESDE_PDF", "REPROCESAR_DESDE_PDF")
    _lista("REPROCESAR_DESDE_CONTENIDO", "REPROCESAR_DESDE_CONTENIDO")
    _lista("REVISAR", "REVISAR")
    _lista("SALVAR", "SALVAR")

    print()
    print("=" * 100)
    print("F. EVIDENCIA")
    print("=" * 100)
    conteos_final = Counter(b["clasificacion_final"] for b in libros)
    conteos_actual = Counter(b["clasificacion"] for b in libros)
    print(f"Total libros: {len(libros)}")
    print(f"Clasificación actual : {dict(conteos_actual)}")
    print(f"Clasificación FINAL  : {dict(conteos_final)}")
    pdfs_registrados = sum(1 for b in libros if b.get("pdf_path"))
    pdfs_fisicos = sum(1 for b in libros if b["pdf_fisico"]["existe"])
    pdfs_sin_magic = [
        b["id"] for b in libros if b["pdf_fisico"]["existe"] and not b["pdf_fisico"]["magic_pdf"]
    ]
    print(
        f"pdf_path registrados: {pdfs_registrados} | existentes físicamente: {pdfs_fisicos} "
        f"| con magic %PDF: {pdfs_fisicos - len(pdfs_sin_magic)}"
    )
    if pdfs_sin_magic:
        print(f"PDFs existentes pero SIN magic bytes %PDF: {pdfs_sin_magic}")
    for b in libros:
        if b.get("grupo_duplicados") and len(b["grupo_duplicados"]) > 1:
            print(
                f"Grupo duplicado id={b['id']} '{b.get('title', '')}' "
                f"(grupo {b['grupo_duplicados']}, copia superior aparente id={b.get('copia_superior_id')})"
            )
    print()
    print("G. CONFIRMACIÓN")
    print("PRODUCCIÓN NO FUE MODIFICADA.")

    print()
    print("=" * 100)
    print("H. JSONL POR LIBRO (para el cruzamiento [ -f ] en bash)")
    print("=" * 100)
    for b in libros:
        print(
            json.dumps(
                {
                    "id": b["id"],
                    "pdf_path": b.get("pdf_path") or "",
                    "pdf_existe": b["pdf_fisico"]["existe"],
                    "pdf_size": b["pdf_fisico"]["tamano"],
                    "clasificacion_final": b["clasificacion_final"],
                },
                ensure_ascii=False,
                default=str,
            )
        )


def _desde_bd():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no definida (o usa --snapshot).")
    import psycopg2
    import psycopg2.extras

    url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(
        url,
        cursor_factory=psycopg2.extras.RealDictCursor,
        options="-c default_transaction_read_only=on",
    )
    conn.set_session(readonly=True, autocommit=False)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT b.id, b.title, b.author_name, b.published, b.page_count, b.content,
               b.pdf_path,
               (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) AS n_book_pages,
               (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) AS n_chapters
        FROM books b
        ORDER BY b.id
        """
    )
    libros = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT title, author_name, array_agg(id ORDER BY id) AS ids
        FROM books
        GROUP BY title, author_name
        HAVING count(*) > 1
        """
    )
    duplicados = set()
    grupos_duplicados = {}
    for r in cursor.fetchall():
        ids = list(r["ids"])
        duplicados.update(ids)
        clave = (r["title"] or "") + "|" + (r["author_name"] or "")
        grupos_duplicados.setdefault(clave, []).extend(ids)

    conn.rollback()
    conn.close()

    for book in libros:
        content = book["content"] or ""
        book["content_length"] = len(content)
        book["estado"] = _estado_contenido(content)
        clave = (book.get("title") or "") + "|" + (book.get("author_name") or "")
        book["grupo_duplicados"] = list(grupos_duplicados.get(clave, []))
    return libros, duplicados


def _desde_snapshot(ruta):
    """Analiza el snapshot guardado por diag_prod.py (solo lectura).
    El snapshot NO contiene pdf_path por libro: la existencia física del PDF
    debe confirmarse ejecutando diag_catalog.py en modo BD (Render shell)."""
    with open(ruta, "r", encoding="utf-16") as f:
        raw = f.read()
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError:
        with open(ruta, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

    diag = snapshot["diagnosis"]

    placeholder_ids = set()
    for row in diag.get("identical_book_content", []):
        if row["content"].strip() == lectura.CONTENIDO_NO_DISPONIBLE:
            placeholder_ids.update(row["ids"])

    fabricados = {}
    for row in diag.get("repeated_paragraphs", []):
        n = row["n"]
        if n >= 200:
            fabricados[row["book_id"]] = {"par": row["par"][:60], "n": n, "title": row["title"]}

    suspicious_ids = {r["id"] for r in diag.get("books_suspicious_content", [])}
    empty_or_placeholder_ids = {r["id"] for r in diag.get("books_empty_or_placeholder", [])}

    ids_conocidos = set()
    libros = {}
    for row in diag.get("page_count_vs_max_page", []):
        libros[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "page_count": row["page_count"],
            "max_page": row["max_page"],
        }
        ids_conocidos.add(row["id"])
    for row in diag.get("repeated_paragraphs", []):
        if row["book_id"] not in libros:
            libros[row["book_id"]] = {"id": row["book_id"], "title": row["title"], "page_count": None, "max_page": None}
        ids_conocidos.add(row["book_id"])
    for row in diag.get("identical_book_content", []):
        for i, bid in enumerate(row["ids"]):
            if bid not in libros:
                libros[bid] = {"id": bid, "title": row["titles"][i], "page_count": None, "max_page": None}
        ids_conocidos.update(row["ids"])
    for row in diag.get("books_suspicious_content", []):
        if row["id"] not in libros:
            libros[row["id"]] = {"id": row["id"], "title": row["title"], "page_count": None, "max_page": None}
        ids_conocidos.add(row["id"])

    duplicados = set()
    for row in diag.get("duplicate_title_author", []):
        duplicados.update(row["ids"])

    total_books = sum(r["n"] for r in diag.get("books_published_status", []))
    for bid in range(1, total_books + 1):
        if bid not in libros:
            libros[bid] = {"id": bid, "title": "(sin datos en snapshot)", "page_count": None, "max_page": None}
    libros = [libros[k] for k in sorted(libros)]

    for book in libros:
        bid = book["id"]
        book["author_name"] = ""
        book["published"] = None
        book["pdf_path"] = None
        book["n_book_pages"] = book["max_page"]
        book["n_chapters"] = None
        evidencia = []
        if bid in placeholder_ids:
            evidencia.append("content == placeholder exacto (identical_book_content)")
        if bid in fabricados:
            evidencia.append(
                f"párrafo repetido {fabricados[bid]['n']} veces "
                f"(repeated_paragraphs, muestra: {fabricados[bid]['par']!r})"
            )
        if bid in suspicious_ids:
            evidencia.append("content sospechoso (books_suspicious_content)")
        if bid in empty_or_placeholder_ids:
            evidencia.append("content vacío o placeholder (books_empty_or_placeholder)")
        book["evidencia"] = evidencia
        if bid in placeholder_ids:
            book["estado"] = {
                "placeholder": True, "pathological": False, "basura": False, "vacío": False,
                "errors": ["Contenido placeholder exacto (evidencia del snapshot)"],
                "content_length": None, "short_content": True,
            }
        elif bid in fabricados:
            book["estado"] = {
                "placeholder": False, "pathological": True, "basura": False, "vacío": False,
                "errors": ["Contenido fabricado (párrafo repetido 200 veces)"],
                "content_length": None, "short_content": False,
            }
        else:
            book["estado"] = {
                "placeholder": False, "pathological": False, "basura": False, "vacío": False,
                "errors": evidencia or ["Sin evidencia en el snapshot: requiere revisión manual"],
                "content_length": None, "short_content": None,
            }
    return libros, duplicados


def main():
    import sys as _sys
    _sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Diagnóstico READ-ONLY del catálogo.")
    parser.add_argument("--snapshot", help="Analizar un snapshot diag_result.json en lugar de la BD")
    parser.add_argument("--resumen", action="store_true", help="Solo conteos por clasificación")
    parser.add_argument("--libro", type=int, help="Detalle de un solo libro (id)")
    args = parser.parse_args()

    if args.snapshot:
        global SIN_INFO_PDF
        SIN_INFO_PDF = True
        libros, duplicados = _desde_snapshot(args.snapshot)
        print(f"# Análisis desde snapshot: {args.snapshot} (sin conexión a BD)", file=sys.stderr)
    else:
        libros, duplicados = _desde_bd()
        print("# Análisis desde BD en modo READ-ONLY (verificación física de PDFs incluida)", file=sys.stderr)

    libros = _clasificar_libros(libros, duplicados)

    if args.snapshot:
        _reporte_json(libros, resumen_only=args.resumen, libro_id=args.libro)
    else:
        if args.resumen:
            _reporte_json(libros, resumen_only=True, libro_id=args.libro)
        elif args.libro is not None:
            _reporte_json(libros, resumen_only=False, libro_id=args.libro)
        else:
            _reporte_completo(libros)


if __name__ == "__main__":
    main()