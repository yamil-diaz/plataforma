# -*- coding: utf-8 -*-
"""
DRY-RUN de repaginación segura usando snapshot (sin BD).
"""
import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import lectura


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


def _es_seed(book_id):
    """Verifica si es un libro sembrado (IDs 5-130 en seed_books.py)."""
    return book_id in range(5, 131)


def _tiene_paginacion_valida(page_count, n_book_pages):
    """Verifica si el libro ya tiene paginación válida y consistente."""
    page_count = page_count or 0
    return page_count > 0 and n_book_pages > 0 and page_count == n_book_pages


def _debe_repaginar(book_id, page_count, n_book_pages, info_contenido, duplicados_ids):
    """Determina si un libro debe ser repaginado."""
    
    # 1. Libro protegido (ID 18 - El Principito original)
    if book_id == 18:
        return False, "EXCLUIDO: Libro protegido (ID 18 - El Principito original)"
    
    # 2. Contenido placeholder/vacío
    if info_contenido["placeholder"] or info_contenido["vacío"]:
        return False, "EXCLUIDO: Contenido placeholder o vacío"
    
    # 3. Contenido patológico o basura
    if info_contenido["pathological"] or info_contenido["basura"]:
        if _es_seed(book_id):
            return True, "REPAGINAR: Seed book con paginación patológica (fuente: seed_books.py)"
        return False, "EXCLUIDO: Contenido patológico/basura sin fuente verificable"
    
    # 4. Contenido muy corto
    if info_contenido["content_length"] is not None and info_contenido["content_length"] < lectura.MIN_CONTENIDO_TOTAL:
        return False, f"EXCLUIDO: Contenido insuficiente ({info_contenido['content_length']} chars < {lectura.MIN_CONTENIDO_TOTAL})"
    
    # 5. Errores de validación
    if info_contenido["errors"]:
        return False, f"EXCLUIDO: Errores de validación: {'; '.join(info_contenido['errors'])}"
    
    # 6. Libro duplicado exacto
    if book_id in duplicados_ids:
        return False, "EXCLUIDO: Duplicado exacto (requiere decisión manual)"
    
    # 7. Ya tiene paginación válida
    if _tiene_paginacion_valida(page_count, n_book_pages):
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
    print("DRY-RUN DE REPAGINACIÓN SEGURA - AETERNUM LIBRARY (desde snapshot)")
    print("=" * 80)
    print()
    
    # Cargar snapshot
    with open('diag_result.json', 'r', encoding='utf-16') as f:
        snapshot = json.load(f)
    
    diag = snapshot['diagnosis']
    
    # Reconstruir lista de libros desde el snapshot
    # Usamos page_count_vs_max_page (vacío según snapshot, pero tenemos el_principito_results y otras tablas)
    # Usamos row_counts y otras consultas para reconstruir
    
    # Primero, obtener todos los IDs de libros del snapshot
    # Usamos near_identical_content, duplicate_title_author, el_principito_results, books_suspicious_content, repeated_paragraphs
    # Pero la mejor fuente sería el conteo total de libros publicados (163)
    
    # Vamos a reconstruir desde los datos que tenemos
    libros_dict = {}
    
    # IDs conocidos de el_principito_results
    for item in diag['el_principito_results']:
        libros_dict[item['id']] = {
            'id': item['id'],
            'title': item['title'],
            'author_name': item['author_name'],
            'page_count': item['page_count'],
            'published': item['published'],
            'content_length': item['content_length'],
            'content': None,  # No tenemos el contenido real en el snapshot
        }
    
    # IDs de repeated_paragraphs
    for item in diag['repeated_paragraphs']:
        if item['book_id'] not in libros_dict:
            libros_dict[item['book_id']] = {
                'id': item['book_id'],
                'title': item['title'],
                'author_name': '',
                'page_count': None,
                'published': 1,
                'content_length': None,
                'content': None,
            }
    
    # IDs de books_suspicious_content
    for item in diag['books_suspicious_content']:
        if item['id'] not in libros_dict:
            libros_dict[item['id']] = {
                'id': item['id'],
                'title': item['title'],
                'author_name': '',
                'page_count': None,
                'published': 1,
                'content_length': None,
                'content': None,
            }
    
    # IDs de duplicate_title_author
    for item in diag['duplicate_title_author']:
        for bid in item['ids']:
            if bid not in libros_dict:
                libros_dict[bid] = {
                    'id': bid,
                    'title': item['title'],
                    'author_name': item['author_name'],
                    'page_count': None,
                    'published': 1,
                    'content_length': None,
                    'content': None,
                }
    
    # IDs de identical_book_content (placeholder books)
    for item in diag['identical_book_content']:
        for i, bid in enumerate(item['ids']):
            if bid not in libros_dict:
                libros_dict[bid] = {
                    'id': bid,
                    'title': item['titles'][i],
                    'author_name': '',
                    'page_count': None,
                    'published': 1,
                    'content_length': len(item['content']),
                    'content': item['content'],
                }
    
    # Agregar IDs del 1 al 163 (total publicados según snapshot)
    # Para los que no tenemos datos, usamos valores por defecto
    for bid in range(1, 164):
        if bid not in libros_dict:
            libros_dict[bid] = {
                'id': bid,
                'title': f'(sin datos en snapshot ID {bid})',
                'author_name': '',
                'page_count': None,
                'published': 1,
                'content_length': None,
                'content': None,
            }
    
    libros = [libros_dict[k] for k in sorted(libros_dict.keys())]
    
    # Detectar duplicados exactos
    duplicados = set()
    for item in diag['duplicate_title_author']:
        for bid in item['ids']:
            duplicados.add(bid)
    
    # Para n_book_pages y n_chapters, usamos datos del snapshot si existen
    # Como no los tenemos en el snapshot, asumimos 0 para los que no sabemos
    # En la BD real, la migración Fase 2 debería haber creado book_pages
    # Pero según el diagnóstico, page_count_vs_max_page está vacío, lo que sugiere
    # que o no hay book_pages o page_count coincide con max_page
    
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
        n_book_pages = 0  # No tenemos este dato en el snapshot
        page_count = book.get("page_count")
        
        # Decisión
        debe, motivo = _debe_repaginar(libro_id, page_count, n_book_pages, info, duplicados)
        
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
            "page_count_actual": page_count,
            "book_pages_actuales": n_book_pages,
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
            print(f"  ID={d['id']:3d} | '{d['titulo'][:50]:50s}' | page_count={d['page_count_actual'] or 'N/A':>5} | generarian={d['paginas_que_generarian']:3d} | {d['motivo']}")
    
    print()
    print("=" * 80)
    print("LIBROS EXCLUIDOS (muestra - primeros 50)")
    print("=" * 80)
    count = 0
    for d in detalles:
        if d["accion"] == "EXCLUIR" and count < 50:
            motivo_corto = d["motivo"][:80]
            print(f"  ID={d['id']:3d} | '{d['titulo'][:50]:50s}' | page_count={d['page_count_actual'] or 'N/A':>5} | {motivo_corto}")
            count += 1
    
    # Verificación específica de El Principito
    print()
    print("=" * 80)
    print("VERIFICACIÓN ESPECÍFICA: EL PRINCIPITO")
    print("=" * 80)
    for d in detalles:
        if d["id"] in [18, 128]:
            print(f"  ID={d['id']} | '{d['titulo']}' | page_count={d['page_count_actual']} | content_len={d['content_length']} | accion={d['accion']} | {d['motivo']}")
    
    # Guardar resultado para revisión
    output = {
        "stats": stats,
        "detalles": detalles,
        "duplicados_ids": list(duplicados),
        "nota": "Basado en snapshot diag_result.json. n_book_pages=0 asumido por falta de datos en snapshot."
    }
    with open("dry_run_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print()
    print("Resultado guardado en dry_run_result.json")


if __name__ == "__main__":
    main()