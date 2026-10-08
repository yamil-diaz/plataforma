#!/bin/bash
set -euo pipefail
echo "=== book 1 prices ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, price, published FROM books WHERE id=1;"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT * FROM book_prices WHERE book_id=1;"

echo "=== force upsert rayuelas ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
VALUES (1, 'PEN', 5.00, 1.50, TRUE, NOW()::text, NOW()::text)
ON CONFLICT (book_id, currency) DO UPDATE
SET price=5.00, rental_price=1.50, is_active=TRUE, updated_at=NOW()::text;
"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
VALUES (1, 'USD', 1.35, 0.41, TRUE, NOW()::text, NOW()::text)
ON CONFLICT (book_id, currency) DO UPDATE
SET price=1.35, rental_price=0.41, is_active=TRUE, updated_at=NOW()::text;
"

echo "=== all paid books prices ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
SELECT b.id, left(b.title,30) AS title, b.price, bp.currency, bp.price AS bp_price, bp.rental_price
FROM books b
LEFT JOIN book_prices bp ON bp.book_id=b.id AND bp.is_active
WHERE b.price>0 AND b.published=1
ORDER BY b.id, bp.currency;
"

echo "=== API catalog paid ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
for b in d:
    if (b.get("price") or 0)>0:
        print(b["id"], b["title"][:35], "price", b.get("price"), "rental", b.get("rental_price"))
'
echo DONE
