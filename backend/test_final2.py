# -*- coding: utf-8 -*-
import sys, os, hashlib, urllib.request
sys.path.insert(0, 'backend')
import lectura

OUTPUT_DIR = 'backend/test_final2'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_book(name, url, filename):
    fp = os.path.join(OUTPUT_DIR, filename)
    print(f'\n===== {name} =====')
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(fp, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        sz = os.path.getsize(fp)
        h = hashlib.sha256()
        with open(fp, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        sha = h.hexdigest()
        print(f'Size: {sz} bytes ({sz/1024/1024:.2f} MB), SHA: {sha}')
        r = lectura.procesar_contenido_para_publicacion(pdf_path=fp, fuente='pdf')
        v = r['validacion']
        print(f'Valid: {v["valid"]}, Errors: {v["errors"]}')
        print(f'Pages: {len(r["paginas"])}, Chapters: {len(r["capitulos"])}, Content: {len(r["content"])} chars')
        if r['paginas']:
            for i in [4, 9, 19, 49]:
                if i < len(r['paginas']):
                    p = r['paginas'][i]
                    print(f'  Page {i+1} ({len(p)} chars): {p[:200]}')
        return {'valid': v['valid'], 'pages': len(r['paginas']), 'content': len(r['content']), 'sha': sha, 'size': sz}
    except Exception as e:
        print(f'Error: {e}')
        return None

# Test Calderon Entremeses
r1 = test_book(
    'Calderon Entremeses',
    'https://archive.org/download/pedrocalderondelabarcaentremeses/Pedro%20Calder%C3%B3n%20de%20la%20Barca%20-%20Entremeses.pdf',
    'calderon_entremeses.pdf'
)

# Test Galdos Episodios Nacionales V (text PDF)
r2 = test_book(
    'Galdos Episodios Nacionales V',
    'https://archive.org/download/episodiosnacion05galdgoog/episodiosnacion05galdgoog_text.pdf',
    'episodios_nacionales_v.pdf'
)

# Test unfacciosos text PDF
r3 = test_book(
    'Episodios Un faccioso',
    'https://archive.org/download/episodiosnacionalesunfacciosomsyalgunosfrailesmenosremoved/episodiosnacionalesunfacciosomsyalgunosfrailesmenosremoved_text.pdf',
    'episodios_faccioso.pdf'
)

# Test vuelta al mundo text PDF
r4 = test_book(
    'Episodios Vuelta al Mundo',
    'https://archive.org/download/episodiosnacionaleslavueltaalmundoenlanumanciaremoved/episodiosnacionaleslavueltaalmundoenlanumanciaremoved_text.pdf',
    'episodios_vuelta.pdf'
)

# Summary
print('\n\n===== SUMMARY =====')
for name, r in [('Calderon Entremeses', r1), ('Galdos Ep. V', r2), ('Galdos Un faccioso', r3), ('Galdos Vuelta', r4)]:
    if r:
        print(f'{name}: Valid={r["valid"]}, Pages={r["pages"]}, Content={r["content"]}, Size={r["size"]/1024/1024:.2f}MB')
    else:
        print(f'{name}: FAILED')
