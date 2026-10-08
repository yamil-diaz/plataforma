#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
docker compose build app
docker compose up -d --force-recreate app
sleep 5

curl -s -c /tmp/dl.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

echo "=== delete book 172 (had checkout attempts) ==="
curl -s -b /tmp/dl.txt -o /tmp/dl1.txt -w "delete172=%{http_code}\n" -X DELETE "https://aeternumlibrary.com/api/books/172" \
  -H "Origin: https://aeternumlibrary.com"
head -c 400 /tmp/dl1.txt
echo

echo "=== create + delete fresh book ==="
python3 - <<'PY'
out = bytearray(b"%PDF-1.4\n")
off={}
def wobj(n, data):
    global out
    off[n]=len(out)
    out.extend(f"{n} 0 obj\n".encode()); out.extend(data); out.extend(b"\nendobj\n")
stream="BT /F1 12 Tf 72 720 Td (Libro para borrar prueba delete) Tj ET"
wobj(1,b"<< /Type /Catalog /Pages 2 0 R >>")
wobj(2,b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
wobj(3, f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode())
wobj(4,b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 3 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>")
xref=len(out)
out.extend(b"xref\n0 5\n0000000000 65535 f \n")
for i in range(1,5):
    out.extend(f"{off[i]:010d} 00000 n \n".encode())
out.extend(f"trailer<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
open("/tmp/delete_me.pdf","wb").write(bytes(out))
print("ok")
PY

curl -s -b /tmp/dl.txt -o /tmp/dlcreate.txt -w "create=%{http_code}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=Borrable Delete $(date +%s)" \
  -F "author_name=Test" \
  -F "category=General" \
  -F "price=0" \
  -F "rental_price=0" \
  -F "pdf_file=@/tmp/delete_me.pdf;type=application/pdf"
head -c 300 /tmp/dlcreate.txt
echo
NEW_ID=$(python3 -c 'import json; print(json.load(open("/tmp/dlcreate.txt")).get("id",""))' 2>/dev/null || true)
echo "new_id=$NEW_ID"
if [ -n "$NEW_ID" ]; then
  curl -s -b /tmp/dl.txt -o /tmp/dl2.txt -w "delete_new=%{http_code}\n" -X DELETE "https://aeternumlibrary.com/api/books/$NEW_ID" \
    -H "Origin: https://aeternumlibrary.com"
  head -c 300 /tmp/dl2.txt
  echo
fi

echo "=== catalog ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d)); print("has_172", any(b.get("id")==172 or b.get("_id")=="172" for b in d))'
echo DONE
