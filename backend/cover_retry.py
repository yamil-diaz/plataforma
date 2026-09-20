#!/usr/bin/env python3
"""
Retry failed books with broader search strategies.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl
import codecs
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BACKEND = Path(__file__).parent
CANDIDATES = BACKEND / "cover_candidates"

# Load results JSON
with open(BACKEND / "cover_phase2_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# The 12 failed books with alternative search terms
retry_books = [
    {"id": 204, "title": "En la Colonia Penitenciaria", "author": "Franz Kafka",
     "alt_titles": ["In the Penal Colony", "En la colonia penitenciaria", "Kafka In der Strafkolonie"]},
    {"id": 206, "title": "Las Preocupaciones de un Padre de Familia", "author": "Franz Kafka",
     "alt_titles": ["Sorge eines Vaters", "A Father's Concern", "Preocupaciones de un padre"]},
    {"id": 208, "title": "Josefina la Cantora o El Pueblo de los Ratones", "author": "Franz Kafka",
     "alt_titles": ["Josefina die Sängerin", "Josephine the Singer", "Josefina la cantora"]},
    {"id": 214, "title": "El Adolescente", "author": "Fiódor Dostoyevski",
     "alt_titles": ["The Adolescent", "El adolescente", "Подросток"]},
    {"id": 217, "title": "Los Endemoniados", "author": "Fiódor Dostoyevski",
     "alt_titles": ["The Devils", "Los demonios", "Demons Dostoevsky", "I demoni"]},
    {"id": 221, "title": "La Patrona", "author": "Fiódor Dostoyevski",
     "alt_titles": ["The Mistress", "La padrona", "Хозяйка"]},
    {"id": 236, "title": "El Doctor Ox", "author": "Julio Verne",
     "alt_titles": ["Doctor Ox", "Le Docteur Ox", "Doctor Who"]},
    {"id": 270, "title": "La Agencia Thompson y Cía", "author": "Julio Verne",
     "alt_titles": ["Thompson and Co", "L'Agence Thompson", "Thompson y Cia"]},
    {"id": 280, "title": "El Misterio de Edwin Drood", "author": "Charles Dickens",
     "alt_titles": ["The Mystery of Edwin Drood", "Mystery of Edwin Drood"]},
    {"id": 286, "title": "El Manuscrito de un Loco", "author": "Charles Dickens",
     "alt_titles": ["A Madman's Manuscript", "The Madman's Manuscript", "Manuscrito de un loco"]},
    {"id": 290, "title": "Cuento de Navidad", "author": "Charles Dickens",
     "alt_titles": ["A Christmas Carol", "Un cuento de Navidad", "Christmas Carol Dickens"]},
    {"id": 277, "title": "Historia de Dos Ciudades", "author": "Charles Dickens",
     "alt_titles": ["A Tale of Two Cities", "Un cuento de dos ciudades"]},
]

def download_image(url, filepath, timeout=30):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AeternumLib/1.0; cover research)"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            if len(data) < 3000:
                return False
            with open(filepath, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        return False

def get_file_info(filepath):
    try:
        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            header = f.read(16)
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            fmt = "PNG"
        elif header[:3] == b'\xff\xd8\xff':
            fmt = "JPEG"
        else:
            fmt = "Unknown"
        return size, fmt
    except:
        return 0, "Unknown"

results_new = []
still_failed = []

for book in retry_books:
    bid = book["id"]
    title = book["title"]
    
    print(f"\n--- ID {bid}: {title} ---")
    
    found = False
    
    # Strategy 1: Try each alt title on Open Library
    for alt_title in book["alt_titles"]:
        if found:
            break
        
        params = urllib.parse.urlencode({
            "title": alt_title,
            "author": book["author"].split()[0],  # Just first name
            "limit": 3,
            "fields": "key,title,author_name,first_publish_year,cover_i,isbn"
        })
        url = f"https://openlibrary.org/search.json?{params}"
        
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "AeternumLib/1.0"
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = json.loads(resp.read().decode())
            
            docs = data.get("docs", [])
            
            for doc in docs:
                cover_i = doc.get("cover_i")
                if not cover_i:
                    isbn_list = doc.get("isbn", [])
                    if isbn_list:
                        cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn_list[0]}-L.jpg"
                    else:
                        continue
                else:
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
                
                filename = f"{bid}_cover_candidate.jpg"
                filepath = CANDIDATES / filename
                
                if download_image(cover_url, filepath):
                    size, fmt = get_file_info(filepath)
                    if size > 3000:
                        results_new.append({
                            "id": bid,
                            "title": title,
                            "author": book["author"],
                            "source": "Open Library",
                            "url": cover_url,
                            "filename": filename,
                            "size": size,
                            "format": fmt,
                            "status": "DESCARGADA"
                        })
                        print(f"  FOUND on Open Library: {filename} ({size} bytes)")
                        found = True
                        break
                
                time.sleep(0.3)
        except Exception as e:
            pass
        
        time.sleep(0.3)
    
    # Strategy 2: Try Internet Archive with broader query
    if not found:
        search_terms = [title] + book["alt_titles"][:2]
        for search_term in search_terms:
            if found:
                break
            
            ia_query = urllib.parse.quote(f'{search_term} {book["author"].split()[0]}')
            ia_url = f"https://archive.org/advancedsearch.php?q=title%3A({ia_query})&fl[]=identifier,title&sort[]=downloads+desc&rows=3&output=json"
            
            try:
                req = urllib.request.Request(ia_url, headers={
                    "User-Agent": "AeternumLib/1.0"
                })
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    data = json.loads(resp.read().decode())
                
                docs = data.get("response", {}).get("docs", [])
                
                for doc in docs:
                    identifier = doc.get("identifier", "")
                    doc_title = doc.get("title", "")
                    
                    # Try thumbnail
                    cover_url = f"https://archive.org/download/{identifier}/__ia_thumb.jpg"
                    filename = f"{bid}_cover_candidate.jpg"
                    filepath = CANDIDATES / filename
                    
                    if download_image(cover_url, filepath):
                        size, fmt = get_file_info(filepath)
                        if size > 3000:
                            results_new.append({
                                "id": bid,
                                "title": title,
                                "author": book["author"],
                                "source": "Internet Archive",
                                "url": cover_url,
                                "filename": filename,
                                "size": size,
                                "format": fmt,
                                "status": "DESCARGADA"
                            })
                            print(f"  FOUND on Internet Archive: {filename} ({size} bytes)")
                            found = True
                            break
                    
                    # Try first jpg in archive
                    files_url = f"https://archive.org/metadata/{identifier}/files"
                    try:
                        req2 = urllib.request.Request(files_url, headers={"User-Agent": "AeternumLib/1.0"})
                        with urllib.request.urlopen(req2, timeout=15, context=ctx) as resp2:
                            files_data = json.loads(resp2.read().decode())
                        
                        for f in files_data.get("result", []):
                            name = f.get("name", "")
                            if name.lower().endswith(('.jpg', '.jpeg', '.png')) and not name.startswith('__'):
                                img_url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(name)}"
                                if download_image(img_url, filepath):
                                    size, fmt = get_file_info(filepath)
                                    if size > 3000:
                                        results_new.append({
                                            "id": bid,
                                            "title": title,
                                            "author": book["author"],
                                            "source": "Internet Archive",
                                            "url": img_url,
                                            "filename": filename,
                                            "size": size,
                                            "format": fmt,
                                            "status": "DESCARGADA"
                                        })
                                        print(f"  FOUND on Internet Archive (file): {filename} ({size} bytes)")
                                        found = True
                                        break
                    except:
                        pass
                
                time.sleep(0.3)
            except:
                pass
            
            time.sleep(0.3)
    
    # Strategy 3: Try Wikimedia Commons
    if not found:
        wm_query = urllib.parse.quote(f'{title} {book["author"]}')
        wm_url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={wm_query}&srnamespace=6&format=json&srlimit=3"
        
        try:
            req = urllib.request.Request(wm_url, headers={"User-Agent": "AeternumLib/1.0"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode())
            
            results_list = data.get("query", {}).get("search", [])
            
            for item in results_list:
                title_wm = item.get("title", "")
                if any(ext in title_wm.lower() for ext in ['.jpg', '.jpeg', '.png', '.svg']):
                    # Get the image URL
                    image_title = urllib.parse.quote(title_wm.replace("File:", ""))
                    info_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{image_title}&prop=imageinfo&iiprop=url|size&format=json"
                    
                    req2 = urllib.request.Request(info_url, headers={"User-Agent": "AeternumLib/1.0"})
                    with urllib.request.urlopen(req2, timeout=15, context=ctx) as resp2:
                        info_data = json.loads(resp2.read().decode())
                    
                    pages = info_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        imageinfo = page.get("imageinfo", [{}])[0]
                        img_url = imageinfo.get("url", "")
                        
                        if img_url:
                            filename = f"{bid}_cover_candidate.jpg"
                            filepath = CANDIDATES / filename
                            
                            if download_image(img_url, filepath):
                                size, fmt = get_file_info(filepath)
                                if size > 3000:
                                    results_new.append({
                                        "id": bid,
                                        "title": title,
                                        "author": book["author"],
                                        "source": "Wikimedia Commons",
                                        "url": img_url,
                                        "filename": filename,
                                        "size": size,
                                        "format": fmt,
                                        "status": "DESCARGADA"
                                    })
                                    print(f"  FOUND on Wikimedia Commons: {filename} ({size} bytes)")
                                    found = True
                                    break
        except:
            pass
    
    if not found:
        print(f"  NOT FOUND after all strategies")
        still_failed.append(book)
    
    time.sleep(0.5)

print(f"\n\n=== RETRY RESULTS ===")
print(f"Found: {len(results_new)}")
print(f"Still failed: {len(still_failed)}")

for r in results_new:
    print(f"  ID {r['id']}: {r['filename']} ({r['size']} bytes) from {r['source']}")

for f in still_failed:
    print(f"  ID {f['id']}: {f['title']} - NOT FOUND")

# Save retry results
with open(BACKEND / "cover_phase2_retry_results.json", "w", encoding="utf-8") as f:
    json.dump({"new_results": results_new, "still_failed": still_failed}, f, ensure_ascii=False, indent=2)
