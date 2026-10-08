#!/bin/bash
echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS book_pages FROM book_pages;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE content IS NOT NULL AND length(content) > 100;"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE pdf_path IS NOT NULL;"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE cover_image_url IS NOT NULL AND cover_image_url <> '';"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM books WHERE cover_image_url IS NULL OR cover_image_url = '';"
echo "=== sample without pages ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT b.id, b.title, length(coalesce(b.content,'')) AS content_len, b.page_count, b.pdf_path IS NOT NULL AS has_pdf, (SELECT count(*) FROM book_pages bp WHERE bp.book_id=b.id) AS pages FROM books b ORDER BY b.id LIMIT 15;"
echo "=== reader endpoint code hints ==="
grep -nE "book_pages|page_count|sin paginación|lector paginado|/pages/" /root/plataforma/backend/server.py | head -40
echo DONE
