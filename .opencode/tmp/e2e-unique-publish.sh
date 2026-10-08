#!/bin/bash
set -euo pipefail

echo "=== create unique PDF ==="
python3 - <<'PY'
import time
ts = int(time.time())
# build a multi-page PDF with unique extractable text
pages_text = []
for i in range(1, 4):
    pages_text.append(f"Capitulo {i} - Obra unica {ts}. Texto de prueba para lectura paginada Aeternum {ts}.")

# minimal multi-page PDF
objs = []
objs.append("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
kids = []
obj_id = 3
content_objs = []
page_objs = []
for text in pages_text:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    content_objs.append((obj_id, stream))
    page_objs.append((obj_id+1, obj_id))
    kids.append(f"{obj_id+1} 0 R")
    obj_id += 2

objs.append(f"2 0 obj<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>endobj\n")
# pages + contents
body_parts = []
xref_positions = {}
# rebuild properly
parts = []
parts.append("%PDF-1.4\n")
offsets = {}
def add_obj(num, body):
    offsets[num] = len("".join(parts)) if False else None

# simpler: write sequentially
out = bytearray()
out.extend(b"%PDF-1.4\n")
off = {}
def wobj(n, data):
    global out
    off[n] = len(out)
    out.extend(f"{n} 0 obj\n".encode())
    out.extend(data)
    out.extend(b"\nendobj\n")

wobj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
# pages tree
page_ids = []
content_ids = []
nid = 3
for text in pages_text:
    content_ids.append(nid)
    page_ids.append(nid+1)
    nid += 2
kids_s = " ".join(f"{p} 0 R" for p in page_ids)
wobj(2, f"<< /Type /Pages /Kids [{kids_s}] /Count {len(page_ids)} >>".encode())
for text, cid, pid in zip(pages_text, content_ids, page_ids):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    wobj(cid, f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode())
    wobj(pid, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {cid} 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>".encode())

xref_pos = len(out)
max_id = max(off)
out.extend(f"xref\n0 {max_id+1}\n".encode())
out.extend(b"0000000000 65535 f \n")
for i in range(1, max_id+1):
    if i in off:
        out.extend(f"{off[i]:010d} 00000 n \n".encode())
    else:
        out.extend(b"0000000000 65535 f \n")
out.extend(f"trailer<< /Size {max_id+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
path = "/tmp/unique_book.pdf"
open(path, "wb").write(bytes(out))
print("wrote", path, "bytes", len(out), "ts", ts)
PY

curl -s -c /tmp/bk2.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'

TITLE="Obra Unica Rental $(date +%s)"
curl -s -b /tmp/bk2.txt -o /tmp/e2e2.txt -w "publish=%{http_code}\n" -X POST https://aeternumlibrary.com/api/books \
  -H "Origin: https://aeternumlibrary.com" \
  -F "title=$TITLE" \
  -F "author_name=Autor Unico" \
  -F "category=Ficción" \
  -F "price=20.00" \
  -F "rental_price=6.50" \
  -F "pdf_file=@/tmp/unique_book.pdf;type=application/pdf"
head -c 700 /tmp/e2e2.txt
echo
BOOK_ID=$(python3 -c 'import json; print(json.load(open("/tmp/e2e2.txt")).get("id",""))' 2>/dev/null || true)
echo "book_id=$BOOK_ID"

if [ -n "$BOOK_ID" ]; then
  echo "=== book row ==="
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, price, published, page_count FROM books WHERE id=$BOOK_ID;"
  echo "=== book_prices ==="
  docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT currency, price, rental_price, is_active FROM book_prices WHERE book_id=$BOOK_ID ORDER BY currency;"
  echo "=== reader page 1 ==="
  curl -s -b /tmp/bk2.txt -o /tmp/pg2.txt -w "reader=%{http_code}\n" "https://aeternumlibrary.com/api/books/$BOOK_ID/pages/1"
  python3 -c 'import json; d=json.load(open("/tmp/pg2.txt")); print("total", d.get("total_pages"), "sample", (d.get("content") or "")[:80])'
  echo "=== prices endpoint ==="
  curl -s -b /tmp/bk2.txt -o /tmp/pr2.txt -w "prices=%{http_code}\n" "https://aeternumlibrary.com/api/books/$BOOK_ID/prices"
  cat /tmp/pr2.txt | head -c 500
  echo
  echo "=== checkout rental USD ==="
  curl -s -b /tmp/bk2.txt -o /tmp/co_r.txt -w "rental=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
    -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
    -d "{\"book_id\":$BOOK_ID,\"item_type\":\"digital_rental\",\"currency\":\"USD\",\"rental_days\":7}"
  head -c 350 /tmp/co_r.txt
  echo
  echo "=== checkout purchase PEN ==="
  curl -s -b /tmp/bk2.txt -o /tmp/co_p.txt -w "purchase=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
    -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
    -d "{\"book_id\":$BOOK_ID,\"item_type\":\"digital_purchase\",\"currency\":\"PEN\"}"
  head -c 350 /tmp/co_p.txt
  echo
fi

echo "=== backfill book_prices for existing paid books ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
SELECT id, 'PEN', price, CASE WHEN price > 0 THEN ROUND(price * 0.3, 2) ELSE NULL END, TRUE, NOW()::text, NOW()::text
FROM books
WHERE price > 0 AND published = 1
ON CONFLICT (book_id, currency) DO UPDATE
SET price = EXCLUDED.price,
    rental_price = COALESCE(EXCLUDED.rental_price, book_prices.rental_price),
    is_active = TRUE,
    updated_at = EXCLUDED.updated_at;

INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
SELECT id, 'USD', ROUND(price * 0.27, 2), CASE WHEN price > 0 THEN ROUND(price * 0.27 * 0.3, 2) ELSE NULL END, TRUE, NOW()::text, NOW()::text
FROM books
WHERE price > 0 AND published = 1
ON CONFLICT (book_id, currency) DO UPDATE
SET price = EXCLUDED.price,
    rental_price = COALESCE(EXCLUDED.rental_price, book_prices.rental_price),
    is_active = TRUE,
    updated_at = EXCLUDED.updated_at;
SQL

echo "=== catalog rental sample ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("len", len(d))
paid=[b for b in d if (b.get("price") or 0)>0]
print("paid", len(paid))
print("with_rental", sum(1 for b in d if b.get("rental_price")))
if paid:
    b=paid[0]
    print("sample", b.get("title"), "price", b.get("price"), "rental", b.get("rental_price"))
'
echo DONE
