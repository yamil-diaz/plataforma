# -*- coding: utf-8 -*-
"""
DRY-RUN de repaginación segura para AeternumLibrary.
Analiza TODOS los libros y muestra qué se haría SIN modificar datos.

Reglas:
- NO repaginar libros con contenido patológico/placeholder/basura
- NO alterar books.content original
- page_count debe coincidir con book_pages reales
- page_number consecutivo desde 1
- Idempotente: si ya está bien, no se toca
"""
import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set environment
os.environ['DATABASE_URL'] = 'postgresql://postgres:yamilpro002@localhost:5432/plataforma_dev'
os.environ['STORAGE_DIR'] = 'backend/storage'

# Importar configuración centralizada de storage (después de configurar entorno)
from storage_config import STORAGE_DIR, STORAGE_BOOKS

import lectura

# Use pg8000 instead of psycopg2 due to encoding issues
import pg8000


def get_db():
    """Crea y devuelve una conexión nueva a PostgreSQL usando pg8000."""
    return pg8000.connect(
        host='localhost',
        database='plataforma_dev',
        user='postgres',
        password='yamilpro002',
        port=5432
    )


CONTENIDO_NO_DISPONIBLE = lectura.CONTENIDO_NO_DISPONIBLE


def _estado_contenido(content, paginas=None):
    """Estado de validación de un contenido (solo lectura)."""
    content = content or ""
    info = {
        "placeholder": content.strip() == CONTENIDO_NO_DISPONIBLE,
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


def _es_seed(book):
    """Verifica si es un libro sembrado (IDs 5-130 en seed_books.py)."""
    return book["id"] in range(5, 131)


def _tiene_paginacion_valida(book, n_book_pages):
    """Verifica si el libro ya tiene paginación válida y consistente."""
    page_count = book.get("page_count") or 0
    return page_count > 0 and n_book_pages > 0 and page_count == n_book_pages


def _debe_repaginar(book, n_book_pages, info_contenido, duplicados_ids):
    """Determina si un libro debe ser repaginado."""
    libro_id = book["id"]
    
    # 1. Libro protegido (ID 18 - El Principito original)
    if libro_id == 18:
        return False, "EXCLUIDO: Libro protegido (ID 18 - El Principito original)"
    
    # 2. Contenido placeholder/vacío
    if info_contenido["placeholder"] or info_contenido["vacío"]:
        return False, "EXCLUIDO: Contenido placeholder o vacío"
    
    # 3. Contenido patológico o basura
    if info_contenido["pathological"] or info_contenido["basura"]:
        if _es_seed(book):
            return True, "REPAGINAR: Seed book con paginación patológica (fuente: seed_books.py)"
        return False, "EXCLUIDO: Contenido patológico/basura sin fuente verificable"
    
    # 4. Contenido muy corto
    if info_contenido["content_length"] is not None and info_contenido["content_length"] < lectura.MIN_CONTENIDO_TOTAL:
        return False, f"EXCLUIDO: Contenido insuficiente ({info_contenido['content_length']} chars < {lectura.MIN_CONTENIDO_TOTAL})"
    
    # 5. Errores de validación
    if info_contenido["errors"]:
        return False, f"EXCLUIDO: Errores de validación: {'; '.join(info_contenido['errors'])}"
    
    # 6. Libro duplicado exacto
    if libro_id in duplicados_ids:
        return False, "EXCLUIDO: Duplicado exacto (requiere decisión manual)"
    
    # 7. Ya tiene paginación válida
    if _tiene_paginacion_valida(book, n_book_pages):
        return False, "EXCLUIDO: Ya tiene paginación válida y consistente"
    
    # 8. Necesita repaginación (contenido confiable pero sin paginación o descuadrada)
    return True, "REPAGINAR: Contenido confiable sin paginación o descuadrada"


def _paginas_que_se_generarian(content):
    """Simula cuántas páginas se generarían desde el contenido."""
    if not content or not content.strip():
        return 0
    paginas = lectura.paginar_desde_contenido(content)
    return len(paginas)


def main():
    print("=" * 80)
    print("DRY-RUN DE REPAGINACIÓN SEGURA - AETERNUM LIBRARY")
    print("=" * 80)
    print()
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Helper to convert pg8000 rows to dict
        def rows_to_dict(cursor, rows):
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        
        # Obtener todos los libros publicados con sus estadísticas
        cursor.execute("""
            SELECT b.id, b.title, b.author_name, b.content, b.page_count, b.published, b.pdf_path,
                   (SELECT count(*) FROM book_pages p WHERE p.book_id = b.id) AS n_book_pages,
                   (SELECT count(*) FROM chapters c WHERE c.book_id = b.id) AS n_chapters
            FROM books b
            WHERE b.published = 1
            ORDER BY b.id
        """)
        libros = rows_to_dict(cursor, cursor.fetchall())
        
        # Detectar duplicados exactos (mismo título + autor)
        cursor.execute("""
            SELECT title, author_name, array_agg(id ORDER BY id) AS ids
            FROM books
            GROUP BY title, author_name
            HAVING count(*) > 1
        """)
        duplicados = set()
        for r in rows_to_dict(cursor, cursor.fetchall()):
            for bid in r["ids"]:
                duplicados.add(bid)
        
        print(f"Total libros publicados: {len(libros)}")
        print(f"Libros en grupos duplicados: {len(duplicados)}")
        print()
        
        # Análisis por libro
        stats = {
            "total": 0,
            "reprocesar": 0,
            "excluido_protegido": 0,
            "excluido_placeholder": 0,
            "excluido_patologico": 0,
            "excluido_corto": 0,
            "excluido_errores": 0,
            "excluido_duplicado": 0,
            "excluido_ya_valido": 0,
        }
        
        detalles = []
        
        for book in libros:
            stats["total"] += 1
            libro_id = book["id"]
            
            # Estado del contenido
            content = book["content"] or ""
            info = _estado_contenido(content)
            
            # Páginas que se generarían
            paginas_estimadas = _paginas_que_se_generarian(content)
            n_book_pages = book["n_book_pages"] or 0
            
            # Decisión
            debe, motivo = _debe_repaginar(book, n_book_pages, info, duplicados)
            
            if debe:
                stats["reprocesar"] += 1
                accion = "REPAGINAR"
            else:
                accion = "EXCLUIR"
                if "protegido" in motivo.lower():
                    stats["excluido_protegido"] += 1
                elif "placeholder" in motivo.lower() or "vacío" in motivo.lower():
                    stats["excluido_placeholder"] += 1
                elif "patológico" in motivo.lower() or "basura" in motivo.lower():
                    stats["excluido_patologico"] += 1
                elif "insuficiente" in motivo.lower():
                    stats["excluido_corto"] += 1
                elif "validación" in motivo.lower():
                    stats["excluido_errores"] += 1
                elif "duplicado" in motivo.lower():
                    stats["excluido_duplicado"] += 1
                elif "válida" in motivo.lower() or "consistente" in motivo.lower():
                    stats["excluido_ya_valido"] += 1
            
            detalle = {
                "id": libro_id,
                "titulo": book["title"],
                "autor": book["author_name"],
                "page_count_actual": book["page_count"],
                "book_pages_actuales": n_book_pages,
                "chapters_actuales": book["n_chapters"],
                "content_length": info["content_length"],
                "placeholder": info["placeholder"],
                "pathological": info["pathological"],
                "basura": info["basura"],
                "paginas_que_generarian": paginas_estimadas,
                "accion": accion,
                "motivo": motivo,
            }
            detalles.append(detalle)
        
        # Imprimir resumen
        print("=" * 80)
        print("RESUMEN DRY-RUN")
        print("=" * 80)
        print(f"Total libros analizados:     {stats['total']}")
        print(f"  -> REPAGINAR:              {stats['reprocesar']}")
        print(f"  -> EXCLUIDOS (total):      {stats['total'] - stats['reprocesar']}")
        print(f"     - Protegido (ID 18):     {stats['excluido_protegido']}")
        print(f"     - Placeholder/Vacío:     {stats['excluido_placeholder']}")
        print(f"     - Patológico/Basura:     {stats['excluido_patologico']}")
        print(f"     - Contenido corto:       {stats['excluido_corto']}")
        print(f"     - Errores validación:    {stats['excluido_errores']}")
        print(f"     - Duplicado exacto:      {stats['excluido_duplicado']}")
        print(f"     - Ya válido:             {stats['excluido_ya_valido']}")
        print()
        
        # Imprimir detalles de los que se repaginarían
        print("=" * 80)
        print("LIBROS QUE SE REPAGINARÍAN (DRY-RUN)")
        print("=" * 80)
        for d in detalles:
            if d["accion"] == "REPAGINAR":
                print(f"  ID={d['id']:3d} | '{d['titulo'][:50]:50s}' | page_count={d['page_count_actual']:3d} | book_pages={d['book_pages_actuales']:3d} | generarian={d['paginas_que_generarian']:3d} | {d['motivo']}")
        
        print()
        print("=" * 80)
        print("LIBROS EXCLUIDOS (muestra)")
        print("=" * 80)
        for d in detalles:
            if d["accion"] == "EXCLUIR":
                motivo_corto = d["motivo"][:80]
                print(f"  ID={d['id']:3d} | '{d['titulo'][:50]:50s}' | page_count={d['page_count_actual']:3d} | book_pages={d['book_pages_actuales']:3d} | {motivo_corto}")
        
        # Verificación específica de El Principito
        print()
        print("=" * 80)
        print("VERIFICACIÓN ESPECÍFICA: EL PRINCIPITO")
        print("=" * 80)
        for d in detalles:
            if d["id"] in [18, 128]:
                print(f"  ID={d['id']} | '{d['titulo']}' | page_count={d['page_count_actual']} | book_pages={d['book_pages_actuales']} | content_len={d['content_length']} | accion={d['accion']} | {d['motivo']}")
        
        # Guardar resultado para revisión
        output = {
            "stats": stats,
            "detalles": detalles,
            "duplicados_ids": list(duplicados),
        }
        with open("dry_run_result.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        print()
        print("Resultado guardado en dry_run_result.json")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()