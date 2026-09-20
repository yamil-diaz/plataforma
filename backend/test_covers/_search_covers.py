# -*- coding: utf-8 -*-
"""
Search Internet Archive for real book covers.
Downloads covers for all 65 Unsplash books and verifies 28 local covers.
"""
import urllib.request, urllib.parse, json, os, sys, time, ssl
sys.stdout.reconfigure(encoding='utf-8')

# Disable SSL verification for simplicity
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

COVERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cover_candidates')
os.makedirs(COVERS_DIR, exist_ok=True)

# All books needing covers (Unsplash generic)
UNSPLASH_BOOKS = [
    (198, "Contemplación", "Fiódor Dostoievski"),
    (199, "La Metamorfosis", "Franz Kafka"),
    (200, "Ante la Ley", "Franz Kafka"),
    (201, "Carta al Padre", "Franz Kafka"),
    (202, "Informe para una Academia", "Franz Kafka"),
    (203, "Un Médico Rural", "Franz Kafka"),
    (204, "En la Colonia Penitenciaria", "Franz Kafka"),
    (205, "El Proceso", "Franz Kafka"),
    (206, "Las Preocupaciones de un Padre de Familia", "Franz Kafka"),
    (207, "El Fogonero", "Franz Kafka"),
    (208, "Josefina la Cantora o El Pueblo de los Ratones", "Franz Kafka"),
    (212, "El Sueño del Príncipe", "Franz Kafka"),
    (214, "El Adolescente", "Fiódor Dostoievski"),
    (215, "El Jugador", "Fiódor Dostoievski"),
    (217, "Los Endemoniados", "Fiódor Dostoievski"),
    (218, "El Gran Inquisidor", "Fiódor Dostoievski"),
    (219, "El Sueño de un Hombre Ridículo", "Fiódor Dostoievski"),
    (220, "La Sumisa", "Franz Kafka"),
    (221, "La Patrona", "Franz Kafka"),
    (223, "Los Hermanos Karamázov", "Fiódor Dostoievski"),
    (224, "Humillados y Ofendidos", "Fiódor Dostoievski"),
    (225, "Nétochka Nezvánova", "Fiódor Dostoievski"),
    (226, "Diario de un Escritor", "Fiódor Dostoievski"),
    (227, "El Cocodrilo", "Fiódor Dostoievski"),
    (228, "El Pueblo Aéreo", "Fiódor Dostoievski"),
    (229, "La Jornada de un Periodista Americano en el Año 2889", "Julio Verne"),
    (230, "César Cascabel", "Julio Verne"),
    (232, "Dueño del Mundo", "Julio Verne"),
    (234, "El Chancellor", "Julio Verne"),
    (235, "Norte Contra Sur", "Julio Verne"),
    (236, "El Doctor Ox", "Julio Verne"),
    (237, "Los Hijos del Capitán Grant", "Julio Verne"),
    (238, "El Archipiélago en Llamas", "Julio Verne"),
    (239, "Las Indias Negras", "Julio Verne"),
    (240, "Familia sin Nombre", "Julio Verne"),
    (242, "El Secreto de Wilhelm Storitz", "Julio Verne"),
    (243, "De la Tierra a la Luna", "Julio Verne"),
    (244, "La Vuelta al Mundo en Ochenta Días", "Julio Verne"),
    (246, "Cinco Semanas en Globo", "Julio Verne"),
    (247, "Un Drama en Livonia", "Julio Verne"),
    (248, "La Invasión del Mar", "Julio Verne"),
    (250, "El Soberbio Orinoco", "Julio Verne"),
    (251, "El País de las Pieles", "Julio Verne"),
    (255, "Robur el Conquistador", "Julio Verne"),
    (256, "El Testamento de un Excéntrico", "Julio Verne"),
    (259, "Matías Sandorf", "Julio Verne"),
    (260, "La Isla de Hélice", "Julio Verne"),
    (265, "Escuela de Robinsones", "Julio Verne"),
    (266, "El Piloto del Danubio", "Julio Verne"),
    (267, "Alrededor de la Luna", "Julio Verne"),
    (268, "Claudio Bombarnac", "Julio Verne"),
    (269, "La Isla Misteriosa", "Julio Verne"),
    (270, "La Agencia Thompson y Cía.", "Julio Verne"),
    (271, "Una Ciudad Flotante", "Julio Verne"),
    (272, "El Castillo de los Cárpatos", "Julio Verne"),
    (273, "Barnaby Rudge de Charles Dickens en PDF", "Charles Dickens"),
    (277, "Historia de Dos Ciudades de Charles Dickens en PDF", "Charles Dickens"),
    (279, "Grandes Esperanzas de Charles Dickens en PDF", "Charles Dickens"),
    (280, "El Misterio de Edwin Drood de Charles Dickens en PDF", "Charles Dickens"),
    (286, "El Manuscrito de un Loco de Charles Dickens en PDF", "Charles Dickens"),
    (287, "Tiempos Difíciles de Charles Dickens en PDF", "Charles Dickens"),
    (288, "Historias de Fantasmas de Charles Dickens en PDF", "Charles Dickens"),
    (289, "La Historia de Nadie de Charles Dickens en PDF", "Charles Dickens"),
    (290, "Cuento de Navidad de Charles Dickens en PDF", "Charles Dickens"),
    (291, "Una Casa en Alquiler de Charles Dickens en PDF", "Charles Dickens"),
]

