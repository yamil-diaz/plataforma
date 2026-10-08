#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
echo "=== nginx client_max_body_size ==="
grep -n client_max_body_size nginx.conf

docker compose up -d --force-recreate nginx
docker compose build app
docker compose up -d --force-recreate app
sleep 6
docker compose ps

echo "=== upload vacalola PDF ==="
curl -s -c /tmp/vl2.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/vl2.txt -o /tmp/vl2_up.txt -w "upload=%{http_code} time=%{time_total} size_upload=%{size_upload}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=La vacalola bailarina $(date +%s)" \
  -F "author_name=José R. Solis Pinedo" \
  -F "category=Ficción" \
  -F "price=10" \
  -F "rental_price=0" \
  -F "pdf_file=@/tmp/vacalola.pdf;type=application/pdf"
head -c 700 /tmp/vl2_up.txt
echo
BOOK_ID=$(python3 -c 'import json; print(json.load(open("/tmp/vl2_up.txt")).get("id",""))' 2>/dev/null || true)
echo "book_id=$BOOK_ID"
if [ -n "$BOOK_ID" ]; then
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, author_name, price, published, page_count FROM books WHERE id=$BOOK_ID;"
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT currency, price, rental_price FROM book_prices WHERE book_id=$BOOK_ID;"
  curl -s -b /tmp/vl2.txt -o /tmp/vl2_pg.txt -w "reader=%{http_code}\n" "https://aeternumlibrary.com/api/books/$BOOK_ID/pages/1"
  python3 -c 'import json; d=json.load(open("/tmp/vl2_pg.txt")); print("pages", d.get("total_pages"), "len", len(d.get("content") or ""))'
fi

echo "=== logs ==="
docker compose logs app --tail 20 2>&1 | grep -iE 'CREATE_BOOK|POST /api/books|413|Error' | tail -10
echo DONE
