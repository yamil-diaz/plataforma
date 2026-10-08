#!/bin/bash
cd /root/plataforma/docker
echo "=== compose ps ==="
docker compose ps
echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS forum_categories FROM forum_categories;'
echo "=== volume via docker ==="
docker run --rm -v docker_aeternum-data:/data alpine sh -c 'du -sh /data; ls -la /data; echo ---books---; ls /data/books 2>&1 | head -10; echo count_books=$(ls /data/books 2>/dev/null | wc -l); echo count_covers=$(ls /data/covers 2>/dev/null | wc -l)'
echo "=== host path if any ==="
docker volume inspect docker_aeternum-data --format '{{.Mountpoint}}'
ls -la "$(docker volume inspect docker_aeternum-data --format '{{.Mountpoint}}')" 2>&1 | head -20
echo "=== backup still there? ==="
ls -lh /root/aeternum-disk.tar.gz 2>&1
du -sh /root/render-backup-aeternum 2>&1
ls /root/render-backup-aeternum/aeternum/books 2>&1 | head -5
echo "=== schema books ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c '\d books' 2>&1 | head -50
echo DONE
