#!/usr/bin/env python3
import json, urllib.request, urllib.parse, psycopg2, os
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()

# fixes conocidos
manual = {
    "El loco por fuerza": "Lope de Vega",
    "La bella malmaridada": "Lope de Vega",
    "Las ferias de Madrid": "Lope de Vega",
    "La fianza satisfecha": "Lope de Vega",
}
cur.execute("SELECT id, title FROM books WHERE published=1 AND LOWER(TRIM(author_name)) IN ('desconocido','') OR author_name IS NULL")
rows=cur.fetchall()
print("need", len(rows))
for bid, title in rows:
    t=(title or "").strip()
    author=manual.get(t)
    if not author:
        q=urllib.parse.quote(t)
        try:
            req=urllib.request.Request(f"https://openlibrary.org/search.json?q={q}&limit=3&fields=title,author_name", headers={"User-Agent":"AeternumLibrary/1.0"})
            docs=json.loads(urllib.request.urlopen(req, timeout=15).read()).get("docs") or []
            for d in docs:
                names=d.get("author_name") or []
                if names:
                    author=names[0]; break
        except Exception as e:
            print("err", bid, e)
    if author:
        cur.execute("UPDATE books SET author_name=%s WHERE id=%s",(author[:120], bid))
        print("OK", bid, t[:45], "->", author)
    else:
        print("FAIL", bid, t[:45])
conn.commit()
cur.execute("SELECT id,title,author_name FROM books WHERE published=1 AND id IN (158,161,162,164,165,170,171) ORDER BY id")
for r in cur.fetchall():
    print(r)
cur.execute("SELECT count(*) FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido')")
print("unknown_left", cur.fetchone()[0])
cur.close(); conn.close()
print("DONE")
