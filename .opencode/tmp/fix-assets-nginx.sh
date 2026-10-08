#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
grep -n -A6 'location /assets' nginx.conf
docker compose up -d --force-recreate nginx
sleep 2

HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
CSS=$(echo "$HTML" | sed -n 's/.*href="\/assets\/\([^"]*\.css\)".*/\1/p' | head -1)
echo "js=$JS css=$CSS"
curl -s -o /dev/null -w "js=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$JS"
curl -s -o /dev/null -w "css=%{http_code} size=%{size_download}\n" --max-time 20 "https://aeternumlibrary.com/assets/$CSS"
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
docker compose logs nginx --tail 10 2>&1 | grep -iE '404|assets' | tail -5 || echo no_asset_404
echo DONE
