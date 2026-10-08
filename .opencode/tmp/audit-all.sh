#!/bin/bash
echo "=== ENV keys status (no values) ==="
docker exec docker-app-1 sh -c 'for k in SECRET_KEY DATABASE_URL CORS_ORIGINS ENV RENDER STORAGE_DIR GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REDIRECT_URI RESEND_API_KEY GEMINI_API_KEY AI_PROVIDER PADDLE_API_KEY PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_ENVIRONMENT CULQI_PUBLIC_KEY CULQI_SECRET_KEY CULQI_WEBHOOK_SECRET CULQI_ENVIRONMENT FRONTEND_URL VITE_PADDLE_CLIENT_TOKEN VITE_PADDLE_ENVIRONMENT FLOW_API_KEY FLOW_API_SECRET FLOW_ENVIRONMENT; do v=$(printenv $k 2>/dev/null || true); if [ -z "$v" ]; then echo "$k=EMPTY"; else echo "$k=SET(len=${#v})"; fi; done'

echo "=== payment provider env reads ==="
grep -nE 'os.getenv|PADDLE|CULQI|FLOW' /root/plataforma/backend/payment_providers.py | head -50

echo "=== checkout endpoints ==="
grep -nE 'checkout|paddle|culqi|flow|webhook' /root/plataforma/backend/server.py | head -40

echo "=== roles in users ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT role, count(*) FROM users GROUP BY role;"

echo "=== register sets role? ==="
grep -nE "role.*user|role.*autor|INSERT INTO users|register" /root/plataforma/backend/server.py | head -30

echo "=== admin users list role field ==="
grep -nE "role|autor|lector|admin/users|GET.*users" /root/plataforma/backend/server.py | grep -iE 'users|role' | head -40

echo "=== storage speed test ==="
docker run --rm -v docker_aeternum-data:/data alpine sh -c 'dd if=/dev/zero of=/data/temp/speedtest.bin bs=1M count=50 2>&1; rm -f /data/temp/speedtest.bin; ls /data/books | wc -l'

echo "=== disk io ==="
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT 2>/dev/null || df -h /var/lib/docker

echo DONE
