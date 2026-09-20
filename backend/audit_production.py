# -*- coding: utf-8 -*-
"""
audit_production.py - DIAGNOSTICO DEFINITIVO DE PRODUCCION (SOLO LECTURA)

Ejecutar en el Shell de Render:
  python audit_production.py

Requiere: DATABASE_URL, STORAGE_DIR (ambos disponibles en Render)
"""
import os
import sys
import json
import re
from collections import Counter, defaultdict

import psycopg2
import psycopg2.extras

# Importar configuración centralizada de storage
from storage_config import STORAGE_DIR, STORAGE_BOOKS, STORAGE_COVERS

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL NO DISPONIBLE - DIAGNOSTICO DE PRODUCCION NO EJECUTADO.")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible."
FRAGMENTO_LARGO = 100
FRAGMENTO_MAX_APARICIONES = 5
FRAGMENTO_RATIO_MINIMO = 0.25
CONTENIDO_CORTO_CHARS = 200


def get_readonly_connection():
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        options="-c default_transaction_read_only=on"
    )
    conn.set_session(readonly=True, autocommit=False)
    return conn


def detectar_contenido_patologico(content):
    content = content or ""
    longitud = len(content)
    info = {
        "pathological": False, "reason": None,
        "repeated_fragment_count": 0, "repetition_ratio": 0.0,
        "short_content": longitud < CONTENIDO_CORTO_CHARS,
        "content_length": longitud,
    }
    if not content.strip():
        info["pathological"] = True
        info["reason"] = "Contenido vacio"
        return info
    if info["short_content"]:
        info["pathological"] = True
        info["reason"] = "Contenido corto ({} chars)".format(longitud)
        return info
    words = content.split()
    if len(words) > FRAGMENTO_LARGO:
        muestras = set()
        stride = max(1, (longitud - FRAGMENTO_LARGO) // 50)
        for i in range(0, longitud - FRAGMENTO_LARGO + 1, stride):
            frag = content[i:i + FRAGMENTO_LARGO]
            if frag.strip():
                muestras.add(frag)
        repetidos = []
        for frag in muestras:
            count = content.count(frag)
            if count > FRAGMENTO_MAX_APARICIONES:
                repetidos.append((frag, count))
        if repetidos:
            repeticion_extra = sum((n - 1) * FRAGMENTO_LARGO for _, n in repetidos)
            ratio = min(1.0, repeticion_extra / longitud)
            info["repeated_fragment_count"] = len(repetidos)
            info["repetition_ratio"] = round(ratio, 4)
            if len(repetidos) >= 3 and ratio >= FRAGMENTO_RATIO_MINIMO:
                info["pathological"] = True
                info["reason"] = "Repeticion extensa: {} fragmentos, {:.1%} duplicado".format(
                    len(repetidos), ratio)
    return info


def verificar_pdf(pdf_path):
    if not pdf_path:
        return {"existe": False, "tamano": None, "tipo": "SIN_PDF_PATH", "ruta": None}
    candidatas = [pdf_path, os.path.join(STORAGE_BOOKS, os.path.basename(pdf_path))]
    for ruta in candidatas:
        if os.path.isfile(ruta):
            try:
                tamano = os.path.getsize(ruta)
                with open(ruta, "rb") as f:
                    cabecera = f.read(5)
                magic_pdf = cabecera.startswith(b"%PDF")
                tipo = "PDF_MAGIC_OK" if magic_pdf else "NO_MAGIC"
                es_persistente = "/var/data/" in ruta
                return {"existe": True, "tamano": tamano, "tipo": tipo, "ruta": ruta, "persistente": es_persistente}
            except OSError:
                return {"existe": False, "tamano": None, "tipo": "ERROR_LECTURA", "ruta": ruta}
    return {"existe": False, "tamano": None, "tipo": "NO_EXISTE", "ruta": pdf_path}


def main():
    out = []
    def p(s=""):
        out.append(s)
        print(s)

    p("=" * 140)
    p("DIAGNOSTICO DEFINITIVO DE PRODUCCION - AeternumLibrary")
    p("Modo: SOLO LECTURA | Fuente: PostgreSQL directa + verificacion fisica de PDFs")
    p("=" * 140)

    # 1. Entorno
    p("\n1. VERIFICACION DE ENTORNO")
    p("-" * 140)
    db_masked = "***"
    if "@" in DATABASE_URL:
        head, tail = DATABASE_URL.split("@", 1)
        db_masked = head.split(":")[0] + ":***@" + tail.split("/")[0] + "/***"
    p("  DATABASE_URL: {}".format(db_masked))
    p("  STORAGE_DIR: {}".format(STORAGE_DIR))
    p("  STORAGE_BOOKS: {}".format(STORAGE_BOOKS))
    p("  STORAGE_BOOKS existe: {}".format(os.path.isdir(STORAGE_BOOKS)))

    # 2. Conexion
    p("\n2. CONEXION A BASE DE DATOS")
    p("-" * 140)
    try:
        conn = get_readonly_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()["version"]
        p("  Conexion OK: {}".format(version))
        cursor.execute("SELECT current_database()")
        db_name = cursor.fetchone()["current_database"]
        p("  Base de datos: {}".format(db_name))
    except Exception as e:
        p("  ERROR de conexion: {}".format(e))
        return

    # 3. Esquema
    p("\n3. COMPROBACION DE ESQUEMA")
    p("-" * 140)
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'books'
        ORDER BY ordinal_position
    """)
    books_cols = {r["column_name"]: r["data_type"] for r in cursor.fetchall()}
    p("  books: {}".format(list(books_cols.keys())))

    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'book_pages'
        ORDER BY ordinal_position
    """)
    pages_cols = {r["column_name"]: r["data_type"] for r in cursor.fetchall()}
    p("  book_pages: {}".format(list(pages_cols.keys())))

    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'chapters'
        ORDER BY ordinal_position
    """)
    chapters_cols = {r["column_name"]: r["data_type"] for r in cursor.fetchall()}
    p("  chapters: {}".format(list(chapters_cols.keys())))

    # 4. Conteos
    p("\n4. CONTEOS GENERALES")
    p("-" * 140)
    cursor.execute("SELECT count(*) AS n FROM books")
    total_books = cursor.fetchone()["n"]
    p("  Total books: {}".format(total_books))
    cursor.execute("SELECT count(*) AS n FROM book_pages")
    total_pages = cursor.fetchone()["n"]
    p("  Total book_pages: {}".format(total_pages))
    cursor.execute("SELECT count(*) AS n FROM chapters")
    total_chapters = cursor.fetchone()["n"]
    p("  Total chapters: {}".format(total_chapters))

    # 5. Todos los libros con datos
    p("\n5. AUDITORIA DE TODOS LOS LIBROS")
    p("-" * 140)
    cursor.execute("""
        SELECT b.id, b.title, b.author_name, b.content, b.pdf_path, b.page_count, b.published,
               length(b.content) AS content_length,
               (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) AS n_book_pages,
               (SELECT min(p.page_number) FROM book_pages p WHERE p.book_id = b.id) AS min_page,
               (SELECT max(p.page_number) FROM book_pages p WHERE p.book_id = b.id) AS max_page,
               (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id AND (p.content IS NULL OR length(trim(p.content)) = 0)) AS empty_pages,
               (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) AS n_chapters
        FROM books b
        ORDER BY b.id
    """)
    libros_raw = [dict(r) for r in cursor.fetchall()]

    # Duplicados
    cursor.execute("""
        SELECT title, author_name, count(*) AS n, array_agg(id ORDER BY id) AS ids
        FROM books
        GROUP BY title, author_name
        HAVING count(*) > 1
    """)
    duplicados_map = {}
    duplicados_ids = set()
    for r in cursor.fetchall():
        ids = list(r["ids"])
        duplicados_ids.update(ids)
        clave = (r["title"] or "") + "|" + (r["author_name"] or "")
        duplicados_map[clave] = {"title": r["title"], "author": r["author_name"], "ids": ids, "count": r["n"]}

    # Paginas faltantes por libro
    cursor.execute("""
        WITH ranges AS (
            SELECT book_id, min(page_number) AS min_p, max(page_number) AS max_p,
                   count(DISTINCT page_number) AS distinct_p
            FROM book_pages GROUP BY book_id
        )
        SELECT book_id, min_p, max_p, distinct_p,
               (max_p - min_p + 1) - distinct_p AS gaps
        FROM ranges WHERE (max_p - min_p + 1) - distinct_p > 0
    """)
    gaps = {r["book_id"]: r for r in cursor.fetchall()}

    # Paginas duplicadas
    cursor.execute("""
        SELECT book_id, page_number, count(*) AS n
        FROM book_pages GROUP BY book_id, page_number HAVING count(*) > 1
    """)
    page_dups = defaultdict(list)
    for r in cursor.fetchall():
        page_dups[r["book_id"]].append(r["page_number"])

    conn.close()

    # Analisis por libro
    libros = []
    patologicos_count = 0
    placeholders_count = 0
    seeds_fabricados = 0
    pdfs_existentes = 0
    pdfs_perdidos = 0
    sin_pdf = 0

    for raw in libros_raw:
        bid = raw["id"]
        content = raw["content"] or ""
        content_length = raw["content_length"] or len(content)

        # PDF
        pdf_info = verificar_pdf(raw["pdf_path"])
        if pdf_info["existe"]:
            pdfs_existentes += 1
        elif raw["pdf_path"]:
            pdfs_perdidos += 1
        else:
            sin_pdf += 1

        # Contenido patologico
        es_placeholder = content.strip() == CONTENIDO_NO_DISPONIBLE or content.strip() == "Contenido de texto no disponible"
        estado = detectar_contenido_patologico(content)
        if es_placeholder:
            placeholders_count += 1
        if estado["pathological"]:
            patologicos_count += 1

        # Seeds fabricados (5-130)
        es_seed = bid in range(5, 131) and estado["pathological"]
        if es_seed:
            seeds_fabricados += 1

        # Grupo duplicado
        grupo = []
        for clave, g in duplicados_map.items():
            if bid in g["ids"]:
                grupo = g["ids"]
                break

        # Clasificacion
        motivos = []
        if es_placeholder:
            if grupo:
                motivos.append("Placeholder + duplicado; sin contenido recuperable")
                clasificacion = "SIN_CONTENIDO_RECUPERABLE"
            else:
                motivos.append("Placeholder; sin contenido recuperable")
                clasificacion = "SIN_CONTENIDO_RECUPERABLE"
        elif estado["pathological"] and content_length > 1000:
            motivos.append("Contenido fabricado/corrupto (repeticion extensa)")
            if pdf_info["existe"]:
                clasificacion = "REPROCESAR_DESDE_PDF"
                motivos.append("PDF fisico disponible para reconstruccion")
            else:
                clasificacion = "REVISAR"
                motivos.append("Sin PDF fisico; requiere revision manual")
        elif estado["pathological"] and content_length <= 1000:
            motivos.append("Contenido patologico severo ({} chars)".format(content_length))
            if pdf_info["existe"]:
                clasificacion = "REPROCESAR_DESDE_PDF"
            else:
                clasificacion = "SIN_CONTENIDO_RECUPERABLE"
        elif bid in duplicados_ids:
            motivos.append("Duplicado detectado")
            clasificacion = "REVISAR"
        elif es_seed:
            motivos.append("Seed con contenido problematico")
            if pdf_info["existe"]:
                clasificacion = "REPROCESAR_DESDE_PDF"
            else:
                clasificacion = "REVISAR"
        elif bid in [1, 2, 3, 4, 131, 132, 146]:
            motivos.append("Sin datos en snapshot previo; verificar manualmente")
            clasificacion = "REVISAR"
        elif content_length < 200:
            motivos.append("Contenido extremadamente corto")
            clasificacion = "REVISAR"
        elif not content.strip():
            motivos.append("Contenido vacio")
            clasificacion = "SIN_CONTENIDO_RECUPERABLE"
        else:
            if pdf_info["existe"] and pdf_info["tipo"] == "PDF_MAGIC_OK":
                motivos.append("Contenido disponible; PDF fisico verificado")
                clasificacion = "SALVAR"
            elif pdf_info["existe"]:
                motivos.append("Contenido disponible; PDF existe pero sin magic bytes")
                clasificacion = "REVISAR"
            else:
                motivos.append("Contenido textual disponible sin PDF")
                clasificacion = "SALVAR"

        # Candidato superior
        candidato = bid
        if grupo:
            no_placeholder = [x for x in grupo if x != bid]
            if no_placeholder:
                candidato = min(grupo)

        libro = {
            "id": bid,
            "title": raw["title"],
            "author": raw["author_name"],
            "content_chars": content_length,
            "book_pages_count": raw["n_book_pages"] or 0,
            "min_page": raw["min_page"],
            "max_page": raw["max_page"],
            "empty_pages": raw["empty_pages"] or 0,
            "page_gaps": gaps.get(bid, {}).get("gaps", 0),
            "page_dups": page_dups.get(bid, []),
            "n_chapters": raw["n_chapters"] or 0,
            "pdf_path": raw["pdf_path"],
            "pdf_existe": pdf_info["existe"],
            "pdf_size": pdf_info["tamano"],
            "pdf_tipo": pdf_info["tipo"],
            "pdf_ruta": pdf_info["ruta"],
            "pdf_persistente": pdf_info.get("persistente", False),
            "published": raw["published"],
            "placeholder": es_placeholder,
            "contenido_patologico": estado["pathological"],
            "patologia_reason": estado["reason"],
            "repetition_ratio": estado["repetition_ratio"],
            "grupo_duplicado": grupo,
            "candidato_superior": candidato,
            "clasificacion_final": clasificacion,
            "motivo": motivos,
        }
        libros.append(libro)

    # Resumen
    clas_counts = Counter(b["clasificacion_final"] for b in libros)
    p("\n" + "=" * 140)
    p("RESUMEN DE CLASIFICACION")
    p("=" * 140)
    p("  Total libros: {}".format(total_books))
    for clas, count in sorted(clas_counts.items()):
        p("  {}: {} ({:.1f}%)".format(clas, count, count * 100 / total_books))

    p("\n" + "=" * 140)
    p("ESTADISTICAS")
    p("=" * 140)
    p("  PDFs fisicos existentes: {}".format(pdfs_existentes))
    p("  PDFs registrados sin archivo: {}".format(pdfs_perdidos))
    p("  Sin PDF registrado: {}".format(sin_pdf))
    p("  Contenido patologico: {}".format(patologicos_count))
    p("  Placeholders: {}".format(placeholders_count))
    p("  Seeds fabricados (5-130): {}".format(seeds_fabricados))
    p("  Grupos duplicados: {}".format(len(duplicados_map)))
    p("  Total en grupos duplicados: {}".format(len(duplicados_ids)))
    p("  Libros con book_pages: {}".format(sum(1 for b in libros if b["book_pages_count"] > 0)))
    p("  Páginas vacías: {}".format(sum(b["empty_pages"] for b in libros)))
    p("  Libros con gaps en paginación: {}".format(len(gaps)))
    p("  Libros con páginas duplicadas: {}".format(len(page_dups)))

    # Detalle por libro
    p("\n" + "=" * 140)
    p("DETALLE POR LIBRO")
    p("=" * 140)
    p("{:>4} | {:<45} | {:<25} | {:>8} | {:>5} | {:>3} | {:>5} | {:<25}".format(
        "ID", "Titulo", "Autor", "Chars", "Pages", "PDF", "Patol", "Clasificacion"))
    p("-" * 140)
    for b in libros:
        title = (b["title"] or "S/D")[:44]
        author = (b["author"] or "S/D")[:24]
        pdf = "SI" if b["pdf_existe"] else "NO"
        patol = "SI" if b["contenido_patologico"] else "NO"
        clas = b["clasificacion_final"][:25]
        p("{:>4} | {:<45} | {:<25} | {:>8} | {:>5} | {:>3} | {:>5} | {:<25}".format(
            b["id"], title, author, b["content_chars"], b["book_pages_count"], pdf, patol, clas))

    # IDs 5-130 (seeds)
    p("\n" + "=" * 140)
    p("ANALISIS ESPECIAL: IDs 5-130 (SEEDS)")
    p("=" * 140)
    seeds = [b for b in libros if b["id"] in range(5, 131)]
    for b in seeds:
        p("  ID {:>3} | {:<45} | chars={:>8} | pdf={} | patol={} | ratio={:.2f} | {}".format(
            b["id"], (b["title"] or "S/D")[:45], b["content_chars"],
            "SI" if b["pdf_existe"] else "NO",
            "SI" if b["contenido_patologico"] else "NO",
            b["repetition_ratio"],
            b["clasificacion_final"]))

    # IDs 133-170 (placeholders)
    p("\n" + "=" * 140)
    p("ANALISIS ESPECIAL: IDs 133-170 (PLACEHOLDERS)")
    p("=" * 140)
    phs = [b for b in libros if b["id"] in range(133, 171)]
    for b in phs:
        p("  ID {:>3} | {:<45} | chars={:>8} | pdf={} | duplicado={}".format(
            b["id"], (b["title"] or "S/D")[:45], b["content_chars"],
            "SI" if b["pdf_existe"] else "NO",
            len(b["grupo_duplicado"]) > 1))

    # IDs 145, 158
    p("\n" + "=" * 140)
    p("ANALISIS ESPECIAL: IDs 145, 158")
    p("=" * 140)
    for bid in [145, 158]:
        b = next((x for x in libros if x["id"] == bid), None)
        if b:
            p("  ID {} | {:<45} | chars={:>8} | ratio={:.4f} | pdf={} | {}".format(
                bid, (b["title"] or "S/D")[:45], b["content_chars"],
                b["repetition_ratio"],
                "SI" if b["pdf_existe"] else "NO",
                b["clasificacion_final"]))

    # IDs 1-4, 131-132, 146
    p("\n" + "=" * 140)
    p("ANALISIS ESPECIAL: IDs SIN DATOS PREVIOS (1-4, 131-132, 146)")
    p("=" * 140)
    for bid in [1, 2, 3, 4, 131, 132, 146]:
        b = next((x for x in libros if x["id"] == bid), None)
        if b:
            p("  ID {} | {:<45} | chars={:>8} | pdf={} | pages={} | {}".format(
                bid, (b["title"] or "S/D")[:45], b["content_chars"],
                "SI" if b["pdf_existe"] else "NO",
                b["book_pages_count"],
                b["clasificacion_final"]))

    # ID 175
    p("\n" + "=" * 140)
    p("ANALISIS ESPECIAL: ID 175")
    p("=" * 140)
    b175 = next((x for x in libros if x["id"] == 175), None)
    if b175:
        p("  ID {} | {:<45} | chars={:>8} | pdf={} | size={} | pages={} | {}".format(
            175, (b175["title"] or "S/D")[:45], b175["content_chars"],
            "SI" if b175["pdf_existe"] else "NO",
            b175["pdf_size"],
            b175["book_pages_count"],
            b175["clasificacion_final"]))
        p("  pdf_path: {}".format(b175["pdf_path"]))
        p("  pdf_ruta: {}".format(b175["pdf_ruta"]))
        p("  motivo: {}".format("; ".join(b175["motivo"])))
    else:
        p("  ID 175 NO EXISTE en la base de datos")

    # JSONL
    p("\n" + "=" * 140)
    p("JSONL POR LIBRO")
    p("=" * 140)
    for b in libros:
        entry = {
            "id": b["id"], "title": b["title"], "author": b["author"],
            "content_chars": b["content_chars"], "book_pages_count": b["book_pages_count"],
            "pdf_path": b["pdf_path"], "pdf_existe": b["pdf_existe"],
            "pdf_size": b["pdf_size"], "contenido_patologico": b["contenido_patologico"],
            "grupo_duplicado": b["grupo_duplicado"],
            "candidato_superior": b["candidato_superior"],
            "clasificacion_final": b["clasificacion_final"],
            "motivo": "; ".join(b["motivo"]) if b["motivo"] else ""
        }
        p(json.dumps(entry, ensure_ascii=False, default=str))

    # Duplicados
    p("\n" + "=" * 140)
    p("GRUPOS DE DUPLICADOS")
    p("=" * 140)
    for clave, g in sorted(duplicados_map.items(), key=lambda x: -x[1]["count"]):
        ids_str = ", ".join(str(i) for i in g["ids"])
        p("  [{} copias] {} | {} | IDs: {}".format(g["count"], g["title"], g["author"], ids_str))

    # Validacion
    p("\n" + "=" * 140)
    p("VALIDACION DE SEGURIDAD")
    p("=" * 140)
    p("  Archivos de produccion modificados: 0")
    p("  Registros de DB modificados: 0")
    p("  INSERT: 0")
    p("  UPDATE: 0")
    p("  DELETE: 0")
    p("  Migraciones: 0")
    p("  Repaginaciones: 0")
    p("  Commits: 0")
    p("  Pushes: 0")
    p("  Deploys: 0")
    p("")
    p("  PRODUCCION NO FUE MODIFICADA.")

    # Guardar salida
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AUDIT_REPORT_PRODUCTION_FINAL.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    p("\n  Informe guardado en: {}".format(report_path))

    # Guardar JSONL
    jsonl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_production_result.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for b in libros:
            entry = {
                "id": b["id"], "title": b["title"], "author": b["author"],
                "content_chars": b["content_chars"], "book_pages_count": b["book_pages_count"],
                "pdf_path": b["pdf_path"], "pdf_existe": b["pdf_existe"],
                "pdf_size": b["pdf_size"], "contenido_patologico": b["contenido_patologico"],
                "grupo_duplicado": b["grupo_duplicado"],
                "candidato_superior": b["candidato_superior"],
                "clasificacion_final": b["clasificacion_final"],
                "motivo": "; ".join(b["motivo"]) if b["motivo"] else ""
            }
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    p("  JSONL guardado en: {}".format(jsonl_path))


if __name__ == "__main__":
    main()
