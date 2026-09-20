import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ['STORAGE_DIR'] = os.getenv('STORAGE_DIR', 'backend/storage')

from diag_catalog import _desde_snapshot, _clasificar_libros

libros, duplicados = _desde_snapshot('backend/diag_result.json')
libros = _clasificar_libros(libros, duplicados)

# Find books with 0 pages or missing page_count
for b in libros:
    if b.get('page_count') == 0 or b.get('page_count') is None:
        print(f"ID={b['id']} Title='{b.get('title', '')}' page_count={b.get('page_count')} book_pages={b.get('n_book_pages')} clasif={b['clasificacion_final']}")

# Also check ID 18 and 128
for b in libros:
    if b.get('id') in [18, 128]:
        print(f"ID={b['id']} Title='{b.get('title', '')}' page_count={b.get('page_count')} book_pages={b.get('n_book_pages')} clasif={b['clasificacion_final']}")