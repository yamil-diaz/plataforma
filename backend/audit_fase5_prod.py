# -*- coding: utf-8 -*-
"""
FASE 5 — VERIFICACIÓN POST-IMPORTACIÓN DEL PILOTO (Producción)
Script de auditoría de solo lectura que consulta la API de producción.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import hashlib
from datetime import datetime

PRODUCTION_URL = "https://aeternum-world.onrender.com"
EXPECTED_SHA256 = "ec07703ef40d687a9ac2e632d027b7b9b6051eb098c5abf7985e4176903ec854"

HISTORICAL_FILES = [
    "4400ba09-c36c-42bc-b5b8-1037fc520e7c_91.pdf",
    "80ad2a2e-e7a5-44e5-b76c-cd570cada258_84.pdf",
    "94959e31-ce67-4054-8494-659cb843fec4_rayuelas mentales.pdf",
    "66627525-21b0-48f6-8ef0-05ef72d509bc_imagen_2026-08-18_193231941.png"
]

PLACEHOLDER = "Contenido de texto no disponible."

def api_get(path):
    """GET request a la API de producción."""
    url = f"{PRODUCTION_URL}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return resp.status, data
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body
    except Exception as e:
        return None, str(e)

def calculate_sha256_from_url(url):
    """Calcula SHA-256 descargando el PDF desde la URL."""
    h = hashlib.sha256()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest(), True
    except Exception as e:
        return str(e), False

def run_audit():
    print("=" * 70)
    print("FASE 5 — VERIFICACIÓN POST-IMPORTACIÓN DEL PILOTO (PRODUCCIÓN)")
    print(f"Fecha: {datetime.now().isoformat()}")
    print(f"URL Producción: {PRODUCTION_URL}")
    print("=" * 70)
    
    results = {}
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 5 — API
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 5 — API (PRODUCCIÓN)")
    print("=" * 70)
    
    # GET /api/books
    status, data = api_get("/api/books")
    print(f"\nGET /api/books -> HTTP {status}")
    results['api_list_status'] = status
    
    if status == 200 and isinstance(data, list):
        books = data
        results['api_books_count'] = len(books)
        print(f"  Total libros publicados: {len(books)}")
        
        # Find pilot book
        pilot = None
        for b in books:
            title = b.get('title', '')
            if 'rayuela' in title.lower():
                pilot = b
                break
        
        if pilot:
            book_id = pilot.get('id')
            results['pilot_id'] = book_id
            results['pilot_title'] = pilot.get('title')
            results['pilot_author'] = pilot.get('author_name')
            results['pilot_page_count'] = pilot.get('page_count')
            results['pilot_published'] = pilot.get('published')
            results['pilot_pdf_path'] = pilot.get('pdf_path')
            
            print(f"\n  [OK] Libro piloto encontrado:")
            print(f"    ID: {book_id}")
            print(f"    Título: {pilot.get('title')}")
            print(f"    Autor: {pilot.get('author_name')}")
            print(f"    page_count: {pilot.get('page_count')}")
            print(f"    published: {pilot.get('published')}")
            print(f"    pdf_path: {pilot.get('pdf_path')}")
            print(f"    views: {pilot.get('views')}")
            
            # GET /api/books/{id} - detail
            status_detail, detail = api_get(f"/api/books/{book_id}")
            print(f"\n  GET /api/books/{book_id} -> HTTP {status_detail}")
            results['api_detail_status'] = status_detail
            
            if status_detail == 200:
                print(f"    [OK] Detalle obtenido correctamente")
            
            # GET /api/books/{id}/chapters
            status_ch, chapters = api_get(f"/api/books/{book_id}/chapters")
            print(f"\n  GET /api/books/{book_id}/chapters -> HTTP {status_ch}")
            results['api_chapters_status'] = status_ch
            if status_ch == 200:
                results['api_chapters_count'] = len(chapters) if isinstance(chapters, list) else 0
                print(f"    Capítulos: {results['api_chapters_count']}")
            
            # GET pages 1 through page_count
            page_count = pilot.get('page_count', 0)
            page_contents = []
            page_errors = []
            placeholder_count = 0
            unique_contents = set()
            min_len = float('inf')
            max_len = 0
            total_len = 0
            
            if page_count > 0:
                print(f"\n  Verificando {page_count} páginas vía API...")
                for p in range(1, page_count + 1):
                    status_page, page_data = api_get(f"/api/books/{book_id}/pages/{p}")
                    if status_page == 200 and isinstance(page_data, dict):
                        content = page_data.get('content', '')
                        page_contents.append({'page': p, 'content': content, 'length': len(content)})
                        unique_contents.add(content)
                        
                        if content.strip() == PLACEHOLDER:
                            placeholder_count += 1
                        
                        min_len = min(min_len, len(content))
                        max_len = max(max_len, len(content))
                        total_len += len(content)
                        
                        if p % 10 == 0 or p == page_count:
                            print(f"    Página {p}/{page_count}: {len(content)} chars")
                    else:
                        page_errors.append({'page': p, 'status': status_page, 'data': page_data})
                        print(f"    Página {p}: ERROR HTTP {status_page}")
                
                results['total_pages_fetched'] = len(page_contents)
                results['page_fetch_errors'] = len(page_errors)
                results['unique_contents'] = len(unique_contents)
                results['all_same_content'] = len(unique_contents) == 1
                results['placeholder_count'] = placeholder_count
                results['min_content_len'] = min_len if min_len != float('inf') else 0
                results['max_content_len'] = max_len
                results['avg_content_len'] = total_len / len(page_contents) if page_contents else 0
                
                print(f"\n  Resumen de contenido:")
                print(f"    Páginas obtenidas: {len(page_contents)}/{page_count}")
                print(f"    Errores: {len(page_errors)}")
                print(f"    Contenidos únicos: {len(unique_contents)}")
                print(f"    Todas iguales: {'SÍ' if results['all_same_content'] else 'NO'}")
                print(f"    Placeholder: {placeholder_count}")
                print(f"    Longitud mín: {results['min_content_len']}")
                print(f"    Longitud máx: {results['max_content_len']}")
                print(f"    Longitud prom: {results['avg_content_len']:.2f}")
                
                # Show first 200 chars of each unique content
                if not results['all_same_content'] and len(unique_contents) <= 20:
                    print(f"\n  Muestras de contenido único:")
                    for i, c in enumerate(list(unique_contents)[:5]):
                        print(f"    [{i+1}] {c[:200]}...")
                
                # Show first and last page content snippet
                if page_contents:
                    print(f"\n  Página 1 (primeros 300 chars):")
                    print(f"    {page_contents[0]['content'][:300]}")
                    print(f"\n  Página {page_count} (primeros 300 chars):")
                    print(f"    {page_contents[-1]['content'][:300]}")
            else:
                print(f"    page_count = 0, no se pueden verificar páginas")
                results['total_pages_fetched'] = 0
            
            # Download endpoint (check headers only, don't save)
            pdf_url = f"{PRODUCTION_URL}/api/books/{book_id}/download"
            print(f"\n  Verificando endpoint de descarga...")
            try:
                req = urllib.request.Request(pdf_url)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    results['download_status'] = resp.status
                    content_type = resp.headers.get('Content-Type', '')
                    content_disp = resp.headers.get('Content-Disposition', '')
                    content_length = resp.headers.get('Content-Length', 'unknown')
                    results['download_content_type'] = content_type
                    results['download_content_length'] = content_length
                    print(f"    HTTP {resp.status}")
                    print(f"    Content-Type: {content_type}")
                    print(f"    Content-Disposition: {content_disp}")
                    print(f"    Content-Length: {content_length}")
                    
                    # Calculate SHA-256 from download
                    h = hashlib.sha256()
                    total_read = 0
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        h.update(chunk)
                        total_read += len(chunk)
                    sha256_download = h.hexdigest()
                    results['sha256_from_download'] = sha256_download
                    results['sha256_match'] = sha256_download == EXPECTED_SHA256
                    print(f"    SHA-256: {sha256_download}")
                    print(f"    SHA-256 esperado: {EXPECTED_SHA256}")
                    print(f"    SHA-256 coincide: {'SÍ' if results['sha256_match'] else 'NO'}")
                    print(f"    Bytes descargados: {total_read}")
            except Exception as e:
                print(f"    Error: {e}")
                results['download_error'] = str(e)
        else:
            print(f"\n  [FAIL] Libro 'rayuela' NO encontrado en listado de la API")
            print(f"  Libros disponibles:")
            for b in books:
                print(f"    - [{b.get('id')}] {b.get('title')} ({b.get('author_name')})")
    else:
        print(f"  Error al obtener listado: {data}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 6 — FRONTEND
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 6 — FRONTEND")
    print("=" * 70)
    
    # Check if frontend is accessible
    status_frontend, _ = api_get("/")
    print(f"GET / -> HTTP {status_frontend}")
    results['frontend_status'] = status_frontend
    
    print(f"\n  NOTA: La verificación visual del frontend (catálogo, lector,")
    print(f"  navegación entre páginas, contenido repetido, placeholder)")
    print(f"  NO ES VERIFICABLE desde OpenCode.")
    print(f"  Se requiere inspección manual en el navegador.")
    results['frontend_manual'] = "NO VERIFICABLE desde OpenCode"
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 7 — DATOS NO RELACIONADOS (no accesible vía API pública)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 7 — DATOS NO RELACIONADOS")
    print("=" * 70)
    print(f"\n  NOTA: Las tablas users, rayos_transactions, forum_posts,")
    print(f"  reviews, competitions NO son accesibles vía API pública.")
    print(f"  Requieren acceso directo a PostgreSQL (solo desde Render).")
    print(f"  Se puede verificar que el listado de libros de la API solo")
    print(f"  muestra libros publicados y no hay datos extraños.")
    
    # Check other public endpoints don't show anomalies
    status_users_me, _ = api_get("/api/users/me")
    print(f"\n  GET /api/users/me (sin auth): HTTP {status_users_me}")
    results['users_me_no_auth'] = status_users_me
    
    # ═══════════════════════════════════════════════════════════════════════
    # RESUMEN
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("DATOS CAPTURADOS PARA EL INFORME FINAL")
    print("=" * 70)
    
    # Save results
    output_path = os.path.join(os.path.dirname(__file__), 'audit_fase5_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResultados guardados en: {output_path}")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    return results

if __name__ == "__main__":
    run_audit()