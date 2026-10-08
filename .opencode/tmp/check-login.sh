#!/bin/bash
echo "=== CORS headers login ==="
curl -s -D - -o /tmp/login_body.txt -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","admin123_wrong":true}' | head -40
echo "--- body ---"
cat /tmp/login_body.txt | head -c 400
echo
echo "=== correct login attempt (will hash check) ==="
curl -s -D - -o /tmp/login2.txt -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}' | head -40
echo "--- body ---"
cat /tmp/login2.txt | head -c 500
echo
echo "=== users in db ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT id, email, role, google_id IS NOT NULL AS has_google, email_verified, is_banned FROM users ORDER BY id;"
echo "=== app logs login ==="
cd /root/plataforma/docker && docker compose logs app --tail 40
echo DONE
