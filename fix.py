import os
import glob

search_dir = r'c:\Users\Z\Downloads\plataforma\frontend\src'
files = glob.glob(search_dir + '/**/*.jsx', recursive=True)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace("|| 'http://localhost:8000/api'", "|| '/api'")
    new_content = new_content.replace(": 'http://localhost:8000'", ": ''")
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {file}')
