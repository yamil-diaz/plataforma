#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== rebuild app (frontend VITE + backend) ==="
docker compose build --no-cache app
docker compose up -d --force-recreate app nginx
sleep 6
docker compose ps

echo "=== app logs ==="
docker compose logs app --tail 30

echo "=== env status in container ==="
docker exec docker-app-1 sh -c 'for k in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REDIRECT_URI RESEND_API_KEY GEMINI_API_KEY AI_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_ENVIRONMENT CULQI_SECRET_KEY CORS_ORIGINS RENDER ENV STORAGE_DIR; do v=$(printenv $k 2>/dev/null || true); if [ -z "$v" ]; then echo "$k=EMPTY"; else echo "$k=SET(len=${#v})"; fi; done'

echo "=== verify public ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
# detectar hash de assets desde index.html servido
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
CSS=$(echo "$HTML" | sed -n 's/.*href="\/assets\/\([^"]*\.css\)".*/\1/p' | head -1)
echo "html_js=$JS"
echo "html_css=$CSS"
if [ -n "$JS" ]; then
  curl -s -o /dev/null -w "js=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$JS"
fi
if [ -n "$CSS" ]; then
  curl -s -o /dev/null -w "css=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$CSS"
fi

echo "=== google auth ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/auth/google | head -c 300
echo
echo "=== books api ==="
curl -s -o /dev/null -w "books=%{http_code}\n" --max-time 15 https://aeternumlibrary.com/api/books
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books_len", len(d) if isinstance(d,list) else d)'

echo "=== health ==="
curl -s --max-time 10 https://aeternumlibrary.com/api/health | head -c 200
echo
echo DONE_PHASE2
