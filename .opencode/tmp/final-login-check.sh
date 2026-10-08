#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== reset admin password admin123 ==="
docker exec docker-app-1 python - <<'PY'
import bcrypt, os, psycopg2
pw=b"admin123"
h=bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode()
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
cur.execute("UPDATE users SET hashed_password=%s, email_verified=TRUE, is_banned=FALSE WHERE email=%s", (h,"admin@plataforma.com"))
print("admin_reset", cur.rowcount)
# also ensure rodrigo can login with email even without google_id
cur.execute("UPDATE users SET email_verified=TRUE WHERE email=%s", ("rodrigozegara2006@gmail.com",))
conn.commit()
cur.close(); conn.close()
print("OK")
PY

echo "=== login admin ==="
curl -s -c /tmp/cja.txt -o /tmp/la.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
cat /tmp/la.txt | head -c 250
echo
curl -s -b /tmp/cja.txt -o /tmp/mea.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me

echo "=== try login a restored user (wrong pass should be 400 not 500) ==="
curl -s -o /tmp/lu.txt -w "user_wrong=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"paredespatrick770@gmail.com","password":"wrongpass"}'
cat /tmp/lu.txt | head -c 200
echo

echo "=== google still configured ==="
curl -s https://aeternumlibrary.com/api/auth/google | python3 -c 'import sys,json; d=json.load(sys.stdin); print("oauth", "auth_url" in d)'

echo "=== books ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'

echo "=== final counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM books;'

echo DONE
