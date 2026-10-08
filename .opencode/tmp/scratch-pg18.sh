#!/bin/bash
set -euo pipefail
DUMP=/root/plataforma_ugk5_20260827_210207.dump

echo "=== scratch logs ==="
docker logs aeternum-scratch-pg --tail 40 2>&1 || true
docker rm -f aeternum-scratch-pg 2>/dev/null || true
docker volume rm -f aeternum-scratch-pgdata 2>/dev/null || true

echo "=== start fresh scratch with explicit auth ==="
docker run -d --name aeternum-scratch-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=scratch \
  -e POSTGRES_DB=aeternum \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -v aeternum-scratch-pgdata:/var/lib/postgresql/data \
  postgres:18-alpine
for i in 1 2 3 4 5 6 7 8 9 10; do
  if docker exec aeternum-scratch-pg pg_isready -U postgres >/dev/null 2>&1; then
    echo "pg ready at try $i"
    break
  fi
  sleep 2
done
docker exec aeternum-scratch-pg pg_isready -U postgres
docker logs aeternum-scratch-pg --tail 20

echo "=== restore dump into scratch ==="
docker exec -i aeternum-scratch-pg psql -U postgres -d aeternum -c 'SELECT 1;' 
# mount dump and restore
docker cp "$DUMP" aeternum-scratch-pg:/tmp/dump.dump
docker exec -i aeternum-scratch-pg pg_restore -U postgres -d aeternum --no-owner --no-acl /tmp/dump.dump 2>&1 | tail -40

echo "=== counts in scratch ==="
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -c 'SELECT id, email, name, role, created_at FROM users ORDER BY id LIMIT 20;'

echo DONE
