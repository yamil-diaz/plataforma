# -*- coding: utf-8 -*-
import urllib.request, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request('https://aeternum-world.onrender.com/api/books')
req.add_header('User-Agent', 'Mozilla/5.0')
resp = urllib.request.urlopen(req, timeout=30)
books = json.loads(resp.read())

unsplash = []
local_cover = []
no_cover = []

for b in books:
    url = b.get('cover_image_url') or ''
    title = (b.get('title') or '').strip()
    bid = b.get('id')

    if not url:
        no_cover.append((bid, title, url))
    elif 'unsplash' in url:
        unsplash.append((bid, title, url))
    elif '/static/covers/' in url:
        local_cover.append((bid, title, url))
    else:
        no_cover.append((bid, title, url))

print('Total: %d libros publicados' % len(books))
print('')
print('PORTADA ESPECIFICA (local): %d' % len(local_cover))
for bid, title, url in local_cover:
    fname = url.split('/')[-1]
    print('  ID %d: %s -> %s' % (bid, title, fname))
print('')
print('PORTADA GENERICA (Unsplash): %d' % len(unsplash))
for bid, title, url in unsplash:
    print('  ID %d: %s' % (bid, title))
print('')
print('SIN PORTADA: %d' % len(no_cover))
for bid, title, url in no_cover:
    display = url if url else '(vacia)'
    print('  ID %d: %s -> %s' % (bid, title, display))

# Save full data for later
with open('production_books.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)
print('')
print('Saved to production_books.json')
