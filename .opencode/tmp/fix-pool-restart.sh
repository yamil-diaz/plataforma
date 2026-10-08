#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== copy fixed database.py ==="
# ya está en /root/plataforma/backend/database.py via scp anterior? copiar de local via docker build context
ls -la /root/plataforma/backend/database.py | head -1
grep -n "DB_POOL_MAX\|_discard_broken\|_DirectConnection\|max_connections" /root/plataforma/backend/database.py | head -15
grep -n "max_connections\|DB_POOL_MAX\|RENDER=" docker-compose.yml | head -15

echo "=== rebuild app + restart db with more connections ==="
docker compose build app
docker compose up -d --force-recreate db app
sleep 8
docker compose ps

echo "=== postgres max_connections ==="
for i in 1 2 3 4 5; do
  if docker exec docker-db-1 pg_isready -U aeternum >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SHOW max_connections;"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS conns FROM pg_stat_activity WHERE datname='aeternum';"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS pages FROM book_pages;'

echo "=== app env ==="
docker exec docker-app-1 printenv DB_POOL_MAX RENDER ENV STORAGE_DIR

echo "=== login + books + me x5 ==="
curl -s -c /tmp/fix.txt -o /tmp/fixb.txt -w "login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
head -c 200 /tmp/fixb.txt; echo
for i in 1 2 3 4 5; do
  curl -s -b /tmp/fix.txt -o /dev/null -w "me$i=%{http_code}\n" https://aeternumlibrary.com/api/me
  curl -s -o /tmp/bx.txt -w "books$i=%{http_code} t=%{time_total}\n" --max-time 20 https://aeternumlibrary.com/api/books
done
python3 -c 'import json; d=json.load(open("/tmp/bx.txt")); print("books_len", len(d) if isinstance(d,list) else d)'
curl -s -b /tmp/fix.txt -o /tmp/pg.txt -w "page=%{http_code}\n" https://aeternumlibrary.com/api/books/1/pages/1
python3 -c 'import json; d=json.load(open("/tmp/pg.txt")); print("reader_total", d.get("total_pages"))'

echo "=== pool errors in logs? ==="
docker compose logs app --tail 30 2>&1 | grep -iE 'pool exhausted|too many clients' | tail -5 || echo no_pool_errors

echo DONE
