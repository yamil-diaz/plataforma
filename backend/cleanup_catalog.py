# -*- coding: utf-8 -*-
"""
cleanup_catalog.py — LIMPIEZA CONTROLADA DEL CATÁLOGO (FASE 1: DRY-RUN).

Este script inspecciona la base de datos de producción y clasifica libros
candidatos a eliminación. SOLO ejecuta --dry-run en esta etapa.

Modos:
  --dry-run   Conecta en READ ONLY, analiza, genera DELETE_IDS, NO modifica nada.
  --execute   (Preparado para etapa futura. NO ejecutar sin aprobación explícita.)

Uso:
  python cleanup_catalog.py --dry-run
  python cleanup_catalog.py --dry-run --verbose
  python cleanup_catalog.py --execute --ids 133,134,135 --confirm "BORRAR 133,134,135"
"""
import os
import sys
import argparse
import json
from collections import Counter
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Configuracion ────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or os.path.join(BASE_DIR, "storage"))
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")

# IDs que JAMAS se eliminan — si aparecen en DELETE_IDS, el dry-run aborta.
PROTECTED_IDS = {
    5, 6, 7, 8, 10, 11, 12, 13, 18, 19, 21, 22, 29, 34, 41, 117, 145, 158, 172, 173, 175,
}

# Contenido placeholder conocido
CONTENIDO_PLACEHOLDER = "Contenido no disponible"

# Limites de seguridad para --execute (preparados, no usados en dry-run)
MAX_LIBROS_POR_EJECUCION = 50
UMBRAL_PROTECCION_MASIVA = 0.90


# ── Utilidades ───────────────────────────────────────────────────────────────

