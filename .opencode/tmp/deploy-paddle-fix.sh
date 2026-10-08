#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
docker compose build app
docker compose up -d --force-recreate app
sleep 5
docker compose ps

echo "=== test checkout book 1 USD purchase ==="
curl -s -c /tmp/pa2.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/pa2.txt -o /tmp/co2.txt -w "checkout=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_purchase","currency":"USD"}'
head -c 700 /tmp/co2.txt; echo
python3 -c 'import json; d=json.load(open("/tmp/co2.txt")); print("payment_url", (d.get("payment_url") or "")[:80]); print("order_id", d.get("order_id"))' 2>/dev/null || true

echo "=== test rental if price exists ==="
curl -s -b /tmp/pa2.txt -o /tmp/co3.txt -w "rental=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_rental","currency":"USD","rental_days":7}'
head -c 400 /tmp/co3.txt; echo

echo "=== paddle logs ==="
docker compose logs app --tail 25 2>&1 | grep -iE 'PADDLE|checkout|tax' | tail -15
echo DONE
