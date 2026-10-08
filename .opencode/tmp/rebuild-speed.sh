#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
sed -i 's/- "8000:8000"/- "127.0.0.1:8000:8000"/' docker-compose.yml || true
grep -n '8000' docker-compose.yml

docker compose build app
docker compose up -d --force-recreate app
sleep 5
docker compose ps

echo "=== speed test books ==="
for i in 1 2 3; do
  curl -s -o /tmp/bx.txt -w "books$i=%{http_code} t=%{time_total} size=%{size_download}\n" --max-time 20 https://aeternumlibrary.com/api/books
done
python3 -c 'import json; d=json.load(open("/tmp/bx.txt")); print("len", len(d) if isinstance(d,list) else d); print("has_content", "content" in (d[0] if isinstance(d,list) and d else {}))'

echo "=== login + me + page ==="
curl -s -c /tmp/fin.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/fin.txt -o /dev/null -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me
curl -s -b /tmp/fin.txt -o /tmp/pg.txt -w "page=%{http_code}\n" https://aeternumlibrary.com/api/books/1/pages/1
python3 -c 'import json; d=json.load(open("/tmp/pg.txt")); print("reader", d.get("total_pages"), "len", len(d.get("content") or ""))'

echo "=== conns ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='aeternum';"
docker compose logs app --tail 20 2>&1 | grep -iE 'pool exhausted|too many' || echo no_pool_err

echo DONE
