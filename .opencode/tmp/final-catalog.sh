#!/bin/bash
set -euo pipefail
docker exec -w /app docker-app-1 python - <<'PY'
import psycopg2, os
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
# títulos legibles + autores conocidos
fixes = [
    (133, "Indigno de ser humano", "Makoto Shinkai"),
    (151, "Voz Horizona", "Luis Hernandez"),
]
for bid, title, author in fixes:
    cur.execute("UPDATE books SET title=%s, author_name=%s WHERE id=%s", (title, author, bid))
    print("fixed", bid, title, author)
conn.commit()
cur.execute("SELECT count(*) FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido')")
print("unknown_left", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM books WHERE cover_image_url LIKE '/static/covers/%'")
print("local_covers", cur.fetchone()[0])
cur.close(); conn.close()
print("DONE")
PY

echo "=== catalog formal sample ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("total", len(d))
bad_a=sum(1 for b in d if not (b.get("author_name") or "").strip() or b.get("author_name","").lower()=="desconocido")
bad_c=sum(1 for b in d if not (b.get("cover_image_url") or "").startswith("/static/covers/"))
print("sin_autor_o_desconocido", bad_a)
print("sin_portada_local", bad_c)
print("--- muestra ---")
for b in d[:8]:
    print(f"{b[\"id\"]:>3} | {(b.get('title') or '')[:42]:<42} | {(b.get('author_name') or '')[:28]:<28} | {(b.get('cover_image_url') or '')[:30]}")
for b in d:
    if b["id"] in (158,161,164,171,126,147):
        print(f"{b[\"id\"]:>3} | {(b.get('title') or '')[:42]:<42} | {(b.get('author_name') or '')[:28]:<28} | portada_local={str(b.get(\"cover_image_url\",\"\")).startswith(\"/static/covers/\")}")
'
echo DONE
