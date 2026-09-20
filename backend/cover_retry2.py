#!/usr/bin/env python3
import json, urllib.request, urllib.parse, ssl, sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Check ID 204 file size
path = r'C:\Users\Z\Desktop\plataforma\backend\cover_candidates\204_cover_candidate.jpg'
print(f'ID 204 file size: {os.path.getsize(path)} bytes')

# ID 286: "El Manuscrito de un Loco" by Dickens - original is "A Madman's Manuscript" from Sketches by Boz
searches = [
    ("A Madman's Manuscript", "Dickens"),
    ("Sketches by Boz", "Dickens"),
    ("El manuscrito de un loco", "Dickens"),
    ("Madhouse", "Dickens"),
]

for title, author in searches:
    print(f'Searching: "{title}" by {author}')
    params = urllib.parse.urlencode({
        "title": title,
        "author": author,
        "limit": 5,
        "fields": "key,title,author_name,cover_i,isbn"
    })
    url = f"https://openlibrary.org/search.json?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AeternumLib/1.0"})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        docs = data.get("docs", [])
        for doc in docs:
            cover_i = doc.get("cover_i")
            isbn_list = doc.get("isbn", [])
            if cover_i:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
            elif isbn_list:
                cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn_list[0]}-L.jpg"
            else:
                continue
            
            filepath = r'C:\Users\Z\Desktop\plataforma\backend\cover_candidates\286_cover_candidate.jpg'
            req2 = urllib.request.Request(cover_url, headers={"User-Agent": "AeternumLib/1.0"})
            with urllib.request.urlopen(req2, timeout=20, context=ctx) as resp2:
                data2 = resp2.read()
                if len(data2) > 3000:
                    with open(filepath, 'wb') as f:
                        f.write(data2)
                    doc_title = doc.get("title", "?")
                    print(f"  FOUND: {len(data2)} bytes from '{doc_title}'")
                    print(f"  URL: {cover_url}")
                    break
            time.sleep(0.3)
        else:
            continue
        break
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(0.5)
else:
    print("  ID 286: Still not found after all attempts")
