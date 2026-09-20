# -*- coding: utf-8 -*-
"""
FASE 5 — DESCARGA DE LIBROS DE DOMINIO PÚBLICO
Script para descargar PDFs de fuentes legítimas.
"""
import os
import sys
import hashlib
import urllib.request
import urllib.error
import json

# Directorio de salida
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'public_domain_books')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Libros candidatos de dominio público
# Fuente: Project Gutenberg y Internet Archive
CANDIDATES = [
    {
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "year": 1865,
        "gutenberg_id": 11,
        "url": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
        "format": "txt",
        "description": "Obra clásica de literatura infantil, dominio público desde 1941."
    },
    {
        "title": "Frankenstein; or, the modern prometheus",
        "author": "Mary Wollstonecraft Shelley",
        "year": 1818,
        "gutenberg_id": 84,
        "url": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
        "format": "txt",
        "description": "Novela gótica, dominio público desde 1919."
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "gutenberg_id": 1342,
        "url": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
        "format": "txt",
        "description": "Novela de romance, dominio público desde 1919."
    },
    {
        "title": "The Adventures of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "year": 1892,
        "gutenberg_id": 1661,
        "url": "https://www.gutenberg.org/cache/epub/1661/pg1661.txt",
        "format": "txt",
        "description": "Colección de relatos, dominio público desde 1968."
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "gutenberg_id": 64317,
        "url": "https://www.gutenberg.org/cache/epub/64317/pg64317.txt",
        "format": "txt",
        "description": "Novela estadounidense, dominio público desde 2021."
    }
]

def calculate_sha256(file_path):
    """Calcula SHA-256 de un archivo."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def download_book(book_info):
    """Descarga un libro desde Project Gutenberg."""
    print(f"\nDescargando: {book_info['title']}")
    print(f"Autor: {book_info['author']}")
    print(f"Año: {book_info['year']}")
    print(f"URL: {book_info['url']}")
    
    try:
        req = urllib.request.Request(book_info['url'])
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            
            # Guardar como archivo de texto
            filename = f"{book_info['gutenberg_id']}_{book_info['title'].replace(' ', '_')}.txt"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Calcular SHA-256
            sha256 = calculate_sha256(filepath)
            file_size = os.path.getsize(filepath)
            
            print(f"Guardado: {filepath}")
            print(f"Tamaño: {file_size} bytes")
            print(f"SHA-256: {sha256}")
            
            return {
                "success": True,
                "filepath": filepath,
                "sha256": sha256,
                "size": file_size,
                "content_length": len(content)
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("=" * 70)
    print("FASE 5 — DESCARGA DE LIBROS DE DOMINIO PÚBLICO")
    print("=" * 70)
    
    results = []
    
    for i, book in enumerate(CANDIDATES[:5], 1):
        print(f"\n{'='*70}")
        print(f"LIBRO #{i}")
        print(f"{'='*70}")
        
        result = download_book(book)
        results.append({
            "book": book,
            "result": result
        })
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    successful = sum(1 for r in results if r['result']['success'])
    print(f"Descargas exitosas: {successful}/{len(results)}")
    
    for i, r in enumerate(results, 1):
        status = "OK" if r['result']['success'] else "FAIL"
        print(f"  #{i}: {r['book']['title']} - {status}")
    
    # Guardar resultados
    output_file = os.path.join(OUTPUT_DIR, 'download_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResultados guardados en: {output_file}")
    return results

if __name__ == "__main__":
    main()