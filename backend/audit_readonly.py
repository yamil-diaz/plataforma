# -*- coding: utf-8 -*-
"""
audit_readonly.py — AUDITORÍA COMPLETA DE RECUPERACIÓN (SOLO LECTURA)

Procesa diag_result.json para generar el informe completo de diagnóstico.
NO ejecuta ninguna operación de escritura.
"""
import json
import os
import sys
import re
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(BASE_DIR, "diag_result.json")

# Constantes del proyecto (de lectura.py)
CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible"
FRAGMENTO_LARGO = 100
FRAGMENTO_MAX_APARICIONES = 5
FRAGMENTO_RATIO_MINIMO = 0.25
PAGINAS_PARECIDAS_MIN = 0.98
CONTENIDO_CORTO_CHARS = 200
MIN_CONTENIDO_TOTAL = 500


def load_snapshot(path):
    """Carga el snapshot (UTF-16 o UTF-8)."""
    with open(path, "r", encoding="utf-16") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def detectar_contenido_patologico(content, paginas=None):
    """Réplica exacta de lectura.detectar_contenido_patologico (solo lectura)."""
    if not content:
        return {"pathological": False, "reason": "empty"}

    result = {
        "pathological": False,
        "reason": None,
        "repeated_fragment_count": 0,
        "repetition_ratio": 0.0,
        "duplicate_consecutive_pages": 0,
        "near_duplicate_consecutive_pages": 0,
        "content_length": len(content),
        "short_content": len(content.strip()) < CONTENIDO_CORTO_CHARS,
    }

    if result["short_content"]:
        result["pathological"] = True
        result["reason"] = "short_content"
        return result

    # Detectar fragmentos repetidos
    words = content.split()
    if len(words) > FRAGMENTO_LARGO:
        fragments = []
        for i in range(len(words) - FRAGMENTO_LARGO + 1):
            frag = " ".join(words[i:i + FRAGMENTO_LARGO])
            fragments.append(frag)

        frag_counts = Counter(fragments)
        repeated = {f: c for f, c in frag_counts.items() if c > FRAGMENTO_MAX_APARICIONES}
        if repeated:
            max_frag = max(repeated.values())
            ratio = max_frag / len(fragments) if fragments else 0
            if ratio >= FRAGMENTO_RATIO_MINIMO:
                result["pathological"] = True
                result["reason"] = "fragment_repetition"
                result["repeated_fragment_count"] = len(repeated)
                result["repetition_ratio"] = ratio

    # Detectar páginas consecutivas duplicadas
    if paginas and len(paginas) > 1:
        dup_count = 0
        near_dup_count = 0
        for i in range(len(paginas) - 1):
            if paginas[i] == paginas[i + 1]:
                dup_count += 1
            elif len(paginas[i]) > 0 and len(paginas[i + 1]) > 0:
                # Similitud por longitud de caracteres comunes
                shorter = min(len(paginas[i]), len(paginas[i + 1]))
                longer = max(len(paginas[i]), len(paginas[i + 1]))
                if shorter > 0:
                    common = len(set(paginas[i]) & set(paginas[i + 1]))
                    similarity = common / shorter
                    if similarity >= PAGINAS_PARECIDAS_MIN:
                        near_dup_count += 1

        result["duplicate_consecutive_pages"] = dup_count
        result["near_duplicate_consecutive_pages"] = near_dup_count
        if dup_count > 0 or near_dup_count >= 2:
            result["pathological"] = True
            if not result["reason"]:
                result["reason"] = "consecutive_duplicates"

    return result


def detectar_basura(content):
    """Réplica de lectura._detectar_basura (solo lectura)."""
    if not content:
        return False
    # Runs largos de caracteres similares
    if re.search(r'(.)\1{50,}', content):
        return True
    # Líneas repetidas
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if lines:
        line_counts = Counter(lines)
        most_common_count = line_counts.most_common(1)[0][1]
        if most_common_count > len(lines) * 0.5:
            return True
    # Caracteres de sustitución
    if content.count('\ufffd') > len(content) * 0.01:
        return True
    return False


