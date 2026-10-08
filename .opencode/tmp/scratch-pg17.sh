#!/bin/bash
set -euo pipefail
DUMP=/root/plataforma_ugk5_20260827_210207.dump

docker rm -f aeternum-scratch-pg 2>/dev/null || true
docker volume rm -f aeternum-scratch-pgdata 2>/dev/null || true

echo "=== start PG17 scratch ==="
docker run -d --name aeternum-scratch-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=scratch \
  -e POSTGRES_DB=aeternum \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -v aeternum-scratch-pgdata:/var/lib/postgresql/data \
  postgres:17-alpine

for i in $(seq 1 15); do
  if docker exec aeternum-scratch-pg pg_isready -U postgres >/dev/null 2>&1; then
    echo "pg ready try=$i"
    break
  fi
  sleep 2
done
docker exec aeternum-scratch-pg pg_isready -U postgres
docker logs aeternum-scratch-pg --tail 15

echo "=== copy dump and restore ==="
docker cp "$DUMP" aeternum-scratch-pg:/tmp/dump.dump
docker exec aeternum-scratch-pg pg_restore -U postgres -d aeternum --no-owner --no-acl /tmp/dump.dump 2>&1 | tail -50

echo "=== counts ==="
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) FROM reviews;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -c 'SELECT id, email, name, role FROM users ORDER BY id LIMIT 25;'

echo DONE
