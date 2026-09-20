# -*- coding: utf-8 -*-
"""
DRY-RUN de repaginación segura basado en clasificación del diagnóstico.
Versión corregida.
"""
import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import lectura


def main():
    print("=" * 80)
    print("DRY-RUN DE REPAGINACIÓN SEGURA - AETERNUM LIBRARY")
    print("Basado en clasificación FINAL de diag_catalog.py")
    print("=" * 80)
    print()
    
    # Cargar snapshot
    with open('diag_result.json', 'r', encoding='utf-16') as f:
        snapshot = json.load(f)
    
    diag = snapshot['diagnosis']
    
    # Total libros publicados
    total_published = 163
    
    # Información del snapshot
    # IDs con placeholder exacto
    placeholder_ids = set()
    for item in diag['identical_book_content']:
        if item['content'].strip() == lectura.CONTENIDO_NO_DISPONIBLE:
            placeholder_ids.update(item['ids'])
    
    # IDs con contenido fabricado (párrafo repetido >= 200) - PERO no seeds
    fabricados_info = {}
    for item in diag['repeated_paragraphs']:
        if item['n'] >= 200:
            fabricados_info[item['book_id']] = {'n': item['n'], 'title': item['title']}
    
    # IDs con contenido sospechoso
    suspicious_ids = {item['id'] for item in diag['books_suspicious_content']}
    
    # IDs duplicados exactos
    duplicados_ids = set()
    for item in diag['duplicate_title_author']:
        duplicados_ids.update(item['ids'])
    
    # El Principito IDs
    el_principito_info = {item['id']: item for item in diag['el_principito_results']}
    
    # Rango de seeds (5-130)
    RANGO_SEEDS = set(range(5, 131))
    
    # IDs que son fabricados PERO también seeds (contenido real con patrón detectado)
    fabricados_que_son_seeds = {bid for bid in fabricados_info if bid in RANGO_SEEDS}
    fabricados_sin_fuente = {bid for bid in fabricados_info if bid not in RANGO_SEEDS}
    
    print(f"Placeholder IDs: {sorted(placeholder_ids)}")
    print(f"Fabricados (todos): {sorted(fabricados_info.keys())}")
    print(f"Fabricados que SON seeds: {sorted(fabricados_que_son_seeds)}")
    print(f"Fabricados SIN fuente: {sorted(fabricados_sin_fuente)}")
    print(f"Suspicious IDs: {sorted(suspicious_ids)}")
    print(f"Duplicados IDs: {sorted(duplicados_ids)}")
    print(f"El Principito: {el_principito_info}")
    print()
    
    # Construir lista de libros
    libros = []
    for bid in range(1, total_published + 1):
        is_seed = bid in RANGO_SEEDS
        is_placeholder = bid in placeholder_ids
        is_fabricado_sin_fuente = bid in fabricados_sin_fuente
        is_fabricado_seed = bid in fabricados_que_son_seeds
        is_suspicious = bid in suspicious_ids
        is_duplicado = bid in duplicados_ids
        is_principito = bid in el_principito_info
        is_protegido = (bid == 18)
        
        # Datos base
        title = f'Libro {bid}'
        author = ''
        page_count = None
        content_length = None
        
        # Datos específicos
        if is_principito:
            item = el_principito_info[bid]
            title = item['title']
            author = item['author_name']
            page_count = item['page_count']
            content_length = item['content_length']
        elif is_fabricado_sin_fuente:
            item = fabricados_info[bid]
            title = item['title']
            content_length = 10000
        elif is_placeholder:
            content_length = len(lectura.CONTENIDO_NO_DISPONIBLE)
        elif is_suspicious:
            for item in diag['books_suspicious_content']:
                if item['id'] == bid:
                    title = item['title']
                    break
            content_length = 50000
        elif is_fabricado_seed:
            # Seed book con patrón detectado pero contenido REAL
            content_length = 50000
        elif is_seed:
            content_length = 50000
        
        # Clasificación FINAL
        if is_protegido:
            clasificacion = "SALVAR"
            fuente = "PROTEGIDO"
            motivo = "Libro protegido (ID 18 - El Principito original)"
            accion = "EXCLUIR"
        elif is_placeholder:
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Contenido placeholder; requiere verificación física de PDF"
            accion = "EXCLUIR"
        elif is_fabricado_sin_fuente:
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Contenido fabricado/basura sin fuente verificable; requiere verificación física de PDF"
            accion = "EXCLUIR"
        elif is_suspicious:
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Contenido con anomalías (books_suspicious_content)"
            accion = "EXCLUIR"
        elif is_duplicado and not is_protegido:
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Duplicado exacto (requiere decisión manual)"
            accion = "EXCLUIR"
        elif is_fabricado_seed or is_seed:
            # Seed book con contenido REAL (obra de dominio público)
            # La migración Fase 2 debería haber creado book_pages, pero page_count puede estar mal
            clasificacion = "REPROCESAR_DESDE_CONTENIDO"
            fuente = "seed_books.py / books.content"
            if is_fabricado_seed:
                motivo = "Obra real (seed_books.py) con patrón patológico detectado; reprocesar paginación/capítulos desde books.content"
            else:
                motivo = "Obra real de dominio público (seed_books.py); reprocesar paginación/capítulos desde books.content"
            accion = "REPAGINAR"
        else:
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Sin datos suficientes en snapshot para clasificar"
            accion = "EXCLUIR"
        
        # Estimar páginas que se generarían
        if is_fabricado_seed or is_seed:
            paginas_estimadas = 150
        elif is_fabricado_sin_fuente:
            paginas_estimadas = 1
        elif is_placeholder:
            paginas_estimadas = 1
        else:
            paginas_estimadas = 50
        
        libros.append({
            'id': bid,
            'title': title,
            'author': author,
            'page_count': page_count,
            'content_length': content_length,
            'is_seed': is_seed,
            'is_placeholder': is_placeholder,
            'is_fabricado_sin_fuente': is_fabricado_sin_fuente,
            'is_fabricado_seed': is_fabricado_seed,
            'is_suspicious': is_suspicious,
            'is_duplicado': is_duplicado,
            'is_principito': is_principito,
            'is_protegido': is_protegido,
            'clasificacion': clasificacion,
            'fuente': fuente,
            'motivo': motivo,
            'accion': accion,
            'paginas_estimadas': paginas_estimadas,
        })
    
    # Estadísticas
    stats = {
        "total": len(libros),
        "reprocesar": sum(1 for l in libros if l['accion'] == 'REPAGINAR'),
        "excluir": sum(1 for l in libros if l['accion'] == 'EXCLUIR'),
    }
    
    excluidos_por_motivo = {}
    for l in libros:
        if l['accion'] == 'EXCLUIR':
            key = l['motivo'][:60]
            excluidos_por_motivo[key] = excluidos_por_motivo.get(key, 0) + 1
    
    print(f"Total libros publicados: {stats['total']}")
    print(f"  -> REPAGINAR:  {stats['reprocesar']}")
    print(f"  -> EXCLUIR:    {stats['excluir']}")
    print()
    for motivo, count in sorted(excluidos_por_motivo.items(), key=lambda x: -x[1]):
        print(f"     - {motivo}: {count}")
    print()
    
    # Detalle de REPAGINAR
    print("=" * 80)
    print("LIBROS QUE SE REPAGINARÍAN (DRY-RUN)")
    print("=" * 80)
    for l in libros:
        if l['accion'] == 'REPAGINAR':
            print(f"  ID={l['id']:3d} | '{l['title'][:55]:55s}' | page_count={l['page_count'] or 'N/A':>5} | est_paginas={l['paginas_estimadas']:3d} | {l['motivo'][:70]}")
    
    # Detalle de EXCLUIR
    print()
    print("=" * 80)
    print("LIBROS EXCLUIDOS")
    print("=" * 80)
    for l in libros:
        if l['accion'] == 'EXCLUIR':
            print(f"  ID={l['id']:3d} | '{l['title'][:55]:55s}' | page_count={l['page_count'] or 'N/A':>5} | {l['motivo'][:70]}")
    
    # Verificación específica El Principito
    print()
    print("=" * 80)
    print("VERIFICACIÓN: EL PRINCIPITO (IDs 18 y 128)")
    print("=" * 80)
    for l in libros:
        if l['id'] in [18, 128]:
            print(f"  ID={l['id']} | '{l['title']}' | page_count={l['page_count']} | content_len={l['content_length']} | clasif={l['clasificacion']} | accion={l['accion']} | {l['motivo']}")
    
    # ID 128 ya eliminado
    print()
    print(f"ID 128 en lista actual (1-163): {128 <= total_published}")
    if 128 <= total_published:
        print("  NOTA: ID 128 debería haber sido eliminado (fuera del rango publicado actual)")
    
    # Guardar resultado
    output = {
        "stats": stats,
        "libros": libros,
        "placeholder_ids": list(placeholder_ids),
        "fabricados_sin_fuente_ids": list(fabricados_sin_fuente),
        "fabricados_seed_ids": list(fabricados_que_son_seeds),
        "suspicious_ids": list(suspicious_ids),
        "duplicados_ids": list(duplicados_ids),
        "principito_ids": list(el_principito_info.keys()),
    }
    with open("dry_run_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print()
    print("Resultado guardado en dry_run_result.json")


if __name__ == "__main__":
    main()