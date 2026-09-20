# -*- coding: utf-8 -*-
"""
FASE 5 — VERIFICACIÓN DE PDFs EN ESPAÑOL
Script para descargar y verificar PDFs de Internet Archive.
"""
import os
import sys
import hashlib
import urllib.request
import json

sys.path.insert(0, os.path.dirname(__file__))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_spanish_pdfs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Candidates from Internet Archive
CANDIDATES = [
    {
        "title": "La vida de Lazarillo de Tormes",
        "author": "Anónimo",
        "year": 1554,
        "identifier": "lavidadelazaril00delgoog",
        "pdf_filename": "lavidadelazaril00delgoog.pdf",
        "source_url": "https://archive.org/download/lavidadelazaril00delgoog/lavidadelazaril00delgoog.pdf",
        "description": "Novela picaresca española, anónima, siglo XVI."
    },
    {
        "title": "Marianela",
        "author": "Benito Pérez Galdós",
        "year": 1878,
        "identifier": "marianela03galdgoog",
        "pdf_filename": "marianela03galdgoog.pdf",
        "source_url": "https://archive.org/download/marianela03galdgoog/marianela03galdgoog.pdf",
        "description": "Novela de Benito Pérez Galdós."
    },
    {
        "title": "Doña Perfecta",
        "author": "Benito Pérez Galdós",
        "year": 1876,
        "identifier": "doaperfectanove01galdgoog",
        "pdf_filename": "doaperfectanove01galdgoog.pdf",
        "source_url": "https://archive.org/download/doaperfectanove01galdgoog/doaperfectanove01galdgoog.pdf",
        "description": "Novela de Benito Pérez Galdós."
    },
    {
        "title": "La vida es sueño",
        "author": "Pedro Calderón de la Barca",
        "year": 1635,
        "identifier": "lavidaessueo01goog",
        "pdf_filename": "lavidaessueo01goog.pdf",
        "source_url": "https://archive.org/download/lavidaessueo01goog/lavidaessueo01goog.pdf",
        "description": "Drama filosófico de Calderón de la Barca."
    },
    {
        "title": "Cuentos de amor, locura y muerte",
        "author": "Horacio Quiroga",
        "year": 1917,
        "identifier": "cuentos-de-amor-locura-y-muerte-horacio-quiroga",
        "pdf_filename": "cuentos-de-amor-locura-y-muerte-horacio-quiroga.pdf",
        "source_url": "https://archive.org/download/cuentos-de-amor-locura-y-muerte-horacio-quiroga/cuentos-de-amor-locura-y-muerte-horacio-quiroga.pdf",
        "description": "Colección de cuentos de Horacio Quiroga."
    },
]

def calculate_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def test_pdf_extraction(pdf_path):
    """Test if PDF has extractable text using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # Extract text from first 3 pages
        sample_texts = []
        for i in range(min(3, total_pages)):
            text = reader.pages[i].extract_text() or ""
            sample_texts.append(text[:500])
        
        total_text = "\n".join(reader.pages[i].extract_text() or "" for i in range(total_pages))
        
        return {
            "success": True,
            "total_pages": total_pages,
            "total_text_length": len(total_text),
            "sample_texts": sample_texts,
            "has_text": len(total_text.strip()) > 100
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def download_and_test(candidate):
    print(f"\n{'='*60}")
    print(f"Title: {candidate['title']}")
    print(f"Author: {candidate['author']}")
    print(f"Year: {candidate['year']}")
    print(f"URL: {candidate['source_url']}")
    
    filename = candidate['pdf_filename']
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    try:
        print(f"Downloading...")
        req = urllib.request.Request(candidate['source_url'])
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(filepath, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        sha256 = calculate_sha256(filepath)
        
        print(f"Downloaded: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"SHA-256: {sha256}")
        
        # Test PDF extraction
        print(f"Testing PDF extraction...")
        result = test_pdf_extraction(filepath)
        
        if result['success']:
            print(f"Total pages: {result['total_pages']}")
            print(f"Total text length: {result['total_text_length']} chars")
            print(f"Has extractable text: {result['has_text']}")
            
            if result['sample_texts']:
                print(f"\nSample from page 1 (first 300 chars):")
                print(f"  {result['sample_texts'][0][:300]}...")
            
            return {
                "success": True,
                "file_size": file_size,
                "sha256": sha256,
                "pages": result['total_pages'],
                "text_length": result['total_text_length'],
                "has_text": result['has_text']
            }
        else:
            print(f"Extraction failed: {result['error']}")
            return {"success": False, "error": result['error']}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("=" * 60)
    print("FASE 5 — VERIFICACION DE PDFs EN ESPANOL")
    print("=" * 60)
    
    results = []
    for candidate in CANDIDATES:
        result = download_and_test(candidate)
        results.append({
            "candidate": candidate,
            "result": result
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for i, r in enumerate(results, 1):
        status = "APT" if r['result'].get('success') and r['result'].get('has_text') else "REVISAR"
        pages = r['result'].get('pages', 'N/A')
        text_len = r['result'].get('text_length', 'N/A')
        print(f"#{i}: {r['candidate']['title']} - {status} ({pages} pages, {text_len} chars)")
    
    # Save results
    output_file = os.path.join(OUTPUT_DIR, 'test_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()