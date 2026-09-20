#!/usr/bin/env python3
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))
from pypdf import PdfReader
import lectura

for fname in ['dracula.pdf', 'pride_and_prejudice.pdf']:
    base = os.path.dirname(os.path.abspath(__file__))
    fpath = os.path.join(base, fname)
    reader = PdfReader(fpath)
    print(f'=== {fname} ({len(reader.pages)} paginas) ===')
    
    paginas = []
    for page in reader.pages:
        t = page.extract_text() or ''
        paginas.append(t)
    
    content = '\n'.join(paginas)
    print(f'  Content length: {len(content)} chars')
    print(f'  Pages count: {len(paginas)}')
    
    # Run the full pipeline
    resultado = lectura.procesar_contenido_para_publicacion(pdf_path=fpath, fuente='pdf')
    validacion = resultado['validacion']
    print(f'  Pipeline valid: {validacion["valid"]}')
    print(f'  Pipeline errors: {validacion["errors"]}')
    detalle = validacion.get('detalle', {})
    print(f'  Pathological: {detalle.get("pathological")}')
    print(f'  es_basura: {detalle.get("es_basura")}')
    print(f'  es_placeholder: {detalle.get("es_placeholder")}')
    print(f'  content_length: {detalle.get("content_length")}')
    print(f'  short_content: {detalle.get("short_content")}')
    
    # Check basura on extracted content
    extracted_content = resultado['content']
    print(f'  Extracted content length: {len(extracted_content)}')
    basura = lectura._detectar_basura(extracted_content)
    print(f'  _detectar_basura(extracted): {basura}')
    
    # Check characters
    chars = [c for c in extracted_content if not c.isspace()]
    if chars:
        from collections import Counter
        top = Counter(chars).most_common(5)
        total = len(chars)
        suspicious = sum(1 for c in chars if ord(c) < 32 or c == '\ufffd')
        print(f'  Suspicious chars: {suspicious}/{total} ({suspicious/total*100:.1f}%)')
        print(f'  Top 5: {[(c, n, f"{n/total*100:.1f}%") for c, n in top]}')
    print()
