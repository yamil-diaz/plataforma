#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== migration author_withdrawals ==="
docker exec -w /app docker-app-1 python /app/migrate_withdrawals.py 2>/dev/null || \
  docker exec -i docker-db-1 psql -U aeternum -d aeternum <<'SQL'
CREATE TABLE IF NOT EXISTS author_withdrawals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    method TEXT NOT NULL DEFAULT 'bank_transfer',
    account_details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','paid')),
    admin_note TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_author_withdrawals_user ON author_withdrawals(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_author_withdrawals_status ON author_withdrawals(status, created_at DESC);
SQL

echo "=== rebuild app ==="
docker compose build app
docker compose up -d --force-recreate app
sleep 5
docker compose ps

echo "=== currencies endpoint ==="
curl -s https://aeternumlibrary.com/api/commerce/currencies
echo

echo "=== login admin ==="
curl -s -c /tmp/fin.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

echo "=== author earnings ==="
curl -s -b /tmp/fin.txt -o /tmp/earn.txt -w "earnings=%{http_code}\n" https://aeternumlibrary.com/api/author/earnings
head -c 400 /tmp/earn.txt
echo

echo "=== request withdrawal test ==="
curl -s -b /tmp/fin.txt -o /tmp/wd.txt -w "withdraw=%{http_code}\n" -X POST https://aeternumlibrary.com/api/author/withdrawals \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"amount": 10.50, "currency": "PEN", "method": "yape", "account_details": "999888777 - Test Yape"}'
head -c 400 /tmp/wd.txt
echo

echo "=== admin withdrawals ==="
curl -s -b /tmp/fin.txt -o /tmp/awd.txt -w "admin_wd=%{http_code}\n" https://aeternumlibrary.com/api/admin/withdrawals
head -c 500 /tmp/awd.txt
echo

echo "=== checkout currencies in UI bundle ==="
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
curl -s --max-time 20 "https://aeternumlibrary.com/assets/$JS" > /tmp/b3.js
grep -oE "Sol peruano|Dólar estadounidense|Mis Ganancias|author/withdrawals|author/earnings" /tmp/b3.js | sort -u

echo "=== books api still ok ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
echo DONE
