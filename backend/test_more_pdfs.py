# -*- coding: utf-8 -*-
"""
FASE 5 — TEST ADDITIONAL PDFs
"""
import os
import sys
import hashlib
import urllib.request
import json

sys.path.insert(0, os.path.dirname(__file__))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_more_pdfs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

CANDIDATES = [
    {
        "title": "Episodios nacionales (Tomo V)",
        "author": "Benito Pérez Galdós",
        "year": 1905,
        "identifier": "episodiosnacion05galdgoog",
        "pdf_filename": "episodiosnacion05galdgoog_text.pdf",
        "source_url": "https://archive.org/download/episodiosnacion05galdgoog/episodiosnacion05galdgoog_text.pdf",
    },
    {
        "title": "Folk-lore español (Biblioteca de las tradiciones populares)",
        "author": "Emilia Pardo Bazán et al.",
        "year": 1884,
        "identifier": "folkloreespaolb14bazgoog",
        "pdf_filename": "folkloreespaolb14bazgoog.pdf",
        "source_url": "https://archive.org/download/folkloreespaolb14bazgoog/folkloreespaolb14bazgoog.pdf",
    },
    {
        "title": "Sentencias de Don Quijote y Agudezas de Sancho",
        "author": "Miguel de Cervantes",
        "year": 1863,
        "identifier": "sentenciasdedon00saavgoog",
        "pdf_filename": "sentenciasdedon00saavgoog.pdf",
        "source_url": "https://archive.org/download/sentenciasdedon00saavgoog/sentenciasdedon00saavgoog.pdf",
    },
    {
        "title": "Poemas rústicos",
        "author": "Manuel José Othón",
        "year": 1902,
        "identifier": "poemasrsticos00othgoog",
        "pdf_filename": "poemasrsticos00othgoog.pdf",
        "source_url": "https://archive.org/download/poemasrsticos00othgoog/poemasrsticos00othgoog.pdf",
    },
    {
        "title": "Morriña: Historia amorosa",
        "author": "Emilia Pardo Bazán",
        "year": 1889,
        "identifier": "morriahistoriaa00bazgoog",
        "pdf_filename": "morriahistoriaa00bazgoog.pdf",
        "source_url": "https://archive.org/download/morriahistoriaa00bazgoog/morriahistoriaa00bazgoog.pdf",
    },
    {
        "title": "El pasado",
        "author": "Pío Baroja",
        "year": 1906,
        "identifier": "elpasado00barogoog",
        "pdf_filename": "elpasado00barogoog.pdf",
        "source_url": "https://archive.org/download/elpasado00barogoog/elpasado00barogoog.pdf",
    },
    {
        "title": "Fisiología de la risa",
        "author": "Juan Montalvo",
        "year": 2012,
        "identifier": "montalvojufisiologiadelar00",
        "pdf_filename": "montalvojufisiologiadelar00.pdf",
        "source_url": "https://archive.org/download/montalvojufisiologiadelar00/montalvojufisiologiadelar00.pdf",
    },
    {
        "title": "Topacios (Cuentos y Fantasías)",
        "author": "Rafael Ángel Troyo",
        "year": 1920,
        "identifier": "topacios-cuentos-y-fantasias-por-rafael-angel-troyo",
        "pdf_filename": "Topacios ( Cuentos Y Fantasías) Por Rafael Angel Troyo.pdf",
        "source_url": "https://archive.org/download/topacios-cuentos-y-fantasias-por-rafael-angel-troyo/Topacios%20%28%20Cuentos%20Y%20Fantas%C3%ADas%29%20Por%20Rafael%20Angel%20Troyo.pdf",
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
        page_lengths = []
        empty_pages = 0
        for i in range(total_pages):
            text = reader.pages[i].extract_text() or ""
            page_lengths.append(len(text.strip()))
            if not text.strip():
                empty_pages += 1
            total_text += text
        
        sample = ""
        for i in range(min(5, total_pages)):
            text = reader.pages[i].extract_text() or ""
            if len(text.strip()) > 100:
                sample = text[:500]
                break
        
        is_boilerplate = "digital copy of a book" in total_text[:2000].lower() and len(total_text) < 15000
        
        return {
            "success": True,
            "total_pages": total_pages,
            "total_text_length": len(total_text),
            "empty_pages": empty_pages,
            "sample": sample,
            "has_text": len(total_text.strip()) > 500 and not is_boilerplate,
            "is_boilerplate": is_boilerplate,
            "avg_page_length": len(total_text) / total_pages if total_pages else 0
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def download_and_test(candidate):
    print(f"\n{'='*60}")
    print(f"Title: {candidate['title']}")
    print(f"Author: {candidate['author']}")
    
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
            print(f"Empty pages: {result['empty_pages']}")
            print(f"Has real text: {result['has_text']}")
            print(f"Is boilerplate: {result['is_boilerplate']}")
            
            if result['sample']:
                print(f"\nSample (first 400 chars):")
                print(f"  {result['sample'][:400]}")
            
            return {
                "success": True,
                "file_size": file_size,
                "sha256": sha256,
                "pages": result['total_pages'],
                "text_length": result['total_text_length'],
                "has_text": result['has_text'],
                "is_boilerplate": result['is_boilerplate'],
                "empty_pages": result['empty_pages']
            }
        else:
            print(f"Extraction failed: {result['error']}")
            return {"success": False, "error": result['error']}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("=" * 60)
    print("FASE 5 - TEST MORE PDFs")
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
        boilerplate = r['result'].get('is_boilerplate', False)
        print(f"#{i}: {r['candidate']['title']} - {status} ({pages} pages, {text_len} chars, boilerplate={boilerplate})")
    
    output_file = os.path.join(OUTPUT_DIR, 'test_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()