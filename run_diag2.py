import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
os.environ['STORAGE_DIR'] = os.getenv('STORAGE_DIR', 'backend/storage')

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

exec(open(os.path.join(os.path.dirname(__file__), 'backend/diag_catalog.py'), encoding='utf-8').read())