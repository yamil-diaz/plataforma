#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico global de integridad del catálogo - SOLO LECTURA (SELECT only).

Requisitos:
1. page_hashes: hashlib.sha256((p['content'] or '').encode()).hexdigest()
2. short_pages: len(p['content'] or '') < 50
3. NO INSERT/UPDATE/DELETE - solo SELECT
4. Genera catalog_integrity_report.json localmente
5. Solo consultas SELECT
6. Si falla un libro individual, registrar error y continuar
6. Al finalizar mostrar obligatoriamente:
   * total de libros
   * cantidad 🔴 dañados
   * cantidad 🟡 sospechosos
   * cantidad ⚪ sin fuente
   * cantidad 🟢 íntegros
   * IDs completos de 🔴 dañados
   * IDs completos de 🟡 sospechosos
   * grupos de contenido idéntico entre libros
   * análisis específico del ID 18
   * confirmación de que todas las consultas fueron SELECT
   * confirmación de que la BD de producción no fue modificada
"""

import os
import sys
import json
import hashlib
import traceback
from collections import defaultdict

import psycopg2
import psycopg2.extras

# Importar configuración centralizada de storage
from storage_config import STORAGE_BOOKS

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL no definida", file=sys.stderr)
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

CONTENIDO_NO_DISPONIBLE = "Contenido de texto no disponible."


def get_connection():
    """Conexión READ-ONLY a la base de datos."""
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        options="-c default_transaction_read_only=on"
    )
    conn.set_session(readonly=True, autocommit=False)
    return conn


def analizar_libro(cursor, libro_id):
    """Analiza un libro individual, retorna dict con resultado o error."""
    try:
        # Obtener libro y sus páginas
        cursor.execute("""
            SELECT b.id, b.title, b.author_name, b.content, b.page_count, b.published,
                   b.pdf_path, b.created_at
            FROM books b
            WHERE b.id = %s
        """, (libro_id,))
        libro = cursor.fetchone()
        
        if not libro:
            return {"id": libro_id, "error": "Libro no encontrado", "estado": "ERROR"}
        
        cursor.execute("""
            SELECT page_number, content
            FROM book_pages
            WHERE book_id = %s
            ORDER BY page_number
        """, (libro_id,))
        paginas = cursor.fetchall()
        
        # Contenido del libro
        content = libro["content"] or ""
        content_len = len(content)
        
        # Hashes de páginas (requisito 1)
        page_hashes = []
        for p in paginas:
            page_content = p["content"] or ""
            page_hash = hashlib.sha256(page_content.encode()).hexdigest()
            page_hashes.append({
                "page_number": p["page_number"],
                "hash": page_hash,
                "content_length": len(page_content)
            })
        
        # Páginas cortas (requisito 2)
        short_pages = [
            {"page_number": p["page_number"], "content_length": len(p["content"] or ""), "content_preview": (p["content"] or "")[:100]}
            for p in paginas if len(p["content"] or "") < 50
        ]
        
        # Estado del contenido
        is_placeholder = content.strip() == CONTENIDO_NO_DISPONIBLE
        is_empty = not content.strip()
        is_short = content_len < 300
        
        # Detectar contenido patológico (párrafos repetidos masivamente)
        pathological = False
        repetition_ratio = 0.0
        if content and not is_placeholder and not is_empty:
            # Buscar párrafos repetidos
            parrafos = [par.strip() for par in content.split("\n\n") if par.strip()]
            if parrafos:
                from collections import Counter
                conteo = Counter(parrafos)
                max_reps = max(conteo.values())
                if max_reps >= 50:  # Umbral para "fabricado x200"
                    pathological = True
                    repetition_ratio = max_reps / len(parrafos) if len(parrafos) > 0 else 0
        
        # Clasificar
        if is_placeholder or is_empty:
            estado = "DANADO"
        elif pathological:
            estado = "SOSPECHOSO"
        elif not libro["pdf_path"]:
            estado = "SIN_FUENTE"
        else:
            estado = "INTEGRO"
        
        # Verificar PDF físico
        pdf_existe = False
        if libro["pdf_path"]:
            import os as _os
            pdf_path = libro["pdf_path"]
            if _os.path.isabs(pdf_path) and _os.path.isfile(pdf_path):
                pdf_existe = True
            else:
                candidata = _os.path.join(STORAGE_BOOKS, _os.path.basename(pdf_path))
                if _os.path.isfile(candidata):
                    pdf_existe = True
        
        return {
            "id": libro["id"],
            "title": libro["title"],
            "author_name": libro["author_name"],
            "content_length": content_len,
            "page_count": libro["page_count"],
            "published": libro["published"],
            "pdf_path": libro["pdf_path"],
            "pdf_existe": pdf_existe,
            "n_book_pages": len(paginas),
            "page_hashes": page_hashes,
            "short_pages": short_pages,
            "is_placeholder": is_placeholder,
            "is_empty": is_empty,
            "is_short": is_short,
            "pathological": pathological,
            "repetition_ratio": round(repetition_ratio, 4),
            "estado": estado
        }
        
    except Exception as e:
        return {
            "id": libro_id,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "estado": "ERROR"
        }


def main():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Obtener todos los IDs de libros
    cursor.execute("SELECT id FROM books ORDER BY id")
    all_ids = [row["id"] for row in cursor.fetchall()]
    total_libros = len(all_ids)
    
    print(f"Total de libros a analizar: {total_libros}", file=sys.stderr)
    
    resultados = {}
    libros_danados = []
    libros_sospechosos = []
    libros_sin_fuente = []
    libros_integros = []
    libros_error = []
    
    # Análisis por libro (continúa si falla uno)
    for i, libro_id in enumerate(all_ids):
        if i % 50 == 0:
            print(f"Procesando {i+1}/{total_libros}...", file=sys.stderr)
        resultado = analizar_libro(cursor, libro_id)
        resultados[libro_id] = resultado
        
        if resultado.get("estado") == "DANADO":
            libros_danados.append(libro_id)
        elif resultado.get("estado") == "SOSPECHOSO":
            libros_sospechosos.append(libro_id)
        elif resultado.get("estado") == "SIN_FUENTE":
            libros_sin_fuente.append(libro_id)
        elif resultado.get("estado") == "INTEGRO":
            libros_integros.append(libro_id)
        else:
            libros_error.append(libro_id)
    
    # Análisis de contenido idéntico entre libros (grupos)
    print("Analizando grupos de contenido identico...", file=sys.stderr)
    cursor.execute("""
        SELECT content, COUNT(*) as n,
               array_agg(id ORDER BY id) as ids,
               array_agg(title ORDER BY id) as titles
        FROM books
        WHERE content IS NOT NULL AND content != ''
        GROUP BY content
        HAVING COUNT(*) > 1
        ORDER BY n DESC
    """)
    grupos_identicos = cursor.fetchall()
    
    # Análisis específico del ID 18
    print("Análisis específico del ID 18...", file=sys.stderr)
    libro_18 = resultados.get(18, {})
    if not libro_18:
        cursor.execute("SELECT * FROM books WHERE id = 18")
        libro_18_raw = cursor.fetchone()
        if libro_18_raw:
            libro_18 = analizar_libro(cursor, 18)
    
    # Verificar que solo se ejecutaron SELECTs
    # En modo READ-ONLY con default_transaction_read_only=on, cualquier
    # INSERT/UPDATE/DELETE lanzaría excepción
    
    cursor.close()
    conn.rollback()
    conn.close()
    
    # Preparar reporte
    reporte = {
        "resumen": {
            "total_libros": total_libros,
            "danados": len(libros_danados),
            "sospechosos": len(libros_sospechosos),
            "sin_fuente": len(libros_sin_fuente),
            "integros": len(libros_integros),
            "errores": len(libros_error)
        },
        "ids_danados": libros_danados,
        "ids_sospechosos": libros_sospechosos,
        "ids_sin_fuente": libros_sin_fuente,
        "ids_integros": libros_integros,
        "ids_error": libros_error,
        "grupos_contenido_identico": [
            {
                "n_libros": g["n"],
                "ids": g["ids"],
                "titles": g["titles"],
                "content_length": len(g["content"]) if g["content"] else 0,
                "content_preview": (g["content"] or "")[:200]
            }
            for g in grupos_identicos
        ],
        "analisis_id_18": libro_18,
        "confirmacion_select_only": True,
        "confirmacion_bd_no_modificada": True,
        "libros_detalle": resultados
    }
    
    # Guardar reporte JSON
    output_path = "catalog_integrity_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
    
    # Mostrar resumen obligatorio (sin emojis para compatibilidad Windows)
    print("\n" + "="*80)
    print("DIAGNOSTICO GLOBAL DE INTEGRIDAD - RESUMEN OBLIGATORIO")
    print("="*80)
    print(f"Total de libros:              {total_libros}")
    print(f"Cantidad ROJOS (dañados):     {len(libros_danados)}")
    print(f"Cantidad AMARILLOS (sospechosos): {len(libros_sospechosos)}")
    print(f"Cantidad BLANCOS (sin fuente): {len(libros_sin_fuente)}")
    print(f"Cantidad VERDES (integros):   {len(libros_integros)}")
    print(f"Cantidad ERRORES:             {len(libros_error)}")
    print()
    print(f"IDs completos de ROJOS:       {libros_danados}")
    print(f"IDs completos de AMARILLOS:   {libros_sospechosos}")
    print()
    print(f"Grupos de contenido idéntico entre libros: {len(grupos_identicos)}")
    for g in grupos_identicos[:10]:
        print(f"  - {g['n']} libros: IDs {g['ids']} ('{g['titles'][0]}')")
    if len(grupos_identicos) > 10:
        print(f"  ... y {len(grupos_identicos) - 10} grupos más")
    print()
    print("Análisis específico del ID 18:")
    if libro_18:
        if "error" in libro_18:
            print(f"  ERROR: {libro_18['error']}")
        else:
            print(f"  Título: {libro_18.get('title', 'N/A')}")
            print(f"  Autor: {libro_18.get('author_name', 'N/A')}")
            print(f"  Content length: {libro_18.get('content_length', 0)}")
            print(f"  Page count: {libro_18.get('page_count', 0)}")
            print(f"  Páginas en book_pages: {libro_18.get('n_book_pages', 0)}")
            print(f"  PDF path: {libro_18.get('pdf_path', 'N/A')}")
            print(f"  PDF existe físicamente: {libro_18.get('pdf_existe', False)}")
            print(f"  Placeholder: {libro_18.get('is_placeholder', False)}")
            print(f"  Vacío: {libro_18.get('is_empty', False)}")
            print(f"  Patológico: {libro_18.get('pathological', False)}")
            print(f"  Repetition ratio: {libro_18.get('repetition_ratio', 0)}")
            print(f"  Estado: {libro_18.get('estado', 'N/A')}")
            print(f"  Páginas cortas (<50 chars): {len(libro_18.get('short_pages', []))}")
    else:
        print("  No encontrado")
    print()
    print("CONFIRMACIÓN: Todas las consultas fueron SELECT (modo READ-ONLY)")
    print("CONFIRMACIÓN: La BD de producción NO fue modificada")
    print("="*80)
    print(f"\nReporte completo guardado en: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())