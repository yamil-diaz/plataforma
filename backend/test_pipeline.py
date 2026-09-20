# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'backend')
import lectura

candidates = [
    ('Anaconda y otros cuentos', 'backend/test_text_pdfs/Anaconda y otros cuentos - Horacio Quiroga.pdf'),
    ('César o nada', 'backend/test_text_pdfs/Cesaronadanovela00baro.pdf'),
    ('Episodios nacionales V', 'backend/test_more_pdfs/episodiosnacion05galdgoog_text.pdf'),
    ('El Hijo', 'backend/test_text_pdfs/El Hijo - Horacio Quiroga.pdf'),
    ('Fisiología de la risa', 'backend/test_more_pdfs/montalvojufisiologiadelar00.pdf'),
]

for name, path in candidates:
    print(f'\n===== {name} =====')
    try:
        result = lectura.procesar_contenido_para_publicacion(pdf_path=path, fuente='pdf')
        v = result['validacion']
        print(f'Valid: {v["valid"]}')
        print(f'Errors: {v["errors"]}')
        print(f'Pages: {len(result["paginas"])}')
        print(f'Chapters: {len(result["capitulos"])}')
        print(f'Content length: {len(result["content"])}')
        if result['paginas']:
            print(f'First page sample: {result["paginas"][0][:200]}')
        if result['capitulos']:
            for c in result['capitulos'][:5]:
                print(f'  Chapter: {c["title"]} (page {c["page"]})')
    except Exception as e:
        print(f'ERROR: {e}')
