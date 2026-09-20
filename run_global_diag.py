import os
from dotenv import load_dotenv
load_dotenv()
os.environ['STORAGE_DIR'] = 'backend/storage'

exec(open('backend/global_diagnostic.py', encoding='utf-8').read())