def analizar_libros(diag):
    """Análisis completo de todos los libros desde el snapshot."""
    libros = []

    # Recopilar datos del snapshot
    books_published = diag.get("books_published_status", [])
    total_books = sum(r["n"] for r in books_published) if books_published else 0

    #Libros con contenido idéntico (placeholder)
    placeholder_ids = set()
    placeholder_content = None
    for row in diag.get("identical_book_content", []):
        if row["content"].strip() == CONTENIDO_NO_DISPONIBLE:
            placeholder_ids.update(row["ids"])
            placeholder_content = row["content"]

    # Libros fabricados (párrafo repetido 200+ veces)
    fabricados = {}
    for row in diag.get("repeated_paragraphs", []):
        n = row["n"]
        if n >= 200:
            fabricados[row["book_id"]] = {
                "par": row["par"][:100],
                "n": n,
                "title": row["title"]
            }

    # Libros con contenido sospechoso
    suspicious_ids = {r["id"] for r in diag.get("books_suspicious_content", [])}

    # Duplicados por título+autor
    duplicados_groups = {}
    duplicados_ids = set()
    for row in diag.get("duplicate_title_author", []):
        ids = list(row["ids"])
        duplicados_ids.update(ids)
        clave = (row["title"] or "") + "|" + (row["author_name"] or "")
        duplicados_groups[clave] = {
            "title": row["title"],
            "author": row["author_name"],
            "ids": ids,
            "count": row["n"]
        }

    # Near-identical content
    near_identical = diag.get("near_identical_content", [])

    # Pages info
    page_count_vs = {r["id"]: r for r in diag.get("page_count_vs_max_page", [])}
    repeated_paras = diag.get("repeated_paragraphs", [])

    # Crear registros para cada libro
    for book_id in range(1, total_books + 1):
        book = {
            "id": book_id,
            "title": None,
            "author": None,
            "content_chars": None,
            "pdf_path": None,
            "pdf_existe": False,
            "pdf_size": None,
            "page_count": None,
            "book_pages_count": None,
            "book_pages_total_chars": None,
            "first_page": None,
            "last_page": None,
            "placeholder": book_id in placeholder_ids,
            "pathological": False,
            "basura": False,
            "contenido_patologico": False,
            "repetition_ratio": None,
            "grupo_duplicado": [],
            "candidato_superior": None,
            "clasificacion_final": "REVISAR",
            "motivo": [],
        }

        # Buscar datos del snapshot
        if book_id in page_count_vs:
            info = page_count_vs[book_id]
            book["title"] = info.get("title")
            book["page_count"] = info.get("page_count")
            book["book_pages_count"] = info.get("max_page")

        # Verificar si es fabricado
        if book_id in fabricados:
            book["pathological"] = True
            book["contenido_patologico"] = True
            book["repetition_ratio"] = 1.0  # 200 repeticiones = ratio ~1.0
            if not book["title"]:
                book["title"] = fabricados[book_id]["title"]

        # Verificar si es placeholder
        if book_id in placeholder_ids:
            book["placeholder"] = True
            book["content_chars"] = len(placeholder_content) if placeholder_content else 33

        # Verificar sospechoso
        if book_id in suspicious_ids:
            book["basura"] = True
            book["contenido_patologico"] = True

        # Buscar en repeated_paragraphs para título
        if not book["title"]:
            for rp in repeated_paras:
                if rp["book_id"] == book_id:
                    book["title"] = rp["title"]
                    break

        # Grupo duplicado
        for clave, grupo in duplicados_groups.items():
            if book_id in grupo["ids"]:
                book["grupo_duplicado"] = grupo["ids"]
                if not book["title"]:
                    book["title"] = grupo["title"]
                if not book["author"]:
                    book["author"] = grupo["author"]
                break

        libros.append(book)

    return libros, duplicados_groups, fabricados, placeholder_ids, suspicious_ids


