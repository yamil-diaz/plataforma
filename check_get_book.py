import subprocess
result = subprocess.run(['git', 'show', 'HEAD:backend/server.py'], capture_output=True)
content = result.stdout
idx = content.find(b'@api_router.get("/books/{book_id}")')
if idx >= 0:
    snippet = content[idx:idx+2000]
    print(snippet.decode('utf-8', errors='ignore')[:2000])
else:
    print('Function not found in HEAD')