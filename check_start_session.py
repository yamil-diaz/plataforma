import subprocess
result = subprocess.run(['git', 'show', 'HEAD:backend/server.py'], capture_output=True)
content = result.stdout
idx = content.find(b'async def start_reading_session')
if idx >= 0:
    snippet = content[idx:idx+1500]
    print(snippet.decode('utf-8', errors='ignore')[:1500])
else:
    print('Function not found in HEAD')