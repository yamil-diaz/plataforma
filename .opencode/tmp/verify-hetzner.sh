#!/bin/bash
cd /root/plataforma/docker
echo "=== compose ps ==="
docker compose ps
echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
echo "=== app health via nginx host ==="
curl -s --max-time 10 -o /dev/null -w 'https_status=%{http_code}\n' https://aeternumlibrary.com
curl -s --max-time 10 -o /dev/null -w 'api_books_status=%{http_code}\n' https://aeternumlibrary.com/api/books
echo "=== port 8000 public? ==="
ss -lntp | grep ':8000' || true
echo "=== cert expiry ==="
echo | openssl s_client -connect aeternumlibrary.com:443 -servername aeternumlibrary.com 2>/dev/null | openssl x509 -noout -dates
rm -f /root/verify-hetzner.sh
echo DONE
