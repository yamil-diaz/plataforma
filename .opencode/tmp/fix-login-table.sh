#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== create login_attempts if missing ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    ip_address TEXT NOT NULL UNIQUE,
    attempts INTEGER NOT NULL DEFAULT 0,
    lockout_until TEXT,
    updated_at TEXT
);
SQL

echo "=== list tables like attempt/lock ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE '%attempt%' OR tablename LIKE '%lock%' OR tablename LIKE '%login%' OR tablename LIKE '%password%');"

echo "=== try login ==="
curl -s -D - -o /tmp/login3.txt -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}' | head -30
echo "--- body ---"
cat /tmp/login3.txt | head -c 400
echo

echo "=== try login user ositoperu ==="
curl -s -o /tmp/login4.txt -w "status=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"ositoperu1022@gmail.com","password":"test1234"}'
cat /tmp/login4.txt | head -c 300
echo

echo "=== app logs tail ==="
docker compose logs app --tail 15
echo DONE
