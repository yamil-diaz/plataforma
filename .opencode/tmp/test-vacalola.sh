#!/bin/bash
echo "=== book vacalola in DB? ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, author_name, price, published, page_count, created_at FROM books WHERE title ILIKE '%vacalola%' OR title ILIKE '%bailarina%' OR author_name ILIKE '%Solis%';"

echo "=== inspect PDF with script ==="
docker exec docker-app-1 python - <<'PY'
from pypdf import PdfReader
path="/tmp/vacalola.pdf"
try:
    r=PdfReader(path)
    print("pages", len(r.pages))
    print("encrypted", r.is_encrypted)
    if len(r.pages):
        t=r.pages[0].extract_text() or ""
        print("p1_len", len(t))
        print("p1", repr(t[:150]))
except Exception as e:
    print("pypdf_error", type(e).__name__, e)
# magic + size
import os
print("size", os.path.getsize(path))
with open(path,"rb") as f:
    print("header", f.read(16))
PY

echo "=== try API upload with this PDF ==="
curl -s -c /tmp/vl.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
# copy into container for curl from host? upload from host via scp already at /tmp/vacalola.pdf on HOST not container
# host has /tmp/vacalola.pdf from earlier scp
ls -lh /tmp/vacalola.pdf
curl -s -b /tmp/vl.txt -o /tmp/vl_up.txt -w "upload=%{http_code} time=%{time_total}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=La vacalola bailarina API $(date +%s)" \
  -F "author_name=Jose R. Solis Pinedo" \
  -F "category=Ficción" \
  -F "price=10" \
  -F "rental_price=0" \
  -F "pdf_file=@/tmp/vacalola.pdf;type=application/pdf"
head -c 800 /tmp/vl_up.txt
echo

echo "=== app logs after upload ==="
cd /root/plataforma/docker && docker compose logs app --tail 30 2>&1 | grep -iE 'CREATE_BOOK|POST /api/books|rechazado|Error|422|409|500|vacalola|sin páginas' | tail -20
echo DONE
