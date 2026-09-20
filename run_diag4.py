import os
import sys

# Directly set environment variables
os.environ['DATABASE_URL'] = 'postgresql://postgres:yamilpro002@localhost:5432/plataforma_dev'
os.environ['STORAGE_DIR'] = 'backend/storage'

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Now run the diagnostic
from diag_catalog import main
import sys as _sys

# Patch sys.argv
_sys.argv = ['diag_catalog.py', '--resumen']
main()