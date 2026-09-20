import os
import sys

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

os.environ['STORAGE_DIR'] = os.getenv('STORAGE_DIR', 'backend/storage')

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Now run the diagnostic
from diag_catalog import main
import sys as _sys

# Patch sys.argv
_sys.argv = ['diag_catalog.py', '--resumen']
main()