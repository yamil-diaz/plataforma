#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== patch pool maxconn in image code ==="
# el código va en la imagen; parcheamos el archivo del host y rebuild liviano o docker cp + recreate
# mejor: aplicar SQL-level fix + restart con env DB_POOL_MAX=50 si el código lo lee del env
# pero el código actual de la imagen tiene maxconn=10 fijo. Parcheamos via sed en el build context.
if grep -q 'maxconn=10' /root/plataforma/backend/database.py; then
  sed -i 's/maxconn=10/maxconn=int(os.getenv("DB_POOL_MAX", "50"))/' /root/plataforma/backend/database.py
fi
grep -n 'maxconn' /root/plataforma/backend/database.py

# Also patch inside running container for immediate effect
docker exec docker-app-1 sh -c "sed -i 's/maxconn=10/maxconn=int(os.getenv(\"DB_POOL_MAX\", \"50\"))/' /app/database.py && grep -n maxconn /app/database.py"

echo "=== restart app ==="
docker compose up -d --force-recreate app
sleep 5
docker compose ps

echo "=== inspect dump with pg17 ==="
docker run --rm -v /root/plataforma_ugk5_20260827_210207.dump:/d.dump postgres:17-alpine pg_restore --list /d.dump 2>&1 | head -120

echo "=== try strings on dump for table names ==="
docker run --rm -v /root/plataforma_ugk5_20260827_210207.dump:/d.dump alpine sh -c 'strings /d.dump | grep -E "^[a-z_]+$" | sort -u | head -80'

echo DONE