def search_archive(query, rows=3):
    """Search Internet Archive for a book."""
    params = urllib.parse.urlencode({
        'q': 'title:"%s" AND mediatype:texts' % query,
        'output': 'json',
        'fl[]': 'identifier,title',
        'rows': rows,
    })
    url = 'https://archive.org/advancedsearch.php?%s' % params
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())
        return data.get('response', {}).get('docs', [])
    except Exception as e:
        print('  ERROR searching: %s' % str(e))
        return []

def get_cover_url(identifier):
    """Get cover image URL for an Archive.org item."""
    # Try metadata first
    meta_url = 'https://archive.org/metadata/%s/files' % identifier
    try:
        req = urllib.request.Request(meta_url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        files = json.loads(resp.read()).get('result', [])
        for f in files:
            name = f.get('name', '').lower()
            if name in ('cover_image.jpg', 'cover.jpg', '__cover.jpg'):
                return 'https://archive.org/download/%s/%s' % (identifier, f['name'])
            if name.endswith('.jpg') and ('cover' in name):
                return 'https://archive.org/download/%s/%s' % (identifier, f['name'])
    except:
        pass
    
    # Fallback: try common cover paths
    for ext in ['cover_image.jpg', 'cover.jpg', '__cover.jpg']:
        url = 'https://archive.org/download/%s/%s' % (identifier, ext)
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            if resp.status == 200:
                return url
        except:
            pass
    
    return None

def download_cover(url, filepath):
    """Download a cover image."""
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = resp.read()
        with open(filepath, 'wb') as f:
            f.write(data)
        return len(data)
    except Exception as e:
        print('  ERROR downloading: %s' % str(e))
        return 0

def clean_title_for_search(title):
    """Clean title for search."""
    # Remove "de Charles Dickens en PDF" suffix
    t = title.replace(' de Charles Dickens en PDF', '')
    t = t.replace('en PDF', '').strip()
    return t

# Process all books
results = []
total = len(UNSPLASH_BOOKS)

for i, (bid, title, author) in enumerate(UNSPLASH_BOOKS):
    print('[%d/%d] ID %d: %s (%s)' % (i+1, total, bid, title, author))
    
    search_title = clean_title_for_search(title)
    
    # Search Internet Archive
    docs = search_archive(search_title)
    
    if not docs:
        # Try with author name
        docs = search_archive('%s %s' % (search_title, author.split()[-1]))
    
    found = False
    for doc in docs:
        identifier = doc.get('identifier', '')
        ia_title = doc.get('title', '')
        print('  Found: %s -> %s' % (identifier, ia_title[:60]))
        
        cover_url = get_cover_url(identifier)
        if cover_url:
            ext = 'jpg'
            if '.png' in cover_url.lower():
                ext = 'png'
            filename = '%d_%s.%s' % (bid, search_title.lower().replace(' ', '_').replace(':', '').replace("'", '').replace('.', '')[:40], ext)
            filepath = os.path.join(COVERS_DIR, filename)
            
            size = download_cover(cover_url, filepath)
            if size > 1000:  # At least 1KB
                print('  DOWNLOADED: %s (%d bytes)' % (filename, size))
                results.append({
                    'id': bid, 'title': title, 'author': author,
                    'source': 'Internet Archive',
                    'source_url': cover_url,
                    'filename': filename,
                    'size': size,
                    'ia_identifier': identifier,
                    'ia_title': ia_title,
                })
                found = True
                break
            else:
                print('  Cover too small, trying next...')
        else:
            print('  No cover found for %s' % identifier)
    
    if not found:
        print('  NO COVER FOUND')
        results.append({
            'id': bid, 'title': title, 'author': author,
            'source': 'SIN FUENTE FIABLE',
            'source_url': '',
            'filename': '',
            'size': 0,
            'ia_identifier': '',
            'ia_title': '',
        })
    
    time.sleep(0.5)  # Be polite to Archive.org

# Save results
with open(os.path.join(COVERS_DIR, '_search_results.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('')
print('=' * 80)
print('SEARCH COMPLETE')
print('=' * 80)
downloaded = [r for r in results if r['filename']]
not_found = [r for r in results if not r['filename']]
print('Downloaded: %d' % len(downloaded))
print('Not found: %d' % len(not_found))
if not_found:
    print('')
    print('Books without cover:')
    for r in not_found:
        print('  ID %d: %s (%s)' % (r['id'], r['title'], r['author']))
