# -*- coding: utf-8 -*-
"""
DRY-RUN de repaginación segura basado en clasificación del diagnóstico.
Usa los resultados de diag_catalog.py (clasificación FINAL) para decidir.
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
    
    # Reconstruir libros con clasificación FINAL usando la lógica de diag_catalog.py
    # Primero, obtenemos todos los IDs de libros (1-163 publicados + algunos más)
    total_published = 163  # según books_published_status
    
    # Información que tenemos del snapshot
    # 1. el_principito_results: IDs 18 y 128
    # 2. duplicate_title_author: 13 grupos
    # 3. identical_book_content: 35 libros con placeholder (IDs 133-170)
    # 4. repeated_paragraphs: libros con contenido fabricado (patológico)
    # 5. books_suspicious_content: IDs 145, 158
    # 6. near_identical_content: pares con contenido casi idéntico
    
    # IDs con placeholder exacto
    placeholder_ids = set()
    for item in diag['identical_book_content']:
        if item['content'].strip() == lectura.CONTENIDO_NO_DISPONIBLE:
            placeholder_ids.update(item['ids'])
    
    # IDs con contenido fabricado (párrafo repetido >= 200)
    fabricados_ids = {}
    for item in diag['repeated_paragraphs']:
        if item['n'] >= 200:
            fabricados_ids[item['book_id']] = {'n': item['n'], 'title': item['title']}
    
    # IDs con contenido sospechoso
    suspicious_ids = {item['id'] for item in diag['books_suspicious_content']}
    
    # IDs duplicados exactos
    duplicados_ids = set()
    for item in diag['duplicate_title_author']:
        duplicados_ids.update(item['ids'])
    
    # El Principito IDs
    el_principito_ids = {item['id'] for item in diag['el_principito_results']}
    
    # Rango de seeds (5-130)
    RANGO_SEEDS = set(range(5, 131))
    
    # Construir lista de libros
    libros = []
    for bid in range(1, total_published + 1):
        # Información básica
        title = f'Libro {bid}'
        author = ''
        page_count = None
        content_length = None
        is_seed = bid in RANGO_SEEDS
        is_placeholder = bid in placeholder_ids
        is_fabricado = bid in fabricados_ids
        is_suspicious = bid in suspicious_ids
        is_duplicado = bid in duplicados_ids
        is_principito = bid in el_principito_ids
        is_protegido = (bid == 18)
        
        # Datos específicos del snapshot
        if is_principito:
            for item in diag['el_principito_results']:
                if item['id'] == bid:
                    title = item['title']
                    author = item['author_name']
                    page_count = item['page_count']
                    content_length = item['content_length']
                    break
        elif is_fabricado:
            title = fabricados_ids[bid]['title']
            # Estimar content_length basado en párrafo repetido
            content_length = 10000  # aprox
        elif is_placeholder:
            content_length = len(lectura.CONTENIDO_NO_DISPONIBLE)
        elif is_suspicious:
            for item in diag['books_suspicious_content']:
                if item['id'] == bid:
                    title = item['title']
                    break
            content_length = 50000  # aprox
        elif is_seed:
            # Estos son libros reales de seed_books.py
            content_length = 50000  # aprox obra completa
        
        # Clasificación FINAL según reglas de diag_catalog.py
        if is_protegido:
            clasificacion = "SALVAR"  # ID 18 protegido, no tocar
            fuente = "PROTEGIDO"
            motivo = "Libro protegido (ID 18 - El Principito original)"
            accion = "EXCLUIR"
        elif is_placeholder:
            # Sin PDF físico (modo snapshot) -> REVISAR
            # Con PDF físico -> REPROCESAR_DESDE_PDF
            # Sin PDF y sin otra fuente -> ELIMINAR
            clasificacion = "REVISAR"  # modo snapshot
            fuente = None
            motivo = "Contenido placeholder; requiere verificación física de PDF"
            accion = "EXCLUIR"
        elif is_fabricado:
            if is_seed:
                # Seed book con patrón fabricado x200 pero fuente real en repo
                clasificacion = "REPROCESAR_DESDE_CONTENIDO"
                fuente = "seed_books.py"
                motivo = "Contenido sembrado (seed_books.py, obra real) con paginación patológica; reprocesar desde books.content"
                accion = "REPAGINAR"
            else:
                # Fabricado sin fuente verificable
                clasificacion = "REVISAR"  # modo snapshot
                fuente = None
                motivo = "Contenido fabricado/basura; requiere verificación física de PDF"
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
        elif is_seed:
            # Seed book con contenido real, pero page_count puede estar mal
            # Según snapshot: page_count_vs_max_page está vacío, pero la migración Fase 2
            # debería haber creado book_pages. Asumimos que necesitan repaginación.
            clasificacion = "REPROCESAR_DESDE_CONTENIDO"
            fuente = "seed_books.py / books.content"
            motivo = "Obra real de dominio público (seed_books.py); reprocesar paginación/capítulos desde books.content"
            accion = "REPAGINAR"
        else:
            # Otros libros (1-4, 131-132, etc.) - sin datos suficientes
            clasificacion = "REVISAR"
            fuente = None
            motivo = "Sin datos suficientes en snapshot para clasificar"
            accion = "EXCLUIR"
        
        # Estimar páginas que se generarían
        if is_seed and not is_fabricado and not is_placeholder:
            paginas_estimadas = 150  # típico para novela
        elif is_fabricado:
            paginas_estimadas = 1  # contenido repetido -> 1 página
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
            'is_fabricado': is_fabricado,
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
            key = l['motivo'][:50]
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
    print("LIBROS QUE SE REPAGINARÍAN")
    print("=" * 80)
    for l in libros:
        if l['accion'] == 'REPAGINAR':
            print(f"  ID={l['id']:3d} | '{l['title'][:55]:55s}' | page_count={l['page_count'] or 'N/A':>5} | est_paginas={l['paginas_estimadas']:3d} | {l['motivo'][:70]}")
    
    # Detalle de EXCLUIR (primeros 30)
    print()
    print("=" * 80)
    print("LIBROS EXCLUIDOS (primeros 30)")
    print("=" * 80)
    count = 0
    for l in libros:
        if l['accion'] == 'EXCLUIR' and count < 30:
            print(f"  ID={l['id']:3d} | '{l['title'][:55]:55s}' | page_count={l['page_count'] or 'N/A':>5} | {l['motivo'][:70]}")
            count += 1
    
    # Verificación específica El Principito
    print()
    print("=" * 80)
    print("VERIFICACIÓN: EL PRINCIPITO (IDs 18 y 128)")
    print("=" * 80)
    for l in libros:
        if l['id'] in [18, 128]:
            print(f"  ID={l['id']} | '{l['title']}' | page_count={l['page_count']} | content_len={l['content_length']} | clasif={l['clasificacion']} | accion={l['accion']} | {l['motivo']}")
    
    # ID 128 ya eliminado - verificar que no está en la lista
    print()
    print(f"ID 128 en lista actual: {128 in [l['id'] for l in libros]}")
    if 128 in [l['id'] for l in libros]:
        print("  ADVERTENCIA: ID 128 todavía aparece en el catálogo (debería estar eliminado)")
    
    # Guardar resultado
    output = {
        "stats": stats,
        "libros": libros,
        "placeholder_ids": list(placeholder_ids),
        "fabricados_ids": list(fabricados_ids.keys()),
        "suspicious_ids": list(suspicious_ids),
        "duplicados_ids": list(duplicados_ids),
        "principito_ids": list(el_principito_ids),
    }
    with open("dry_run_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print()
    print("Resultado guardado en dry_run_result.json")


if __name__ == "__main__":
    main()