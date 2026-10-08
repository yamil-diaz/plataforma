#!/bin/bash
set -e
cd /root/plataforma/docker
docker compose build app 2>&1 | tail -20
docker compose up -d --force-recreate app 2>&1 | tail -10
sleep 6
docker compose ps app
echo "=== HOME ==="
curl -s -o /dev/null -w "%{http_code}" https://aeternumlibrary.com/
echo
echo "=== API BOOKS ==="
curl -s https://aeternumlibrary.com/api/books | head -c 160
echo
echo "=== CSS TOKENS IN BUNDLE ==="
ASSET=$(curl -s https://aeternumlibrary.com/ | grep -oE '/assets/index-[^"]+\.js' | head -1)
echo "asset=$ASSET"
curl -s "https://aeternumlibrary.com${ASSET}" | grep -oE 'ae-pop|D4AF37|cubic-bezier\(0\.23' | sort -u | head -10
echo
echo "DESIGN_DEPLOY_DONE"
