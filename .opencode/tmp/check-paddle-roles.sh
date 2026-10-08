#!/bin/bash
echo "=== frontend_dist in container ==="
docker exec docker-app-1 sh -c 'ls -la /app/frontend_dist 2>&1 | head -20; echo ---; ls -la /app/frontend_dist/assets 2>&1 | head -15; echo ---; find /app -name "index-*.js" 2>/dev/null | head; echo ---; grep -o "live_[A-Za-z0-9_]*" /app/frontend_dist/assets/*.js 2>/dev/null | head -5; grep -o "sandbox_[A-Za-z0-9_]*" /app/frontend_dist/assets/*.js 2>/dev/null | head -5; grep -o "paddle" /app/frontend_dist/assets/*.js 2>/dev/null | head -3'

echo "=== public assets ==="
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
echo "js=$JS"
curl -s --max-time 20 "https://aeternumlibrary.com/assets/$JS" | grep -oE "live_[A-Za-z0-9]+|sandbox_[A-Za-z0-9]+|VITE_PADDLE|paddle_client" | head -10

echo "=== role labels backend valid ==="
grep -n 'valid_roles' /root/plataforma/backend/server.py
echo DONE
