#!/usr/bin/env python3
"""
AUDITORIA SIMPLE PARA RENDER SHELL
Ejecutar: python render_audit_simple.py
SOLO LECTURA - NO modifica produccion
"""
import os
import sys
import json

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 no disponible. Instalar con: pip install psycopg2-binary")
    sys.exit(1)

# Importar configuración centralizada de storage
from storage_config import STORAGE_DIR, STORAGE_BOOKS

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL no encontrado en variables de entorno")
    sys.exit(1)

print("=" * 70)
print("AUDITORIA SIMPLE - AeternumLibrary")
print("Modo: SOLO LECTURA | NO modifica produccion")
print("=" * 70)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 1. Contar total de libros
cur.execute("SELECT COUNT(*) FROM books")
total = cur.fetchone()[0]
print(f"\nTotal libros en produccion: {total}")

# 2. Obtener TODOS los libros
cur.execute("""
    SELECT id, title, author, content, pdf_path, 
           LENGTH(content) as content_len,
           created_at
    FROM books 
    ORDER BY id
""")
all_books = cur.fetchall()

# 3. Verificar PDFs fisicos
pdf_files = set()
if os.path.exists(STORAGE_BOOKS):
    pdf_files = set(os.listdir(STORAGE_BOOKS))
print(f"PDFs fisicos en disco: {len(pdf_files)}")

# 4. Analizar cada libro
results = []
for book in all_books:
    bid, title, author, content, pdf_path, content_len, created_at = book
    
    # Detectar contenido problematico
    problems = []
    if content:
        if content_len < 50:
            problems.append("MUY_CORTO")
        if "Contenido de texto no disponible" in content:
            problems.append("PLACEHOLDER")
        if content_len > 50000:
            # Contar repeticiones de parrafos
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
            if len(paragraphs) > 10:
                unique = len(set(paragraphs[:20]))
                if unique <= 3:
                    problems.append("FABRICADO")
    
    # Verificar si el PDF existe fisicamente
    pdf_existe = False
    if pdf_path:
        fname = os.path.basename(pdf_path)
        pdf_existe = fname in pdf_files
    
    results.append({
        'id': bid,
        'title': title,
        'author': author,
        'content_len': content_len or 0,
        'pdf_path': pdf_path,
        'pdf_existe': pdf_existe,
        'problems': problems,
        'created_at': str(created_at) if created_at else None
    })
    
    # Mostrar IDs criticos
    if bid in [172, 173, 175]:
        print(f"\n*** ID {bid} ***")
        print(f"  Titulo: {title}")
        print(f"  Autor: {author}")
        print(f"  Content length: {content_len}")
        print(f"  PDF path: {pdf_path}")
        print(f"  PDF existe: {pdf_existe}")
        print(f"  Problemas: {problems}")

# 5. Guardar resultado
output = {
    'total_libros': total,
    'total_analizados': len(results),
    'pdfs_fisicos': len(pdf_files),
    'ids_encontrados': [r['id'] for r in results],
    'ids_172_173_175_presentes': {
        '172': any(r['id'] == 172 for r in results),
        '173': any(r['id'] == 173 for r in results),
        '175': any(r['id'] == 175 for r in results)
    },
    'books': results
}

# Guardar en archivo
output_path = os.path.join(os.path.dirname(__file__), 'render_audit_result.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n{'=' * 70}")
print("RESUMEN")
print(f"{'=' * 70}")
print(f"Total libros: {total}")
print(f"Analizados: {len(results)}")
print(f"PDFs fisicos: {len(pdf_files)}")
print(f"\nIDs 172, 173, 175 presentes:")
for k, v in output['ids_172_173_175_presentes'].items():
    print(f"  ID {k}: {'SI' if v else 'NO'}")

# Contar problemas
from collections import Counter
prob_count = Counter()
for r in results:
    for p in r['problems']:
        prob_count[p] += 1
print(f"\nProblemas detectados:")
for prob, count in prob_count.most_common():
    print(f"  {prob}: {count}")

print(f"\nArchivo guardado: {output_path}")
print("\nPRODUCCION NO FUE MODIFICADA.")

cur.close()
conn.close()
