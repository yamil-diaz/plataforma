#!/bin/bash
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
echo "=== index.html ==="
echo "$HTML" | head -30
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
CSS=$(echo "$HTML" | sed -n 's/.*href="\/assets\/\([^"]*\.css\)".*/\1/p' | head -1)
echo "js=$JS css=$CSS"
curl -s -o /dev/null -w "js=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$JS"
curl -s -o /dev/null -w "css=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$CSS"
curl -s -o /dev/null -w "favicon=%{http_code}\n" --max-time 10 https://aeternumlibrary.com/favicon.svg
echo "=== assets in container ==="
docker exec docker-app-1 sh -c 'ls -la /app/frontend_dist/assets/; grep -o "src=\"[^\"]*\"" /app/frontend_dist/index.html; grep -o "href=\"[^\"]*\"" /app/frontend_dist/index.html'
echo "=== nginx logs recent ==="
cd /root/plataforma/docker && docker compose logs nginx --tail 30 2>&1 | grep -iE '404|500|error|assets' | tail -15
echo "=== app logs ==="
docker compose logs app --tail 20 2>&1 | grep -iE 'error|exception|startup' | tail -10
echo DONE