def _conectar(readonly=True):
    """Conecta a PostgreSQL. Si readonly=True, establece READ ONLY."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    if readonly:
        conn.set_session(readonly=True, autocommit=False)
    return conn


def _check_protected_ids(delete_ids):
    """Verifica que ningun ID protegido aparezca en la lista de eliminacion."""
    found = sorted(PROTECTED_IDS.intersection(delete_ids))
    if found:
        print(f"\n{'='*70}")
        print(f"ABORTADO: IDS PROTEGIDOS ENCONTRADOS EN DELETE_IDS: {found}")
        print("Ninguna ejecucion sera permitida.")
        print(f"{'='*70}")
        return False
    return True


# ── Fase 1: Inspeccion de esquema ────────────────────────────────────────────

def inspeccionar_esquema(cursor):
    """Descubre foreign keys reales que apuntan a books(id)."""
    cursor.execute("""
        SELECT
            tc.table_name AS dependent_table,
            kcu.column_name AS dependent_column,
            ccu.table_name AS referenced_table,
            ccu.column_name AS referenced_column,
            rc.delete_rule,
            rc.update_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'books'
          AND ccu.column_name = 'id'
        ORDER BY tc.table_name
    """)
    fks = cursor.fetchall()

    print(f"\n{'='*70}")
    print("INSPECCION DE ESQUEMA: Foreign Keys que apuntan a books(id)")
    print(f"{'='*70}")
    for fk in fks:
        print(
            f"  {fk['dependent_table']}.{fk['dependent_column']} -> "
            f"books.{fk['referenced_column']}  "
            f"(ON DELETE {fk['delete_rule']}, ON UPDATE {fk['update_rule']})"
        )
    print(f"  Total: {len(fks)} foreign keys encontradas")
    return fks


def inspeccionar_tablas(cursor):
    """Lista todas las tablas del schema public."""
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [r["table_name"] for r in cursor.fetchall()]
    print(f"\n  Tablas en schema public: {len(tables)}")
    for t in tables:
        print(f"    - {t}")
    return tables


# ── Fase 2: Analisis de libros ───────────────────────────────────────────────

def _detectar_contenido_patologico(content):
    """Detecta contenido repetido/fabricado masivamente.

    Returns dict con 'es_patologico' (bool) y 'razon' (str o None).
    """
    if len(content) < 100:
        return {"es_patologico": False, "razon": None}

    lineas = [l.strip() for l in content.split("\n") if l.strip()]
    if not lineas:
        return {"es_patologico": False, "razon": None}

    # EXIGIR minimo 3 lineas totales para considerar ratio significativo
    # y minimo 3 ocurrencias absolutas de la linea mas comun
    if len(lineas) < 3:
        return {"es_patologico": False, "razon": None}

    conteo = Counter(lineas)
    mas_comun, freq = conteo.most_common(1)[0]
    ratio = freq / len(lineas)

    # Si una linea unica domina >80% del contenido
    # EXIGIR: minimo 3 lineas totales, minimo 3 ocurrencias, linea > 20 chars
    if ratio > 0.80 and len(mas_comun) > 20 and freq >= 3:
        return {
            "es_patologico": True,
            "razon": f"Linea repetida {freq}/{len(lineas)} veces ({ratio:.0%}): '{mas_comun[:60]}...'",
        }

    # Si hay muy pocas lineas unicas en relacion al tamano
    # (ya requiere len(lineas) > 50 por la condicion abajo)
    lineas_unicas = len(set(lineas))
    if len(lineas) > 50 and lineas_unicas < 10:
        return {
            "es_patologico": True,
            "razon": f"Contenido altamente repetido: solo {lineas_unicas} lineas unicas de {len(lineas)} totales",
        }

    return {"es_patologico": False, "razon": None}


def analizar_libros(cursor, verbose=False):
    """Analiza todos los libros y retorna candidatos a eliminacion.

    CRITERIOS DE CLASIFICACION:
    - Solo se clasifica como candidato si hay evidencia INEQUIVOCA de:
      * placeholder (contenido = 'Contenido no disponible')
      * contenido vacio o casi vacio (< 50 chars) Y sin dependencias reales
      * contenido patologico (duplicacion/fabricacion masiva)

    - NO se considera eliminable solo por:
      * no tener PDF
      * tener poco contenido
      * parecer duplicado
    """
    cursor.execute("""
        SELECT
            b.id, b.title, b.author_name, b.content, b.category,
            b.price, b.pdf_path, b.cover_image_url,
            b.views, b.likes, b.dislikes,
            b.average_rating, b.total_reviews,
            b.published, b.created_at, b.page_count, b.paginated_at,
            (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) AS n_book_pages,
            (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) AS n_chapters,
            (SELECT count(*) FROM reviews r WHERE r.book_id = b.id) AS n_reviews,
            (SELECT count(*) FROM book_interactions bi WHERE bi.book_id = b.id) AS n_interactions,
            (SELECT count(*) FROM reading_progress rp WHERE rp.book_id = b.id) AS n_reading_progress,
            (SELECT count(*) FROM reading_sessions rs WHERE rs.book_id = b.id) AS n_reading_sessions
        FROM books b
        ORDER BY b.id
    """)
    all_books = cursor.fetchall()
    total = len(all_books)
    print(f"\n{'='*70}")
    print(f"ANALISIS DE CATALOGO: {total} libros")
    print(f"{'='*70}")

    candidatos = []
    stats = {
        "confiables": 0,
        "con_pdf": 0,
        "sin_pdf": 0,
        "placeholder": 0,
        "vacios": 0,
        "patologicos": 0,
    }

    for book in all_books:
        bid = book["id"]
        title = book["title"] or ""
        author = book["author_name"] or ""
        content = book["content"] or ""
        content_len = len(content)
        pdf_path = book["pdf_path"] or ""
        page_count = book["page_count"] or 0
        n_book_pages = book["n_book_pages"] or 0
        n_chapters = book["n_chapters"] or 0
        n_reviews = book["n_reviews"] or 0
        n_interactions = book["n_interactions"] or 0
        n_reading_progress = book["n_reading_progress"] or 0
        n_reading_sessions = book["n_reading_sessions"] or 0

        # Verificar si el PDF existe en disco
        pdf_existe = False
        if pdf_path:
            ruta = pdf_path if os.path.isabs(pdf_path) else os.path.join(
                STORAGE_BOOKS, os.path.basename(pdf_path)
            )
            pdf_existe = os.path.isfile(ruta)

        # ── Clasificacion ────────────────────────────────────────────────
        es_placeholder = content.strip() == CONTENIDO_PLACEHOLDER
        es_vacio = content_len < 50 and not content.strip()
        diagnostico_pat = _detectar_contenido_patologico(content)
        es_patologico = diagnostico_pat["es_patologico"]

        motivo = None
        clasificacion = None

        if es_placeholder:
            clasificacion = "PLACEHOLDER"
            motivo = "Contenido placeholder ('Contenido no disponible')"
            stats["placeholder"] += 1
        elif es_vacio:
            clasificacion = "VACIO"
            motivo = "Contenido vacio o casi vacio (< 50 chars, sin texto)"
            stats["vacios"] += 1
        elif es_patologico:
            clasificacion = "PATOLOGICO"
            motivo = diagnostico_pat["razon"]
            stats["patologicos"] += 1
        else:
            # El libro tiene contenido real — es confiable
            stats["confiables"] += 1
            if pdf_path:
                stats["con_pdf"] += 1
            else:
                stats["sin_pdf"] += 1
            continue  # No es candidato

        # ── Solo candidatos pasan aqui ────────────────────────────────────
        candidatos.append({
            "id": bid,
            "title": title,
            "author": author,
            "content_length": content_len,
            "page_count": page_count,
            "book_pages": n_book_pages,
            "chapters": n_chapters,
            "reviews": n_reviews,
            "interactions": n_interactions,
            "reading_progress": n_reading_progress,
            "reading_sessions": n_reading_sessions,
            "pdf_path": pdf_path or "-",
            "pdf_existe": pdf_existe,
            "clasificacion": clasificacion,
            "motivo": motivo,
        })

        if verbose:
            print(f"  [CANDIDATO] {bid}: {title} — {clasificacion} — {motivo}")

    # ── Resumen ──────────────────────────────────────────────────────────
    print(f"\n  RESUMEN:")
    print(f"    Total libros:           {total}")
    print(f"    Confiables:             {stats['confiables']}")
    print(f"      Con PDF:              {stats['con_pdf']}")
    print(f"      Sin PDF:              {stats['sin_pdf']}")
    print(f"    Candidatos a limpiar:   {len(candidatos)}")
    print(f"      - Placeholder:        {stats['placeholder']}")
    print(f"      - Vacios:             {stats['vacios']}")
    print(f"      - Patologicos:        {stats['patologicos']}")

    return candidatos


# ── Fase 3: Generar DELETE_IDS ───────────────────────────────────────────────

def generar_delete_ids(candidatos):
    """Genera la lista DELETE_IDS y verifica protegidos."""
    delete_ids = [c["id"] for c in candidatos]
    delete_ids.sort()

    print(f"\n{'='*70}")
    print("DELETE_IDS GENERADO")
    print(f"{'='*70}")
    print(f"  {delete_ids}")
    print(f"  Total: {len(delete_ids)} libros")

    # Verificacion de IDs protegidos
    protected_found = sorted(PROTECTED_IDS.intersection(delete_ids))
    print(f"\n  PROTECTED_IDS_FOUND_IN_DELETE_IDS = {protected_found}")

    if protected_found:
        print(f"\n{'!'*70}")
        print(f"  ABORTADO: {len(protected_found)} ID(s) PROTEGIDO(s) en DELETE_IDS")
        print(f"  IDs: {protected_found}")
        print(f"  Ninguna ejecucion sera permitida.")
        print(f"{'!'*70}")
        return None

    return delete_ids


# ── Fase 4: Mostrar detalle de candidatos ────────────────────────────────────

def mostrar_candidatos(candidatos):
    """Muestra tabla detallada de cada candidato."""
    if not candidatos:
        print("\n  No se encontraron candidatos a eliminacion.")
        return

    print(f"\n{'='*70}")
    print("DETALLE DE CANDIDATOS")
    print(f"{'='*70}")

    for c in candidatos:
        pdf_flag = "SI" if c["pdf_existe"] else "NO"
        tiene_dependencias = (
            c["reviews"] > 0 or c["interactions"] > 0 or
            c["reading_progress"] > 0 or c["reading_sessions"] > 0
        )
        dep_str = []
        if c["reviews"] > 0:
            dep_str.append(f"reviews={c['reviews']}")
        if c["interactions"] > 0:
            dep_str.append(f"interactions={c['interactions']}")
        if c["reading_progress"] > 0:
            dep_str.append(f"reading_progress={c['reading_progress']}")
        if c["reading_sessions"] > 0:
            dep_str.append(f"reading_sessions={c['reading_sessions']}")
        if c["book_pages"] > 0:
            dep_str.append(f"book_pages={c['book_pages']}")
        if c["chapters"] > 0:
            dep_str.append(f"chapters={c['chapters']}")

        print(f"\n  ID: {c['id']}")
        print(f"    Titulo:    {c['title']}")
        print(f"    Autor:     {c['author']}")
        print(f"    Chars:     {c['content_length']}")
        print(f"    Pages:     {c['page_count']} (book_pages={c['book_pages']}, chapters={c['chapters']})")
        print(f"    PDF:       {c['pdf_path']} (existe={pdf_flag})")
        print(f"    Deps:      {', '.join(dep_str) if dep_str else 'NINGUNA'}")
        print(f"    Clase:     {c['clasificacion']}")
        print(f"    Motivo:    {c['motivo']}")


# ── Modo --execute (PREPARADO, NO EJECUTAR) ──────────────────────────────────

def ejecutar_borrado(conn, delete_ids, confirm):
    """Ejecuta el borrado real. PROTEGIDO: requiere confirmacion explicita.

    ESTA FUNCION NO DEBE EJECUTARSE EN ESTA ETAPA.
    """
    raise SystemExit(
        "RECHAZADO: --execute no esta habilitado en esta etapa. "
        "Espera la aprobacion manual del dry-run."
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Limpieza controlada del catalogo (Fase 1: dry-run)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Modo solo lectura: analiza, clasifica, genera DELETE_IDS sin modificar nada."
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Ejecuta borrado real (REQUERIRA confirmacion adicional)."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Muestra informacion adicional durante el analisis."
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Ruta para guardar el reporte JSON (opcional)."
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("Especifica --dry-run o --execute.")

    if args.execute:
        raise SystemExit(
            "RECHAZADO: --execute no esta habilitado en esta etapa. "
            "Usa --dry-run para inspeccionar."
        )

    # ── Modo dry-run ─────────────────────────────────────────────────────
    print(f"{'='*70}")
    print("MODO: DRY-RUN (READ ONLY)")
    print(f"{'='*70}")
    print(f"  DATABASE_URL: ...{DATABASE_URL[-20:]}")
    print(f"  STORAGE_DIR:  {STORAGE_DIR}")

    conn = _conectar(readonly=True)
    cursor = conn.cursor()

    try:
        # Verificar READ ONLY
        cursor.execute("SHOW transaction_read_only")
        ro = cursor.fetchone()
        ro_value = ro.get("transaction_read_only", "on") if ro else "on"
        if ro_value != "on":
            raise SystemExit("ERROR: la conexion NO esta en modo READ ONLY. Abortando.")
        print(f"  PostgreSQL READ ONLY: confirmado ({ro_value})")

        # Paso 1: Inspeccionar esquema
        fks = inspeccionar_esquema(cursor)
        inspeccionar_tablas(cursor)

        # Paso 2: Analizar libros
        candidatos = analizar_libros(cursor, verbose=args.verbose)

        # Paso 3: Mostrar detalle
        mostrar_candidatos(candidatos)

        # Paso 4: Generar DELETE_IDS
        delete_ids = generar_delete_ids(candidatos)

        if delete_ids is None:
            # IDs protegidos encontrados — abortar
            print("\nDRY-RUN: FAILED")
            print("NO DATABASE MODIFICATIONS PERFORMED")
            return 1

        # Paso 5: Reporte JSON si se solicita
        if args.output:
            cursor.execute("SELECT count(*) AS n FROM books")
            total_books = cursor.fetchone()["n"]
            reporte = {
                "mode": "dry-run",
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "total_books": total_books,
                "delete_ids": delete_ids,
                "protected_ids_found": [],
                "candidatos": candidatos,
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(reporte, f, indent=2, ensure_ascii=False)
            print(f"\n  Reporte guardado en: {args.output}")

        # Paso 6: Mensaje final
        print(f"\n{'='*70}")
        print("DRY-RUN ONLY")
        print("NO DATABASE MODIFICATIONS PERFORMED")
        print(f"{'='*70}")
        print(f"\n  Para ejecutar posteriormente en Render:")
        print(f"    cd /opt/render/project/src/backend")
        print(f"    python cleanup_catalog.py --dry-run")
        print(f"\n  Proximos pasos:")
        print(f"    1. Revisar manualmente cada candidato")
        print(f"    2. Autorizar o modificar DELETE_IDS")
        print(f"    3. Ejecutar --execute con confirmacion")

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
