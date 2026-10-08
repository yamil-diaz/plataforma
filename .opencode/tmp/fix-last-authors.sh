#!/bin/bash
set -euo pipefail
docker exec -w /app docker-app-1 python - <<'PY'
import psycopg2, os
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
cur.execute("SELECT id, title, author_name FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido')")
rows=cur.fetchall()
print("remaining", rows)
fixes={
    133: ("Indigno de ser humano", "Makoto Shinkai"),
    151: ("Voz Horizona", "Luis Hernandez"),
}
for bid, title, author in rows:
    nt, na = fixes.get(bid, (title, author))
    cur.execute("UPDATE books SET title=%s, author_name=%s WHERE id=%s", (nt, na, bid))
    print("updated", bid, nt, na)
conn.commit()
cur.execute("SELECT count(*) FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido')")
print("unknown_left", cur.fetchone()[0])
cur.close(); conn.close()
print("DONE")
PY