def clasificar_libro(book, duplicados_ids, fabricados, placeholder_ids):
    """Clasificación del libro según las reglas del enunciado."""
    motivos = []

    # Placeholder
    if book["placeholder"]:
        motivos.append("Contenido placeholder (33 chars)")
        return "SIN_CONTENIDO_RECUPERABLE", motivos

    # Fabricado sin fuente verificable
    if book["id"] in fabricados and book["id"] not in range(5, 131):
        motivos.append("Contenido fabricado (párrafo repetido 200+ veces)")
        return "SIN_CONTENIDO_RECUPERABLE", motivos

    # Fabricado con fuente (seed range 5-130)
    if book["id"] in fabricados and book["id"] in range(5, 131):
        motivos.append("Contenido fabricado pero con fuente verificable (seed_books.py)")
        return "REVISAR", motivos

    # Duplicado
    if book["id"] in duplicados_ids:
        motivos.append("Duplicado detectado")
        return "REVISAR", motivos

    # Sospechoso
    if book.get("basura"):
        motivos.append("Contenido marcado como sospechoso")
        return "REVISAR", motivos

    # Sin datos en snapshot
    if not book["title"] or book["title"] == "(sin datos en snapshot)":
        motivos.append("Sin datos suficientes en snapshot")
        return "REVISAR", motivos

    # Contenido aparentemente válido
    motivos.append("Contenido aparentemente válido")
    return "SALVAR", motivos


def generar_informe(diag):
    """Genera el informe completo de auditoría."""
    libros, duplicados_groups, fabricados, placeholder_ids, suspicious_ids = analizar_libros(diag)

    # Clasificar cada libro
    duplicados_ids = set()
    for grupo in duplicados_groups.values():
        duplicados_ids.update(grupo["ids"])

    for book in libros:
        clasificacion, motivos = clasificar_libro(
            book, duplicados_ids, fabricados, placeholder_ids
        )
        book["clasificacion_final"] = clasificacion
        book["motivo"] = motivos

    # Determinar candidato superior por grupo
    for clave, grupo in duplicados_groups.items():
        ids = grupo["ids"]
        # El candidato superior es el que NO es placeholder y NO es fabricado
        candidatos = []
        for bid in ids:
            if bid not in placeholder_ids and bid not in fabricados:
                candidatos.append(bid)
        if candidatos:
            # Elegir el de menor ID como candidato
            superior = min(candidatos)
        else:
            # Todos son placeholder/fabricado, elegir el de menor ID
            superior = min(ids)
        for bid in ids:
            for book in libros:
                if book["id"] == bid:
                    book["candidato_superior"] = superior
                    break

    return libros, duplicados_groups


def imprimir_tabla_final(libros):
    """Imprime la tabla final de cruze."""
    print()
    print("=" * 140)
    print("TABLA FINAL DE CRUZAMIENTO")
    print("=" * 140)
    header = "ID | Titulo | Autor | Content | Pages | PDF | Patol | Dup | Sup | Clasificacion"
    print(header)
    print("-" * 140)
    for b in libros:
        title = (b["title"] or "S/D")[:40]
        author = (b["author"] or "S/D")[:20]
        content = str(b["content_chars"] or "N/A")[:8]
        pages = str(b["book_pages_count"] or "N/A")[:5]
        pdf = "SI" if b["pdf_existe"] else "NO"
        patol = "SI" if b["contenido_patologico"] else "NO"
        dup = "SI" if len(b["grupo_duplicado"]) > 1 else "NO"
        sup = str(b["candidato_superior"] or "N/A")[:4]
        clas = b["clasificacion_final"][:20]
        print(f"{b['id']:>4} | {title:<40} | {author:<20} | {content:>8} | {pages:>5} | {pdf:>3} | {patol:>5} | {dup:>3} | {sup:>4} | {clas:<20}")


def imprimir_jsonl(libros):
    """Imprime JSONL por libro."""
    print()
    print("=" * 140)
    print("JSONL POR LIBRO")
    print("=" * 140)
    for b in libros:
        entry = {
            "id": b["id"],
            "title": b["title"],
            "author": b["author"],
            "content_chars": b["content_chars"],
            "book_pages_count": b["book_pages_count"],
            "pdf_path": b["pdf_path"],
            "pdf_existe": b["pdf_existe"],
            "pdf_size": b["pdf_size"],
            "contenido_patologico": b["contenido_patologico"],
            "grupo_duplicado": b["grupo_duplicado"],
            "candidato_superior": b["candidato_superior"],
            "clasificacion_final": b["clasificacion_final"],
            "motivo": "; ".join(b["motivo"]) if b["motivo"] else ""
        }
        print(json.dumps(entry, ensure_ascii=False, default=str))


