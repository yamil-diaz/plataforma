#!/bin/bash
echo "=== is restore still running? ==="
docker exec docker-app-1 sh -c 'ps aux | grep -E "restore_all|python" | grep -v grep' || true
echo "=== db counts now ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='books' AND column_name IN ('cover_image_url','uploader_id');"
echo "=== app status ==="
cd /root/plataforma/docker && docker compose ps
docker compose logs app --tail 15
echo DONE
