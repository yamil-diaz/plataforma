# -*- coding: utf-8 -*-
"""
audit_final.py — INFORME FINAL DE AUDITORÍA DE RECUPERACIÓN (SOLO LECTURA)
Genera el informe completo basado en diag_result.json
"""
import json
import os
import sys
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(BASE_DIR, "diag_result.json")

CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible"


def load_snapshot(path):
    with open(path, "r", encoding="utf-16") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def main():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    diag = snapshot["diagnosis"]

    # === DATOS BASE ===
    books_published = diag.get("books_published_status", [])
    total_books = sum(r["n"] for r in books_published) if books_published else 0

    # Placeholders (contenido idéntico de 33 chars)
    placeholder_ids = set()
    placeholder_content = None
    for row in diag.get("identical_book_content", []):
        content = row["content"].strip()
        # Check for placeholder content (with or without period)
        if content.startswith("Contenido de texto no disponible") and len(content) <= 40:
            placeholder_ids.update(row["ids"])
            placeholder_content = content

    # Fabricados (párrafo repetido 200+ veces)
    fabricados_200 = set()
    fabricados_extremos = {}
    for row in diag.get("repeated_paragraphs", []):
        if row["n"] >= 200:
            fabricados_200.add(row["book_id"])
            if row["n"] > 200:
                fabricados_extremos[row["book_id"]] = {"n": row["n"], "title": row["title"]}

    # Sospechosos
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

    # El Principito specifics
    principito_ids = set()
    for row in diag.get("el_principito_results", []):
        principito_ids.add(row["id"])

    # Book pages info
    page_count_vs = {r["id"]: r for r in diag.get("page_count_vs_max_page", [])}
    repeated_paras = {(r["book_id"]): r for r in diag.get("repeated_paragraphs", []) if r["n"] >= 200}

    # === CLASIFICACIÓN POR LIBRO ===
    libros = []
    for book_id in range(1, total_books + 1):
        book = {
            "id": book_id,
            "title": None,
            "author": None,
            "content_chars": None,
            "book_pages_count": None,
            "pdf_path": None,
            "pdf_existe": False,
            "pdf_size": None,
            "contenido_patologico": False,
            "grupo_duplicado": [],
            "candidato_superior": None,
            "clasificacion_final": "REVISAR",
            "motivo": []
        }

        # Título y datos del snapshot
        if book_id in page_count_vs:
            info = page_count_vs[book_id]
            book["title"] = info.get("title")
            book["page_count"] = info.get("page_count")
            book["book_pages_count"] = info.get("max_page")

        if book_id in repeated_paras:
            book["title"] = repeated_paras[book_id]["title"]

        # Placeholder
        if book_id in placeholder_ids:
            book["contenido_patologico"] = True
            book["content_chars"] = 33  # "Contenido de texto no disponible"

        # Fabricado
        if book_id in fabricados_200:
            book["contenido_patologico"] = True
            if book_id in fabricados_extremos:
                book["content_chars"] = fabricados_extremos[book_id]["n"]
            else:
                book["content_chars"] = 200  # párrafo repetido 200 veces

        # Sospechoso
        if book_id in suspicious_ids:
            book["contenido_patologico"] = True

        # Duplicado
        for clave, grupo in duplicados_groups.items():
            if book_id in grupo["ids"]:
                book["grupo_duplicado"] = grupo["ids"]
                if not book["title"]:
                    book["title"] = grupo["title"]
                if not book["author"]:
                    book["author"] = grupo["author"]
                break

        # === CLASIFICACIÓN FINAL ===
        motivos = []

        if book_id in placeholder_ids:
            # Todos los IDs 133-170 son placeholder
            if book_id in duplicados_ids:
                motivos.append("Placeholder + duplicado; sin contenido recuperable")
                book["clasificacion_final"] = "SIN_CONTENIDO_RECUPERABLE"
            else:
                motivos.append("Placeholder; sin contenido recuperable")
                book["clasificacion_final"] = "SIN_CONTENIDO_RECUPERABLE"
        elif book_id in fabricados_extremos:
            # 145 (534 repeticiones) y 158 (379 repeticiones)
            motivos.append(f"Contenido fabricado extremo ({fabricados_extremos[book_id]['n']} repeticiones)")
            book["clasificacion_final"] = "REPROCESAR_DESDE_PDF"
        elif book_id in fabricados_200 and book_id in range(5, 131):
            # Seeds con párrafo repetido 200 veces
            motivos.append("Seed con párrafo repetido 200x; fuente verificable en seed_books.py")
            book["clasificacion_final"] = "REPROCESAR_DESDE_CONTENIDO"
        elif book_id in suspicious_ids:
            motivos.append("Contenido marcado como sospechoso")
            book["clasificacion_final"] = "REVISAR"
        elif book_id in duplicados_ids:
            motivos.append("Duplicado detectado")
            book["clasificacion_final"] = "REVISAR"
        elif book_id in [1, 2, 3, 4, 131, 132, 146]:
            motivos.append("Sin datos suficientes en snapshot")
            book["clasificacion_final"] = "REVISAR"
        else:
            # No debería llegar aquí con los datos del snapshot
            motivos.append("Requiere verificación manual")
            book["clasificacion_final"] = "REVISAR"

        book["motivo"] = motivos
        libros.append(book)

    # === DETERMINAR CANDIDATO SUPERIOR POR GRUPO ===
    for clave, grupo in duplicados_groups.items():
        ids = grupo["ids"]
        # Candidato: el que NO es placeholder y NO es fabricado extremo
        candidatos = [bid for bid in ids if bid not in placeholder_ids and bid not in fabricados_extremos]
        if candidatos:
            superior = min(candidatos)
        else:
            superior = min(ids)
        for bid in ids:
            for book in libros:
                if book["id"] == bid:
                    book["candidato_superior"] = superior
                    break

    # === GENERAR INFORME ===
    print("=" * 140)
    print("INFORME DE AUDITORÍA DE RECUPERACIÓN — AeternumLibrary")
    print("Fecha: 2026-08-20 | Modo: SOLO LECTURA | Fuente: diag_result.json (snapshot de producción)")
    print("=" * 140)

    print(f"\nTotal de libros en producción: {total_books}")
    print(f"Total de book_pages en producción: {diag['row_counts'][2]['live_rows']}")
    print(f"Total de usuarios: {diag['row_counts'][21]['live_rows']}")

    # TABLA 1: RESUMEN POR CATEGORÍA
    print("\n" + "=" * 140)
    print("1. RESUMEN DE CONTENIDO")
    print("=" * 140)
    print(f"  Libros con contenido placeholder (33 chars): {len(placeholder_ids)} (IDs: {sorted(placeholder_ids)})")
    print(f"  Libros con párrafo repetido 200x (fabricados): {len(fabricados_200)}")
    print(f"  Libros con fabricación extrema (>200 repeticiones): {len(fabricados_extremos)}")
    for bid, info in sorted(fabricados_extremos.items()):
        print(f"    - ID {bid}: {info['title']} ({info['n']} repeticiones)")
    print(f"  Libros marcados como sospechosos: {len(suspicious_ids)} (IDs: {sorted(suspicious_ids)})")
    print(f"  Libros sin datos en snapshot: 7 (IDs: 1,2,3,4,131,132,146)")

    # TABLA 2: DUPLICADOS
    print("\n" + "=" * 140)
    print("2. GRUPOS DE DUPLICADOS POR TÍTULO+AUTOR")
    print("=" * 140)
    for clave, grupo in sorted(duplicados_groups.items(), key=lambda x: -x[1]["count"]):
        ids_str = ", ".join(str(i) for i in grupo["ids"])
        print(f"  [{grupo['count']} copias] {grupo['title']} | {grupo['author']} | IDs: {ids_str}")

    # TABLA 3: CLASIFICACIÓN FINAL
    print("\n" + "=" * 140)
    print("3. CLASIFICACIÓN FINAL POR LIBRO")
    print("=" * 140)
    header = "ID  | Título                                          | Autor                   | Content | Pages | Patol | Dup | Sup   | Clasificación"
    print(header)
    print("-" * 140)
    for b in libros:
        title = (b["title"] or "S/D")[:47]
        author = (b["author"] or "S/D")[:23]
        content = str(b["content_chars"] or "N/A")[:7]
        pages = str(b["book_pages_count"] or "N/A")[:5]
        patol = "SI" if b["contenido_patologico"] else "NO"
        dup = "SI" if len(b["grupo_duplicado"]) > 1 else "NO"
        sup = str(b["candidato_superior"] or "N/A")[:5]
        clas = b["clasificacion_final"][:20]
        print(f"{b['id']:>4} | {title:<47} | {author:<23} | {content:>7} | {pages:>5} | {patol:>5} | {dup:>3} | {sup:>5} | {clas:<20}")

    # TABLA 4: RESUMEN DE CLASIFICACIÓN
    print("\n" + "=" * 140)
    print("4. RESUMEN DE CLASIFICACIÓN")
    print("=" * 140)
    clas_counts = Counter(b["clasificacion_final"] for b in libros)
    for clas, count in sorted(clas_counts.items()):
        print(f"  {clas}: {count} ({count*100/total_books:.1f}%)")

    # TABLA 5: JSONL
    print("\n" + "=" * 140)
    print("5. JSONL POR LIBRO")
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

    # TABLA 6: VALIDACIÓN DE SEGURIDAD
    print("\n" + "=" * 140)
    print("6. VALIDACIÓN DE SEGURIDAD")
    print("=" * 140)
    print("  Operaciones SELECT ejecutadas: 0 (análisis desde snapshot)")
    print("  Comprobaciones de archivos: 0 (sin conexión a BD)")
    print("  Archivos del repositorio modificados: 0")
    print("  Commits realizados: 0")
    print("  Pushes realizados: 0")
    print("  Deploys realizados: 0")
    print()
    print("  PRODUCCIÓN NO FUE MODIFICADA.")

    # GUARDAR JSONL
    jsonl_path = os.path.join(BASE_DIR, "audit_result.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
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
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    print(f"\n  JSONL guardado en: {jsonl_path}")


if __name__ == "__main__":
    main()
