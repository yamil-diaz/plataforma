#!/usr/bin/env python3
import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))
from pypdf import PdfReader
from collections import Counter
import lectura

fname = 'dracula.pdf'
base = os.path.dirname(os.path.abspath(__file__))
fpath = os.path.join(base, fname)
reader = PdfReader(fpath)

paginas = [p.extract_text() or '' for p in reader.pages]
content = '\n'.join(paginas)

print(f'Content: {len(content)} chars')

# Rule 1: racha larga de caracteres identicos
MAX_RACHA = 200
match = re.search(r'(.)\1{%d}' % (MAX_RACHA - 1), content)
if match:
    start = max(0, match.start() - 20)
    end = min(len(content), match.end() + 20)
    print(f'RACHA LARGA detectada: char="{match.group(1)}" repitiendose {len(match.group())} veces')
    print(f'  Contexto: ...{repr(content[start:end])}...')
else:
    print('Rule 1 (racha larga): OK')

# Rule 2: linea repetida
LINEA_REPETIDA_MAX = 50
conteo_lineas = Counter(linea.strip() for linea in content.splitlines() if linea.strip())
top_line = conteo_lineas.most_common(1)[0] if conteo_lineas else ('', 0)
print(f'Rule 2 (linea repetida): top linea se repite {top_line[1]} veces (max {LINEA_REPETIDA_MAX})')
if top_line[1] > LINEA_REPETIDA_MAX:
    print(f'  Linea: {repr(top_line[0][:100])}')

# Rule 3: un caracter concentra >35%
letras = [c for c in content if not c.isspace()]
mas_frecuente = Counter(letras).most_common(1)[0]
ratio = mas_frecuente[1] / len(letras) if letras else 0
print(f'Rule 3 (char >35%): "{mas_frecuente[0]}" = {ratio*100:.1f}%')

# Rule 4: control/substitution >10%
sospechosos = sum(1 for c in letras if ord(c) < 32 or c == '\ufffd')
ratio_susp = sospechosos / len(letras) if letras else 0
print(f'Rule 4 (control >10%): {sospechosos}/{len(letras)} = {ratio_susp*100:.1f}%')

# Rule 5: U+FFFD > 5
count_fffd = content.count('\ufffd')
print(f'Rule 5 (U+FFFD > 5): {count_fffd}')

# Show if any line is repeated many times
print(f'\nTop 10 lineas mas repetidas:')
for line, count in conteo_lineas.most_common(10):
    print(f'  {count:3d}x: {repr(line[:80])}')
