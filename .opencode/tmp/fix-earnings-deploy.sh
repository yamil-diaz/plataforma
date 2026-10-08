#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
docker compose build app
docker compose up -d --force-recreate app
sleep 5

curl -s -c /tmp/e2.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

echo "=== earnings ==="
curl -s -b /tmp/e2.txt -o /tmp/e2e.txt -w "earnings=%{http_code}\n" https://aeternumlibrary.com/api/author/earnings
head -c 600 /tmp/e2e.txt
echo

echo "=== currencies ==="
curl -s https://aeternumlibrary.com/api/commerce/currencies
echo

echo "=== withdrawal (should be 400 if no balance) ==="
curl -s -b /tmp/e2.txt -o /tmp/w2.txt -w "withdraw=%{http_code}\n" -X POST https://aeternumlibrary.com/api/author/withdrawals \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"amount": 5.00, "currency": "PEN", "method": "yape", "account_details": "999111222"}'
head -c 300 /tmp/w2.txt
echo

echo "=== books ok ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
echo DONE
