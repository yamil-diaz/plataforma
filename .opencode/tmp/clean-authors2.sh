#!/bin/bash
set -euo pipefail

echo "=== clean bad authors via SQL ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
UPDATE books SET author_name='Desconocido'
WHERE published=1 AND (
  LOWER(TRIM(author_name)) IN (
    'microsoft','computer1','computer','unknown','desconocido',
    'nieto','whitby','carlos calvacho','darío botero uribe'
  )
  OR author_name ~* '^(microsoft|computer[0-9]*|toaz|libro_)'
);
"

echo "=== retry OL inside app container ==="
docker exec -w /app docker-app-1 python - <<'PY'
import json, urllib.request, urllib.parse, psycopg2, os
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
cur.execute("""SELECT id, title FROM books WHERE published=1 AND (
  author_name IS NULL OR TRIM(author_name)=''
  OR LOWER(TRIM(author_name)) IN ('desconocido','microsoft','computer1','nieto','whitby')
) ORDER BY id""")
rows=cur.fetchall()
print("retry", len(rows))
for bid, title in rows:
    q=urllib.parse.quote(title)
    try:
        req=urllib.request.Request(f"https://openlibrary.org/search.json?q={q}&limit=3&fields=title,author_name", headers={"User-Agent":"Aeternum/1.0"})
        docs=json.loads(urllib.request.urlopen(req, timeout=15).read()).get("docs") or []
    except Exception as e:
        print("err", bid, e); continue
    author=None
    for d in docs:
        names=d.get("author_name") or []
        if names:
            author=names[0]; break
    if author:
        cur.execute("UPDATE books SET author_name=%s WHERE id=%s",(author[:120], bid))
        print("fixed", bid, str(title)[:40], "->", author)
    else:
        print("still", bid, str(title)[:40])
conn.commit()
cur.execute("SELECT count(*) FROM books WHERE published=1 AND LOWER(TRIM(author_name)) IN ('desconocido','microsoft','computer1')")
print("bad_left", cur.fetchone()[0])
cur.execute("SELECT id,title,author_name FROM books WHERE id IN (158,161,164,167,169,171,147,126) ORDER BY id")
for r in cur.fetchall():
    print(r)
cur.close(); conn.close()
PY

echo "=== API ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
for b in d:
    if b["id"] in (158,161,164,167,169,171,147,126):
        print(b["id"], "|", (b.get("title") or "")[:40], "|", b.get("author_name"), "|", (b.get("cover_image_url") or "")[:45])
'
echo DONE