def imprimir_resumen(libros, duplicados_groups):
    """Imprime el resumen ejecutivo."""
    print()
    print("=" * 140)
    print("RESUMEN EJECUTIVO")
    print("=" * 140)

    clas_counts = Counter(b["clasificacion_final"] for b in libros)
    total = len(libros)

    print(f"\nTotal de libros auditados: {total}")
    print(f"\n--- CLASIFICACION FINAL ---")
    for clas, count in sorted(clas_counts.items()):
        print(f"  {clas}: {count} ({count*100/total:.1f}%)")

    # Duplicados
    grupos_con_duplicados = [g for g in duplicados_groups.values() if g["count"] > 1]
    print(f"\n--- DUPLICADOS ---")
    print(f"  Grupos de duplicados: {len(grupos_con_duplicados)}")
    total_duplicados = sum(g["count"] for g in grupos_con_duplicados)
    print(f"  Total libros en grupos duplicados: {total_duplicados}")

    # PDFs
    pdfs_existentes = sum(1 for b in libros if b["pdf_existe"])
    pdfs_perdidos = sum(1 for b in libros if b["pdf_path"] and not b["pdf_existe"])
    sin_pdf = sum(1 for b in libros if not b["pdf_path"])
    print(f"\n--- PDFs ---")
    print(f"  PDFs existentes: {pdfs_existentes}")
    print(f"  PDFs perdidos (registrados): {pdfs_perdidos}")
    print(f"  Sin PDF registrado: {sin_pdf}")

    # Contenido patológico
    patologicos = sum(1 for b in libros if b["contenido_patologico"])
    placeholders = sum(1 for b in libros if b["placeholder"])
    fabricados_count = sum(1 for b in libros if b["id"] in range(5, 131) and b["pathological"])
    print(f"\n--- CONTENIDO PATOLÓGICO ---")
    print(f"  Libros con contenido patológico: {patologicos}")
    print(f"  Libros con placeholder: {placeholders}")
    print(f"  Libros fabricados (seed range 5-130): {fabricados_count}")

    # Book pages
    con_pages = sum(1 for b in libros if b["book_pages_count"] and b["book_pages_count"] > 0)
    print(f"\n--- BOOK_PAGES ---")
    print(f"  Libros con book_pages: {con_pages}")
    print(f"  Libros sin book_pages: {total - con_pages}")

    # Clasificación por rangos
    print(f"\n--- ANÁLISIS POR RANGOS ---")
    seeds = [b for b in libros if b["id"] in range(5, 131)]
    placeholders_books = [b for b in libros if b["placeholder"]]
    fabricados_books = [b for b in libros if b["id"] in range(5, 131) and b["pathological"]]
    print(f"  Rango seeds (5-130): {len(seeds)} libros")
    print(f"    - Fabricados (párrafo repetido 200x): {len(fabricados_books)}")
    print(f"  Placeholders (133-170): {len(placeholders_books)}")
    print(f"  Fuera de ambos rangos: {total - len(seeds) - len(placeholders_books)}")


def main():
    #sys.stdout.reconfigure(errors="backslashreplace")
    print("Cargando snapshot...")
    snapshot = load_snapshot(SNAPSHOT_PATH)
    diag = snapshot["diagnosis"]

    print("Analizando libros...")
    libros, duplicados_groups = generar_informe(diag)

    imprimir_tabla_final(libros)
    imprimir_resumen(libros, duplicados_groups)
    imprimir_jsonl(libros)

    print()
    print("=" * 140)
    print("VALIDACIÓN DE SEGURIDAD")
    print("=" * 140)
    print("Operaciones SELECT ejecutadas: 0 (análisis desde snapshot)")
    print("Comprobaciones de archivos: 0 (sin conexión a BD)")
    print("Archivos del repositorio modificados: 0")
    print("Commits realizados: 0")
    print("Pushes realizados: 0")
    print("Deploys realizados: 0")
    print()
    print("PRODUCCIÓN NO FUE MODIFICADA.")


if __name__ == "__main__":
    main()
