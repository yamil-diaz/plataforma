#!/bin/bash
echo "=== file exists in volume? ==="
ls -la "/var/lib/docker/volumes/docker_aeternum-data/_data/books/c7ea9040-5391-419b-9626-98fac64150d1_rayuelas mentales.pdf" 2>&1
echo "=== db row 176 ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT id, title, published, pdf_path, uploader_id FROM books WHERE id=176;"
echo "=== try download from localhost via nginx host header ==="
curl -s -o /dev/null -w "local_8000=%{http_code}\n" --max-time 10 "http://127.0.0.1:8000/api/books/176/download"
curl -s --max-time 10 "http://127.0.0.1:8000/api/books/176/download" | head -c 200
echo
echo "=== app logs ==="
cd /root/plataforma/docker && docker compose logs app --tail 30
echo DONE
