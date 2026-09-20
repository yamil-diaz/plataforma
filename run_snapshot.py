import os
import sys

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ['STORAGE_DIR'] = os.getenv('STORAGE_DIR', 'backend/storage')

from diag_catalog import _desde_snapshot, _clasificar_libros, _reporte_json

libros, duplicados = _desde_snapshot('backend/diag_result.json')
libros = _clasificar_libros(libros, duplicados)
_reporte_json(libros, resumen_only=True)