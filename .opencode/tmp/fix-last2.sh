#!/bin/bash
set -euo pipefail
echo "=== remaining unknown ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, author_name FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido');"

echo "=== fix via SQL directly ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "UPDATE books SET title='Indigno de ser humano', author_name='Makoto Shinkai' WHERE id=133;"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "UPDATE books SET title='Voz Horizona', author_name='Luis Hernandez' WHERE id=151;"

echo "=== verify ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT count(*) AS unknown FROM books WHERE published=1 AND (author_name IS NULL OR TRIM(author_name)='' OR LOWER(TRIM(author_name))='desconocido');"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id,title,author_name FROM books WHERE id IN (133,151,158,161,164,171);"
echo DONE
