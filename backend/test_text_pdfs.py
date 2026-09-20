# -*- coding: utf-8 -*-
"""
FASE 5 — VERIFICACIÓN DE PDFs DE TEXTO EN ESPAÑOL
"""
import os
import sys
import hashlib
import urllib.request
import json

sys.path.insert(0, os.path.dirname(__file__))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_text_pdfs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

CANDIDATES = [
    {
        "title": "El Hijo",
        "author": "Horacio Quiroga",
        "year": 1921,
        "identifier": "ElHijoHoracioQuiroga",
        "pdf_filename": "El Hijo - Horacio Quiroga.pdf",
        "source_url": "https://archive.org/download/ElHijoHoracioQuiroga/El%20Hijo%20-%20Horacio%20Quiroga.pdf",
    },
    {
        "title": "Los Mensu",
        "author": "Horacio Quiroga",
        "year": 1921,
        "identifier": "LosMensuHoracioQuiroga",
        "pdf_filename": "Los Mensu Horacio Quiroga.pdf",
        "source_url": "https://archive.org/download/LosMensuHoracioQuiroga/Los%20Mensu%20Horacio%20Quiroga.pdf",
    },
    {
        "title": "Anaconda y otros cuentos",
        "author": "Horacio Quiroga",
        "year": 1918,
        "identifier": "anaconda-y-otros-cuentos-horacio-quiroga",
        "pdf_filename": "Anaconda y otros cuentos - Horacio Quiroga.pdf",
        "source_url": "https://archive.org/download/anaconda-y-otros-cuentos-horacio-quiroga/Anaconda%20y%20otros%20cuentos%20-%20Horacio%20Quiroga.pdf",
    },
    {
        "title": "César o nada",
        "author": "Pío Baroja",
        "year": 1910,
        "identifier": "cesaronadanovela00baro",
        "pdf_filename": "cesaronadanovela00baro.pdf",
        "source_url": "https://archive.org/download/cesaronadanovela00baro/cesaronadanovela00baro.pdf",
    },
    {
        "title": "El Mayorazgo de Labraz",
        "author": "Pío Baroja",
        "year": 1903,
        "identifier": "elmayorazgodela00barogoog",
        "pdf_filename": "elmayorazgodela00barogoog.pdf",
        "source_url": "https://archive.org/download/elmayorazgodela00barogoog/elmayorazgodela00barogoog.pdf",
    },
]

def calculate_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def test_pdf_extraction(pdf_path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        total_text = ""
        for i in range(total_pages):
            text = reader.pages[i].extract_text() or ""
            total_text += text
        
        sample = total_text[:500] if total_text else ""
        
        return {
            "success": True,
            "total_pages": total_pages,
            "total_text_length": len(total_text),
            "sample": sample,
            "has_text": len(total_text.strip()) > 500
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def download_and_test(candidate):
    print(f"\n{'='*60}")
    print(f"Title: {candidate['title']}")
    print(f"Author: {candidate['author']}")
    print(f"Year: {candidate['year']}")
    
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
        
        print(f"Testing PDF extraction...")
        result = test_pdf_extraction(filepath)
        
        if result['success']:
            print(f"Total pages: {result['total_pages']}")
            print(f"Total text length: {result['total_text_length']} chars")
            print(f"Has extractable text: {result['has_text']}")
            
            if result['sample']:
                print(f"\nSample (first 400 chars):")
                print(f"  {result['sample'][:400]}")
            
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
    print("FASE 5 - TEST TEXT PDFs")
    print("=" * 60)
    
    results = []
    for candidate in CANDIDATES:
        result = download_and_test(candidate)
        results.append({
            "candidate": candidate,
            "result": result
        })
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for i, r in enumerate(results, 1):
        status = "APT" if r['result'].get('has_text') else "REVISAR"
        pages = r['result'].get('pages', 'N/A')
        text_len = r['result'].get('text_length', 'N/A')
        print(f"#{i}: {r['candidate']['title']} - {status} ({pages} pages, {text_len} chars)")
    
    output_file = os.path.join(OUTPUT_DIR, 'test_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()