#!/bin/bash
cd /root/plataforma/docker
echo "=== compose ==="
docker compose ps
echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS book_pages FROM book_pages;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM reviews;'
echo "=== users list ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, email, name, role, google_id IS NOT NULL AS g, created_at FROM users ORDER BY id LIMIT 20;'
echo "=== books sample ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, title, published, pdf_path IS NOT NULL AS has_pdf FROM books ORDER BY id LIMIT 10;'
echo "=== volume files ==="
docker run --rm -v docker_aeternum-data:/data alpine sh -c 'echo books=$(ls /data/books 2>/dev/null | wc -l); echo covers=$(ls /data/covers 2>/dev/null | wc -l); du -sh /data'
echo "=== api ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("api_books", len(d) if isinstance(d,list) else d)'
echo "=== db size ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT pg_size_pretty(pg_database_size('aeternum'));"
echo "=== recent app errors ==="
docker compose logs app --tail 40 | grep -iE 'error|exception|traceback|books|users' | tail -20
echo DONE
