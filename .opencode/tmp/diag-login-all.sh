#!/bin/bash
echo "=== compose / app ==="
cd /root/plataforma/docker && docker compose ps
echo "=== env SECRET stable? ==="
docker exec docker-app-1 printenv SECRET_KEY | wc -c
docker exec docker-app-1 printenv ENV RENDER
echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM book_pages;'
echo "=== login attempts table ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM login_attempts;"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT ip_address, attempts, lockout_until FROM login_attempts ORDER BY attempts DESC LIMIT 10;"
echo "=== login admin ==="
curl -s -c /tmp/s1.txt -o /tmp/s1b.txt -w "login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
head -c 250 /tmp/s1b.txt; echo
echo "=== cookies ==="
cat /tmp/s1.txt | grep -E 'token|HttpOnly' || echo no_cookies
echo "=== /me twice ==="
curl -s -b /tmp/s1.txt -o /tmp/me1.txt -w "me1=%{http_code}\n" https://aeternumlibrary.com/api/me
curl -s -b /tmp/s1.txt -o /tmp/me2.txt -w "me2=%{http_code}\n" https://aeternumlibrary.com/api/me
head -c 200 /tmp/me1.txt; echo
echo "=== books api x3 ==="
for i in 1 2 3; do curl -s -o /tmp/b$i.txt -w "books$i=%{http_code} size=%{size_download}\n" --max-time 20 https://aeternumlibrary.com/api/books; done
python3 -c 'import json; d=json.load(open("/tmp/b1.txt")); print("len", len(d) if isinstance(d,list) else d)'
echo "=== refresh-token ==="
curl -s -b /tmp/s1.txt -c /tmp/s1.txt -o /tmp/rt.txt -w "refresh=%{http_code}\n" -X POST https://aeternumlibrary.com/api/refresh-token -H "Origin: https://aeternumlibrary.com"
head -c 200 /tmp/rt.txt; echo
echo "=== app logs errors ==="
docker compose logs app --tail 60 2>&1 | grep -iE 'error|exception|pool|traceback|401|400|login' | tail -30
echo "=== postgres max_connections ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SHOW max_connections;"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='aeternum';"
echo "=== slow endpoints timing ==="
curl -s -o /dev/null -w "https=%{http_code} time=%{time_total}\n" https://aeternumlibrary.com
curl -s -o /dev/null -w "books=%{http_code} time=%{time_total}\n" --max-time 30 https://aeternumlibrary.com/api/books
curl -s -o /dev/null -w "home_html=%{http_code} time=%{time_total}\n" --max-time 20 https://aeternumlibrary.com/
echo DONE
