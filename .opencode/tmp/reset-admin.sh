#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== reset admin password to admin123 ==="
docker exec docker-app-1 python - <<'PY'
import bcrypt, psycopg2, os
pw = b"admin123"
h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode()
url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    "UPDATE users SET hashed_password=%s, email_verified=TRUE, is_banned=FALSE WHERE email=%s RETURNING id, email, role",
    (h, "admin@plataforma.com"),
)
print("updated", cur.fetchone())
# verify
cur.execute("SELECT hashed_password FROM users WHERE email=%s", ("admin@plataforma.com",))
row = cur.fetchone()
print("verify_admin123", bcrypt.checkpw(pw, row[0].encode()))
conn.commit()
cur.close()
conn.close()
PY

echo "=== login admin ==="
curl -s -o /tmp/la.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
cat /tmp/la.txt | head -c 300
echo

echo "=== login cookie flags via -c ==="
curl -s -c /tmp/cj.txt -o /dev/null -w "login_cookies=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
grep -E 'access_token|refresh_token' /tmp/cj.txt || true

echo "=== /me with cookie ==="
curl -s -b /tmp/cj.txt -o /tmp/me.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me
head -c 300 /tmp/me.txt
echo

echo "=== google auth url ok? ==="
curl -s https://aeternumlibrary.com/api/auth/google | python3 -c 'import sys,json; d=json.load(sys.stdin); u=d.get("auth_url",""); print("has_client", "client_id=" in u); print("redirect_ok", "aeternumlibrary.com/auth/google/callback" in u)'

echo DONE
