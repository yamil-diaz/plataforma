#!/bin/bash
echo "=== login admin ==="
curl -s -c /tmp/cj.txt -o /tmp/la.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
cat /tmp/la.txt | head -c 300
echo
echo "=== cookies ==="
grep -E 'access_token|refresh_token' /tmp/cj.txt || echo NO_COOKIES
echo "=== /me ==="
curl -s -b /tmp/cj.txt -o /tmp/me.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me
head -c 300 /tmp/me.txt
echo
echo "=== google auth ==="
curl -s https://aeternumlibrary.com/api/auth/google | python3 -c 'import sys,json; d=json.load(sys.stdin); u=d.get("auth_url",""); print("oauth_ok", "client_id=" in u and "aeternumlibrary.com/auth/google/callback" in u)'
echo DONE
