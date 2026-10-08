#!/bin/bash
echo "=== assets in image ==="
docker exec docker-app-1 ls -la /app/frontend_dist/assets 2>&1 | head -20
echo "=== index.html refs ==="
docker exec docker-app-1 sh -c 'grep -E "assets/|src=|href=" /app/frontend_dist/index.html'
echo "=== curl JS/CSS from public ==="
curl -s -o /dev/null -w "js=%{http_code} size=%{size_download}\n" --max-time 15 https://aeternumlibrary.com/assets/index-WqEqE7KO.js
curl -s -o /dev/null -w "css=%{http_code} size=%{size_download}\n" --max-time 15 https://aeternumlibrary.com/assets/index-DazvAAAB.css
echo "=== google auth endpoint ==="
curl -s --max-time 15 https://aeternumlibrary.com/api/auth/google | head -c 400
echo
echo "=== app env values length (no print values) ==="
docker exec docker-app-1 sh -c 'for k in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REDIRECT_URI RESEND_API_KEY GEMINI_API_KEY AI_PROVIDER PADDLE_CLIENT_TOKEN CULQI_SECRET_KEY CORS_ORIGINS RENDER ENV; do v=$(printenv $k); if [ -z "$v" ]; then echo "$k=EMPTY"; else echo "$k=SET(len=${#v})"; fi; done'
echo "=== local compose port ==="
grep -n '8000' /root/plataforma/docker/docker-compose.yml
echo DONE
