#!/bin/bash
echo "=== covers sample from DB ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
SELECT id, title, left(cover_image_url, 70) AS cover
FROM books
WHERE id IN (158,161,164,167,169,171,159)
ORDER BY id;
"

echo "=== HTTP covers ==="
for id in 158 161 164 167 169 171; do
  C=$(docker exec docker-db-1 psql -U aeternum -d aeternum -tAc "SELECT cover_image_url FROM books WHERE id=$id;")
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://aeternumlibrary.com$C")
  echo "book=$id cover_http=$code"
done

echo "=== catalog unsplash leftovers ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE cover_image_url LIKE 'https://images.unsplash.com%';"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE cover_image_url LIKE '/static/covers/%';"

echo "=== api sample covers ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
for b in d:
    if b["id"] in (158,161,164,171):
        print(b["id"], b["title"][:35], "->", (b.get("cover_image_url") or "")[:55])
'
echo DONE
