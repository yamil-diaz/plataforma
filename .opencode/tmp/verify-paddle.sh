#!/bin/bash
curl -s -c /tmp/pv.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

echo "=== purchase book 1 ==="
curl -s -b /tmp/pv.txt -o /tmp/pv1.txt -w "purchase=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_purchase","currency":"USD"}'
python3 -c 'import json; d=json.load(open("/tmp/pv1.txt")); print("order",d.get("order_id"),"txn",(d.get("transaction_id") or "")[:30],"url",(d.get("payment_url") or "")[:60],"total",d.get("total"))'

echo "=== rental book 1 ==="
curl -s -b /tmp/pv.txt -o /tmp/pv2.txt -w "rental=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_rental","currency":"USD","rental_days":7}'
python3 -c 'import json; d=json.load(open("/tmp/pv2.txt")); print(d)'

echo "=== logs ==="
cd /root/plataforma/docker && docker compose logs app --tail 20 2>&1 | grep -iE 'PADDLE|tax=|checkout' | tail -12
echo DONE
