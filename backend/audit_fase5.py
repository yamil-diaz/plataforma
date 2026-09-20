# -*- coding: utf-8 -*-
"""
FASE 5 — VERIFICACIÓN POST-IMPORTACIÓN DEL PILOTO
Script de auditoría de solo lectura.
"""
import os
import sys
import hashlib
import json
from datetime import datetime

# Agregar directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras

# Cargar variables de entorno desde .env
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL no definida")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

STORAGE_BOOKS = os.path.join(os.path.dirname(__file__), '..', 'backend', 'storage', 'books')

EXPECTED_SHA256 = "ec07703ef40d687a9ac2e632d027b7b9b6051eb098c5abf7985e4176903ec854"

HISTORICAL_FILES = [
    "4400ba09-c36c-42bc-b5b8-1037fc520e7c_91.pdf",
    "80ad2a2e-e7a5-44e5-b76c-cd570cada258_84.pdf",
    "94959e31-ce67-4054-8494-659cb843fec4_rayuelas mentales.pdf",
    "66627525-21b0-48f6-8ef0-05ef72d509bc_imagen_2026-08-18_193231941.png"
]

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def calculate_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def get_pdf_page_count(file_path):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except:
        return -1

def run_audit():
    print("=" * 70)
    print("FASE 5 — VERIFICACIÓN POST-IMPORTACIÓN DEL PILOTO")
    print(f"Fecha: {datetime.now().isoformat()}")
    print("=" * 70)
    
    results = {}
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # ═══════════════════════════════════════════════════════════════════
        # VERIFICACIÓN 1 — DATABASE
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("VERIFICACIÓN 1 — DATABASE")
        print("=" * 70)
        
        # Books count
        cursor.execute("SELECT COUNT(*) as cnt FROM books")
        books_count = cursor.fetchone()['cnt']
        results['books_count'] = books_count
        print(f"\nbooks = {books_count}")
        
        # Book details
        cursor.execute("""
            SELECT id, title, author_name, pdf_path, page_count, published
            FROM books 
            ORDER BY id
        """)
        books = cursor.fetchall()
        print(f"\nDetalles de libros:")
        for book in books:
            print(f"  ID: {book['id']}")
            print(f"  Título: {book['title']}")
            print(f"  Autor: {book['author_name']}")
            print(f"  PDF Path: {book['pdf_path']}")
            print(f"  Page Count: {book['page_count']}")
            print(f"  Published: {book['published']}")
            print()
        
        # book_pages count
        cursor.execute("SELECT COUNT(*) as cnt FROM book_pages")
        book_pages_count = cursor.fetchone()['cnt']
        results['book_pages_count'] = book_pages_count
        print(f"book_pages = {book_pages_count}")
        
        # chapters count
        cursor.execute("SELECT COUNT(*) as cnt FROM chapters")
        chapters_count = cursor.fetchone()['cnt']
        results['chapters_count'] = chapters_count
        print(f"chapters = {chapters_count}")
        
        # Page range verification
        if books:
            book_id = books[0]['id']
            cursor.execute("SELECT MIN(page_number) as min_p, MAX(page_number) as max_p FROM book_pages WHERE book_id = %s", (book_id,))
            page_range = cursor.fetchone()
            results['min_page'] = page_range['min_p']
            results['max_page'] = page_range['max_p']
            print(f"\nRango de páginas: {page_range['min_p']} a {page_range['max_p']}")
            
            # Verify no duplicates
            cursor.execute("""
                SELECT page_number, COUNT(*) as cnt 
                FROM book_pages 
                WHERE book_id = %s 
                GROUP BY page_number 
                HAVING COUNT(*) > 1
            """, (book_id,))
            duplicates = cursor.fetchall()
            results['has_duplicates'] = len(duplicates) > 0
            print(f"Páginas duplicadas: {'SÍ' if duplicates else 'NO'}")
            
            # Verify no pages outside range
            cursor.execute("""
                SELECT COUNT(*) as cnt 
                FROM book_pages 
                WHERE book_id = %s AND (page_number < 1 OR page_number > %s)
            """, (book_id, books[0]['page_count']))
            out_of_range = cursor.fetchone()['cnt']
            results['out_of_range'] = out_of_range
            print(f"Páginas fuera de rango: {out_of_range}")
            
            # Verify page_count matches
            results['page_count_matches'] = books[0]['page_count'] == book_pages_count
            print(f"page_count coincide con book_pages: {'SÍ' if results['page_count_matches'] else 'NO'}")
        
        # ═══════════════════════════════════════════════════════════════════
        # VERIFICACIÓN 2 — CONTENIDO
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("VERIFICACIÓN 2 — CONTENIDO")
        print("=" * 70)
        
        if books:
            cursor.execute("SELECT page_number, content FROM book_pages WHERE book_id = %s ORDER BY page_number", (book_id,))
            pages = cursor.fetchall()
            
            # Content analysis
            unique_contents = set()
            placeholder_count = 0
            pathological_count = 0
            min_len = float('inf')
            max_len = 0
            total_len = 0
            
            for page in pages:
                content = page['content']
                unique_contents.add(content)
                
                if content.strip() == "Contenido de texto no disponible.":
                    placeholder_count += 1
                
                if len(content) < 10:
                    pathological_count += 1
                
                min_len = min(min_len, len(content))
                max_len = max(max_len, len(content))
                total_len += len(content)
            
            avg_len = total_len / len(pages) if pages else 0
            
            results['unique_contents'] = len(unique_contents)
            results['all_same'] = len(unique_contents) == 1
            results['placeholder_count'] = placeholder_count
            results['pathological_count'] = pathological_count
            results['min_content_len'] = min_len
            results['max_content_len'] = max_len
            results['avg_content_len'] = avg_len
            
            print(f"Páginas con contenido: {len(pages)}")
            print(f"Contenidos únicos: {len(unique_contents)}")
            print(f"Todas las páginas son iguales: {'SÍ' if results['all_same'] else 'NO'}")
            print(f"Placeholder detectado: {placeholder_count}")
            print(f"Contenido patológico (<10 chars): {pathological_count}")
            print(f"Longitud mínima: {min_len}")
            print(f"Longitud máxima: {max_len}")
            print(f"Longitud promedio: {avg_len:.2f}")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR en database verification: {e}")
        import traceback
        traceback.print_exc()
        results['db_error'] = str(e)
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 3 — PDF EN PERSISTENT DISK
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 3 — PDF EN PERSISTENT DISK")
    print("=" * 70)
    
    if books and books[0]['pdf_path']:
        pdf_path = books[0]['pdf_path']
        results['pdf_path'] = pdf_path
        
        # Check if file exists
        if os.path.exists(pdf_path):
            results['pdf_exists'] = True
            print(f"PDF existe: SÍ")
            
            # Check if inside STORAGE_BOOKS
            abs_pdf = os.path.abspath(pdf_path)
            abs_storage = os.path.abspath(STORAGE_BOOKS)
            results['in_storage'] = abs_pdf.startswith(abs_storage)
            print(f"Dentro de STORAGE_BOOKS: {'SÍ' if results['in_storage'] else 'NO'}")
            
            # File size
            file_size = os.path.getsize(pdf_path)
            results['pdf_size'] = file_size
            print(f"Tamaño: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Magic bytes
            with open(pdf_path, 'rb') as f:
                magic = f.read(5)
            results['magic_bytes'] = magic
            print(f"Magic bytes: {magic}")
            
            # Page count from PDF
            pdf_pages = get_pdf_page_count(pdf_path)
            results['pdf_page_count'] = pdf_pages
            print(f"Páginas del PDF: {pdf_pages}")
            
            # SHA-256
            sha256 = calculate_sha256(pdf_path)
            results['sha256'] = sha256
            print(f"SHA-256: {sha256}")
            print(f"SHA-256 esperado: {EXPECTED_SHA256}")
            results['sha256_match'] = sha256 == EXPECTED_SHA256
            print(f"SHA-256 coincide: {'SÍ' if results['sha256_match'] else 'NO'}")
        else:
            results['pdf_exists'] = False
            print(f"PDF existe: NO")
            print(f"Ruta buscada: {pdf_path}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 4 — ARCHIVOS HISTÓRICOS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 4 — ARCHIVOS HISTÓRICOS")
    print("=" * 70)
    
    historical_exists = []
    for filename in HISTORICAL_FILES:
        filepath = os.path.join(STORAGE_BOOKS, filename)
        exists = os.path.exists(filepath)
        historical_exists.append(exists)
        print(f"  {filename}: {'EXISTS' if exists else 'MISSING'}")
    
    results['historical_files_intact'] = all(historical_exists)
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 5 — API (solo verificable en local)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 5 — API")
    print("=" * 70)
    
    try:
        import requests
        API_BASE = "http://localhost:8000"
        
        # List books
        resp = requests.get(f"{API_BASE}/api/books", timeout=5)
        results['api_list_status'] = resp.status_code
        print(f"GET /api/books: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            books_api = data if isinstance(data, list) else data.get('books', data.get('items', []))
            results['api_books_count'] = len(books_api) if isinstance(books_api, list) else 0
            print(f"  Libros en API: {results['api_books_count']}")
            
            if isinstance(books_api, list) and len(books_api) > 0:
                # Find the pilot book
                pilot = None
                for b in books_api:
                    title = b.get('title', '')
                    if 'rayuela' in title.lower():
                        pilot = b
                        break
                
                if pilot:
                    book_id_api = pilot.get('id')
                    results['api_pilot_id'] = book_id_api
                    print(f"  Libro piloto encontrado: ID={book_id_api}, título='{pilot.get('title')}'")
                    
                    # Detail
                    resp_detail = requests.get(f"{API_BASE}/api/books/{book_id_api}", timeout=5)
                    results['api_detail_status'] = resp_detail.status_code
                    print(f"  GET /api/books/{book_id_api}: {resp_detail.status_code}")
                    
                    # Download
                    resp_download = requests.get(f"{API_BASE}/api/books/{book_id_api}/download", timeout=5)
                    results['api_download_status'] = resp_download.status_code
                    print(f"  GET /api/books/{book_id_api}/download: {resp_download.status_code}")
                else:
                    results['api_pilot_id'] = None
                    print(f"  Libro piloto NO encontrado en listado")
            else:
                print(f"  No se pudo procesar la respuesta de la API")
        else:
            print(f"  Error al consultar API: {resp.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("  API no está corriendo localmente (ConnectionError)")
        results['api_list_status'] = 'NOT_RUNNING'
        results['api_detail_status'] = 'NOT_RUNNING'
        results['api_download_status'] = 'NOT_RUNNING'
    except Exception as e:
        print(f"  Error al consultar API: {e}")
        results['api_error'] = str(e)
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 7 — DATOS NO RELACIONADOS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("VERIFICACIÓN 7 — DATOS NO RELACIONADOS")
    print("=" * 70)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Users
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        users_count = cursor.fetchone()['cnt']
        results['users_count'] = users_count
        print(f"  users: {users_count}")
        
        # rayos_transactions
        cursor.execute("SELECT COUNT(*) as cnt FROM rayos_transactions")
        rayos_count = cursor.fetchone()['cnt']
        results['rayos_count'] = rayos_count
        print(f"  rayos_transactions: {rayos_count}")
        
        # forum_posts
        cursor.execute("SELECT COUNT(*) as cnt FROM forum_posts")
        forum_count = cursor.fetchone()['cnt']
        results['forum_posts_count'] = forum_count
        print(f"  forum_posts: {forum_count}")
        
        # reviews
        cursor.execute("SELECT COUNT(*) as cnt FROM reviews")
        reviews_count = cursor.fetchone()['cnt']
        results['reviews_count'] = reviews_count
        print(f"  reviews: {reviews_count}")
        
        # competitions (if table exists)
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM competitions")
            competitions_count = cursor.fetchone()['cnt']
            results['competitions_count'] = competitions_count
            print(f"  competitions: {competitions_count}")
        except:
            results['competitions_count'] = 'TABLE_NOT_FOUND'
            print(f"  competitions: TABLE NOT FOUND")
        
        conn.close()
        
    except Exception as e:
        print(f"  Error al verificar datos no relacionados: {e}")
        results['unrelated_error'] = str(e)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("RESUMEN DE VERIFICACIONES")
    print("=" * 70)
    
    # Determine pass/fail for each check
    checks = []
    
    # V1: Database
    v1_pass = (results.get('books_count', 0) == 1 and
               results.get('book_pages_count', 0) == 77 and
               results.get('chapters_count', 0) == 0 and
               not results.get('has_duplicates', True) and
               results.get('out_of_range', -1) == 0 and
               results.get('page_count_matches', False))
    checks.append(("V1-Database", v1_pass))
    
    # V2: Content
    v2_pass = (results.get('placeholder_count', -1) == 0 and
               results.get('pathological_count', -1) == 0)
    checks.append(("V2-Content", v2_pass))
    
    # V3: PDF
    v3_pass = (results.get('pdf_exists', False) and
               results.get('in_storage', False) and
               results.get('sha256_match', False))
    checks.append(("V3-PDF", v3_pass))
    
    # V4: Historical
    v4_pass = results.get('historical_files_intact', False)
    checks.append(("V4-Historical", v4_pass))
    
    # V5: API
    v5_pass = (results.get('api_list_status') == 200 and
               results.get('api_detail_status') == 200)
    checks.append(("V5-API", v5_pass))
    
    # Print checks
    for name, passed in checks:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    
    # Overall
    overall = all(p for _, p in checks)
    print(f"\nRESULTADO GENERAL: {'PASS' if overall else 'FAIL'}")
    
    # Save results to JSON
    output_path = os.path.join(os.path.dirname(__file__), 'audit_fase5_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResultados guardados en: {output_path}")
    
    return results

if __name__ == "__main__":
    run_audit()