#!/usr/bin/env python3
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))
from pypdf import PdfReader
from collections import Counter

for fname in ['pride_and_prejudice.pdf', 'a_christmas_carol.pdf', 'moby_dick.pdf']:
    base = os.path.dirname(os.path.abspath(__file__))
    fpath = os.path.join(base, fname)
    reader = PdfReader(fpath)
    paginas = [p.extract_text() or '' for p in reader.pages]
    content = '\n'.join(paginas)
    conteo = Counter(linea.strip() for linea in content.splitlines() if linea.strip())
    top = conteo.most_common(3)
    print(f'{fname}: top lineas:')
    for line, count in top:
        print(f'  {count:3d}x: {repr(line[:80])}')
    print()
