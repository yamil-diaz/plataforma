import os
from dotenv import load_dotenv
load_dotenv()
os.environ['STORAGE_DIR'] = 'backend/storage'

exec(open('backend/diag_catalog.py', encoding='utf-8').read())