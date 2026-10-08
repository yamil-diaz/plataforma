#!/bin/bash
cd /root/plataforma/docker
echo "=== cover_image_url exists? ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='books' AND column_name LIKE '%cover%';"
echo "=== all book columns ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='books' ORDER BY ordinal_position;"
echo "=== users table ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM users;"
docker exec docker-db-1 psql -U aeternum -d aeternum -c '\d users' 2>&1 | head -30
echo "=== how app resolves storage ==="
docker exec docker-app-1 printenv | grep -iE 'STORAGE|DATA|RENDER|ENV' || true
echo "=== sample pdf path convention from audit ==="
echo "/var/data/aeternum/books/UUID_name.pdf"
ls /var/lib/docker/volumes/docker_aeternum-data/_data/books | head -3
echo DONE
