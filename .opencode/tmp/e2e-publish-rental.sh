#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
docker compose build app
docker compose up -d --force-recreate app
sleep 5

echo "=== login admin ==="
curl -s -c /tmp/bk.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

echo "=== use real PDF from volume as upload source ==="
PDF=$(docker exec docker-app-1 sh -c 'ls /data/aeternum/books/*.pdf 2>/dev/null | head -1')
echo "sample_pdf=$PDF"
docker cp "docker-app-1:${PDF}" /tmp/real_book.pdf
ls -lh /tmp/real_book.pdf

TITLE="Publicacion E2E $(date +%s)"
curl -s -b /tmp/bk.txt -o /tmp/e2e_pub.txt -w "publish=%{http_code}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=$TITLE" \
  -F "author_name=Autor E2E" \
  -F "category=Ficción" \
  -F "price=20.00" \
  -F "rental_price=6.50" \
  -F "pdf_file=@/tmp/real_book.pdf;type=application/pdf"
head -c 600 /tmp/e2e_pub.txt
echo
BOOK_ID=$(python3 -c 'import json; print(json.load(open("/tmp/e2e_pub.txt")).get("id",""))' 2>/dev/null || true)
echo "book_id=$BOOK_ID"

echo "=== book_prices ==="
if [ -n "$BOOK_ID" ]; then
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT book_id, currency, price, rental_price, is_active FROM book_prices WHERE book_id=$BOOK_ID;"
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, price, published, page_count FROM books WHERE id=$BOOK_ID;"
  curl -s -b /tmp/bk.txt -o /tmp/e2e_page.txt -w "reader=%{http_code}\n" "https://aeternumlibrary.com/api/books/$BOOK_ID/pages/1"
  python3 -c 'import json; d=json.load(open("/tmp/e2e_page.txt")); print("pages_total", d.get("total_pages"), "len", len(d.get("content") or ""))'
  curl -s -b /tmp/bk.txt -o /tmp/e2e_prices.txt -w "prices=%{http_code}\n" "https://aeternumlibrary.com/api/books/$BOOK_ID/prices"
  cat /tmp/e2e_prices.txt | head -c 400
  echo
  echo "=== checkout USD rental ==="
  curl -s -b /tmp/bk.txt -o /tmp/e2e_co.txt -w "checkout=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
    -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
    -d "{\"book_id\":$BOOK_ID,\"item_type\":\"digital_rental\",\"currency\":\"USD\",\"rental_days\":7}"
  head -c 400 /tmp/e2e_co.txt
  echo
  echo "=== checkout USD purchase ==="
  curl -s -b /tmp/bk.txt -o /tmp/e2e_co2.txt -w "purchase=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
    -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
    -d "{\"book_id\":$BOOK_ID,\"item_type\":\"digital_purchase\",\"currency\":\"USD\"}"
  head -c 400 /tmp/e2e_co2.txt
  echo
fi

echo "=== catalog has rental_price ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("len",len(d)); print("sample_keys", sorted(d[0].keys()) if d else []); print("with_rental", sum(1 for b in d if b.get("rental_price")))'

echo DONE
