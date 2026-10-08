#!/bin/bash
set -euo pipefail

echo "=== all public tables ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"

echo "=== create login_attempts via stdin ==="
echo "CREATE TABLE IF NOT EXISTS login_attempts (ip_address TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0, lockout_until TEXT);" | docker exec -i docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1

echo "=== verify table ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='login_attempts';"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "\d login_attempts"

echo "=== login admin ==="
curl -s -o /tmp/l.txt -w "admin_login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
head -c 400 /tmp/l.txt
echo

echo "=== login register test user path ==="
curl -s -o /tmp/reg.txt -w "register=%{http_code}\n" -X POST https://aeternumlibrary.com/api/register \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"name":"Test Login","email":"testlogin@example.com","password":"Test1234!"}'
head -c 400 /tmp/reg.txt
echo

echo "=== login new user ==="
curl -s -o /tmp/l2.txt -w "user_login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"testlogin@example.com","password":"Test1234!"}'
head -c 400 /tmp/l2.txt
echo

echo "=== app logs ==="
cd /root/plataforma/docker && docker compose logs app --tail 20
echo DONE
