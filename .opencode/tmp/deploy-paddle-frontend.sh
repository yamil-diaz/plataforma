#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

# Force frontend rebuild with VITE args from .env
export VITE_PADDLE_CLIENT_TOKEN="${VITE_PADDLE_CLIENT_TOKEN:-}"
export VITE_PADDLE_ENVIRONMENT="${VITE_PADDLE_ENVIRONMENT:-production}"
# load from docker/.env if empty
if [ -z "$VITE_PADDLE_CLIENT_TOKEN" ] && [ -f .env ]; then
  VITE_PADDLE_CLIENT_TOKEN=$(grep -E '^VITE_PADDLE_CLIENT_TOKEN=' .env | cut -d= -f2-)
  VITE_PADDLE_ENVIRONMENT=$(grep -E '^VITE_PADDLE_ENVIRONMENT=' .env | cut -d= -f2-)
fi
echo "VITE_PADDLE_CLIENT_TOKEN len=${#VITE_PADDLE_CLIENT_TOKEN} env=$VITE_PADDLE_ENVIRONMENT"

docker compose build --no-cache app
docker compose up -d --force-recreate app
sleep 5
docker compose ps

echo "=== config/public ==="
curl -s https://aeternumlibrary.com/api/config/public
echo
echo "=== bundle has token? ==="
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
echo "js=$JS"
curl -s --max-time 20 "https://aeternumlibrary.com/assets/$JS" > /tmp/b2.js
grep -oE "live_[A-Za-z0-9]+|config/public|ensurePaddleReady" /tmp/b2.js | sort -u | head

echo "=== checkout purchase ==="
curl -s -c /tmp/pf.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/pf.txt -o /tmp/pf1.txt -w "purchase=%{http_code}\n" -X POST https://aeternumlibrary.com/api/checkout \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"book_id":1,"item_type":"digital_purchase","currency":"USD"}'
python3 -c 'import json; d=json.load(open("/tmp/pf1.txt")); print("txn",(d.get("transaction_id") or "")[:40],"order",d.get("order_id"))'

echo "=== paddle env in container ==="
docker exec docker-app-1 sh -c 'printenv PADDLE_CLIENT_TOKEN | wc -c; printenv PADDLE_ENVIRONMENT'

echo DONE
