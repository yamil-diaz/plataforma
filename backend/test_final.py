# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'backend')
import lectura

candidates = [
    ('Los ayacuchos', 'https://archive.org/download/losayacuchos02galdgoog/losayacuchos02galdgoog_text.pdf'),
    ('César o nada', None),  # already tested
]

import urllib.request
import os
import hashlib

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_final_pdfs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test Los ayacuchos
name = 'Los ayacuchos'
url = 'https://archive.org/download/losayacuchos02galdgoog/losayacuchos02galdgoog_text.pdf'
filepath = os.path.join(OUTPUT_DIR, 'losayacuchos02galdgoog_text.pdf')

print(f'Downloading {name}...')
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=60) as resp:
    with open(filepath, 'wb') as f:
        while True:
            chunk = resp.read(8192)
            if not chunk:
                break
            f.write(chunk)

file_size = os.path.getsize(filepath)
h = hashlib.sha256()
with open(filepath, 'rb') as f:
    for chunk in iter(lambda: f.read(8192), b''):
        h.update(chunk)
sha256 = h.hexdigest()

print(f'Downloaded: {file_size} bytes ({file_size/1024/1024:.2f} MB)')
print(f'SHA-256: {sha256}')

print(f'\nRunning lectura pipeline...')
result = lectura.procesar_contenido_para_publicacion(pdf_path=filepath, fuente='pdf')
v = result['validacion']
print(f'Valid: {v["valid"]}')
print(f'Errors: {v["errors"]}')
print(f'Pages: {len(result["paginas"])}')
print(f'Chapters: {len(result["capitulos"])}')
print(f'Content length: {len(result["content"])}')

# Check pages for real content
for i in [5, 10, 20, 50]:
    if i < len(result['paginas']):
        p = result['paginas'][i]
        print(f'Page {i+1} ({len(p)} chars): {p[:200]}')
        print()
