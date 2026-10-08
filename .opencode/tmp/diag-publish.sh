#!/bin/bash
set -euo pipefail

echo "=== book_prices table ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "\d book_prices" 2>&1 | head -25

echo "=== commerce tables ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('book_prices','orders','order_items','digital_entitlements','user_addresses','physical_orders','payment_events','order_effects');"

echo "=== create tiny valid PDF and try publish as admin ==="
# minimal PDF
python3 - <<'PY'
pdf = b"""%PDF-1.1
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>endobj
4 0 obj<< /Length 68 >>stream
BT /F1 12 Tf 72 720 Td (Capitulo 1 - Prueba de publicacion Aeternum) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer<< /Size 5 /Root 1 0 R >>
startxref
324
%%EOF
"""
open("/tmp/test_publish.pdf","wb").write(pdf)
print("pdf_bytes", len(pdf))
PY

curl -s -c /tmp/pub.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

curl -s -b /tmp/pub.txt -o /tmp/pub_resp.txt -w "publish=%{http_code}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=Libro Prueba Publicar $(date +%s)" \
  -F "author_name=Autor Prueba" \
  -F "category=Ficción" \
  -F "price=9.99" \
  -F "pdf_file=@/tmp/test_publish.pdf;type=application/pdf"
head -c 800 /tmp/pub_resp.txt
echo

echo "=== last books ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, price, published, page_count, created_at FROM books ORDER BY id DESC LIMIT 5;"

echo "=== app errors ==="
cd /root/plataforma/docker && docker compose logs app --tail 40 2>&1 | grep -iE 'publish|create_book|rechazado|duplicate|422|409|Error al' | tail -20
echo DONE
