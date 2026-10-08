#!/bin/bash
set -e
cd /root/plataforma
# Frontend lives in repo; rebuild app image which includes frontend build
cd frontend
npm run build
cd /root/plataforma/docker
docker compose build app
docker compose up -d --force-recreate app
sleep 5
docker compose ps app
echo "=== HOME STATUS ==="
curl -s -o /dev/null -w "%{http_code}" -H "Host: aeternumlibrary.com" https://127.0.0.1/
echo
echo "=== API BOOKS ==="
curl -s -H "Host: aeternumlibrary.com" https://127.0.0.1/api/books | head -c 200
echo
echo "DEPLOY_UI_DONE"
