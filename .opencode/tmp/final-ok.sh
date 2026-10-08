#!/bin/bash
curl -s -c /tmp/cja.txt -o /tmp/la.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
echo -n "body="; head -c 250 /tmp/la.txt; echo
curl -s -b /tmp/cja.txt -o /tmp/mea.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me
echo -n "me_body="; head -c 250 /tmp/mea.txt; echo
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
curl -s https://aeternumlibrary.com/api/auth/google | python3 -c 'import sys,json; d=json.load(sys.stdin); print("google_oauth", "auth_url" in d)'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
