#!/bin/bash
echo "=== progress ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS book_pages FROM book_pages;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS books_with_pages FROM books b WHERE EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id);"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS books_no_pages FROM books b WHERE NOT EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id);"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) AS need_cover FROM books WHERE cover_image_url IS NULL OR cover_image_url='';"
echo "=== script still running? ==="
for d in /proc/[0-9]*; do
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null || true)
  case "$cmd" in *paginate_covers*) echo "RUNNING $cmd";; esac
done
echo DONE
