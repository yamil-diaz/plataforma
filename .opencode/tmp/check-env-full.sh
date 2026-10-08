#!/bin/bash
echo "=== /root/aeternum/.env KEYS ONLY ==="
if [ -f /root/aeternum/.env ]; then
  grep -oE '^[A-Z0-9_]+' /root/aeternum/.env | sort -u
  echo "--- non-empty keys ---"
  grep -E '^[A-Z0-9_]+=..+' /root/aeternum/.env | cut -d= -f1 | sort -u
else
  echo "no file"
fi
echo "=== /root/plataforma/docker/.env KEYS ==="
grep -oE '^[A-Z0-9_]+' /root/plataforma/docker/.env 2>/dev/null | sort -u
echo "--- non-empty ---"
grep -E '^[A-Z0-9_]+=..+' /root/plataforma/docker/.env 2>/dev/null | cut -d= -f1 | sort -u
echo "=== frontend_dist exists? ==="
ls /root/plataforma/backend/frontend_dist 2>/dev/null | head -10
ls /app/frontend_dist 2>/dev/null | head -5
docker exec docker-app-1 ls /app/frontend_dist 2>/dev/null | head -10
echo "=== app env keys ==="
docker exec docker-app-1 printenv | cut -d= -f1 | sort
echo "=== google auth endpoints ==="
grep -n "google\|GOOGLE\|auth/google" /root/plataforma/backend/server.py | head -40
echo "=== vite env files ==="
ls -la /root/plataforma/frontend/.env* 2>/dev/null
ls -la /root/plataforma/frontend/dist 2>/dev/null | head -5
echo DONE
