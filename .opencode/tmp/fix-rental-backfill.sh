#!/bin/bash
set -euo pipefail
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 <<'SQL'
-- Asegurar rental_price en book_prices para libros pagados
INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
SELECT b.id, 'PEN', b.price, ROUND(b.price * 0.3, 2), TRUE, NOW()::text, NOW()::text
FROM books b
WHERE b.price > 0 AND b.published = 1
ON CONFLICT (book_id, currency) DO UPDATE
SET price = EXCLUDED.price,
    rental_price = CASE
      WHEN book_prices.rental_price IS NULL OR book_prices.rental_price = 0
        THEN EXCLUDED.rental_price
      ELSE book_prices.rental_price
    END,
    is_active = TRUE,
    updated_at = EXCLUDED.updated_at;

INSERT INTO book_prices (book_id, currency, price, rental_price, is_active, created_at, updated_at)
SELECT b.id, 'USD', ROUND(b.price * 0.27, 2), ROUND(b.price * 0.27 * 0.3, 2), TRUE, NOW()::text, NOW()::text
FROM books b
WHERE b.price > 0 AND b.published = 1
ON CONFLICT (book_id, currency) DO UPDATE
SET price = EXCLUDED.price,
    rental_price = CASE
      WHEN book_prices.rental_price IS NULL OR book_prices.rental_price = 0
        THEN EXCLUDED.rental_price
      ELSE book_prices.rental_price
    END,
    is_active = TRUE,
    updated_at = EXCLUDED.updated_at;

SELECT b.id, b.title, b.price, bp.currency, bp.price AS bp_price, bp.rental_price
FROM books b
JOIN book_prices bp ON bp.book_id = b.id AND bp.is_active
WHERE b.price > 0 AND b.published = 1
ORDER BY b.id, bp.currency
LIMIT 20;
SQL

echo "=== catalog check ==="
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c '
import sys,json
d=json.load(sys.stdin)
paid=[b for b in d if (b.get("price") or 0)>0]
print("len",len(d),"paid",len(paid))
for b in paid[:5]:
    print(b["id"], b["title"][:40], "price", b.get("price"), "rental", b.get("rental_price"))
'
echo DONE
