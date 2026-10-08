#!/bin/bash
echo "=== paddle env ==="
docker exec docker-app-1 sh -c 'for k in PADDLE_API_KEY PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_ENVIRONMENT; do v=$(printenv $k 2>/dev/null || true); if [ -z "$v" ]; then echo "$k=EMPTY"; else echo "$k=SET(len=${#v})"; fi; done'
echo "=== try checkout as admin on book 1 ==="
curl -s -c /tmp/pa.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/pa.txt -o /tmp/co.txt -w "checkout=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_purchase","currency":"USD"}'
head -c 800 /tmp/co.txt; echo
echo "=== book 1 price ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, price, is_physical, physical_price, stock, published FROM books WHERE id=1;"
echo "=== app logs paddle ==="
cd /root/plataforma/docker && docker compose logs app --tail 50 2>&1 | grep -iE 'paddle|checkout|payment|Error al conectar|transaction' | tail -30
echo "=== provider code snippet ==="
grep -n "Error al conectar\|create_checkout\|api.paddle\|PADDLE_API" /root/plataforma/backend/server.py /root/plataforma/backend/payment_providers.py | head -30
echo DONE
