#!/bin/bash
echo "=== final counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS book_pages FROM book_pages;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS books_with_pages FROM books b WHERE EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id);"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS need_cover FROM books WHERE cover_image_url IS NULL OR cover_image_url='';"

echo "=== book without pages ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT b.id, b.title, length(coalesce(b.content,'')) AS clen, b.pdf_path IS NOT NULL AS pdf FROM books b WHERE NOT EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id);"

echo "=== test reader page ==="
curl -s -c /tmp/rd.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/rd.txt -o /tmp/page1.txt -w "page1=%{http_code}\n" https://aeternumlibrary.com/api/books/1/pages/1
python3 -c 'import json; d=json.load(open("/tmp/page1.txt")); print("book",d.get("book_id"),"page",d.get("page_number"),"total",d.get("total_pages"),"content_len",len(d.get("content") or ""))'
curl -s -b /tmp/rd.txt -o /tmp/page2.txt -w "page_mid=%{http_code}\n" https://aeternumlibrary.com/api/books/2/pages/5
python3 -c 'import json; d=json.load(open("/tmp/page2.txt")); print("book2 total",d.get("total_pages"),"len",len(d.get("content") or ""))'

echo "=== sample covers ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, left(cover_image_url,70) AS cover FROM books WHERE id IN (1,50,100,170,171);"

echo "=== covers HTTP ==="
COVER=$(docker exec docker-db-1 psql -U aeternum -d aeternum -tAc "SELECT cover_image_url FROM books WHERE id=1;")
echo "cover=$COVER"
curl -s -o /dev/null -w "cover_http=%{http_code}\n" "https://aeternumlibrary.com$COVER"

echo DONE
