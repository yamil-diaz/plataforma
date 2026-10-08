#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== 1) Copiar certs al bind mount ==="
cp -a /root/aeternum/certbot/conf/live /root/plataforma/docker/certbot/conf/ 2>/dev/null || true
cp -a /root/aeternum/certbot/conf/archive /root/plataforma/docker/certbot/conf/ 2>/dev/null || true
cp -a /root/aeternum/certbot/conf/renewal /root/plataforma/docker/certbot/conf/ 2>/dev/null || true
ls -la /root/plataforma/docker/certbot/conf/live/aeternumlibrary.com/ | sed 's/privkey/privkey[omitted]/'
test -f /root/plataforma/docker/certbot/conf/live/aeternumlibrary.com/fullchain.pem
test -f /root/plataforma/docker/certbot/conf/live/aeternumlibrary.com/privkey.pem
echo "certs OK en bind mount"

echo "=== 2) Fix .env (secrets reales, sin imprimir) ==="
cp -a /root/plataforma/docker/.env /root/plataforma/docker/.env.bak-$(date +%Y%m%d-%H%M%S)
NEW_SECRET=$(openssl rand -hex 32)
NEW_DBPASS=$(openssl rand -hex 16)
# reemplazar solo la linea, sin eco
awk -v s="$NEW_SECRET" -v d="$NEW_DBPASS" '
  /^SECRET_KEY=/ { print "SECRET_KEY=" s; next }
  /^DB_PASSWORD=/ { print "DB_PASSWORD=" d; next }
  /^RENDER=/ { print "RENDER=false"; next }
  { print }
' /root/plataforma/docker/.env > /root/plataforma/docker/.env.new
# asegurar RENDER=false si no existia
if ! grep -q '^RENDER=' /root/plataforma/docker/.env.new; then
  echo 'RENDER=false' >> /root/plataforma/docker/.env.new
fi
# CORS ya correcto; forzar por si acaso
if grep -q '^CORS_ORIGINS=' /root/plataforma/docker/.env.new; then
  sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://aeternumlibrary.com|' /root/plataforma/docker/.env.new
else
  echo 'CORS_ORIGINS=https://aeternumlibrary.com' >> /root/plataforma/docker/.env.new
fi
mv /root/plataforma/docker/.env.new /root/plataforma/docker/.env
chmod 600 /root/plataforma/docker/.env

# validar sin imprimir valores
if grep -q 'openssl' /root/plataforma/docker/.env; then
  echo "ERROR: todavia hay plantilla openssl en .env" >&2
  exit 1
fi
if ! grep -q '^RENDER=false' /root/plataforma/docker/.env; then
  echo "ERROR: RENDER=false no quedo en .env" >&2
  exit 1
fi
if ! grep -q '^SECRET_KEY=' /root/plataforma/docker/.env; then
  echo "ERROR: falta SECRET_KEY" >&2
  exit 1
fi
if ! grep -q '^DB_PASSWORD=' /root/plataforma/docker/.env; then
  echo "ERROR: falta DB_PASSWORD" >&2
  exit 1
fi
echo ".env OK (valores literales, RENDER=false, sin plantilla)"

echo "=== 3) Sincronizar password de Postgres con .env ==="
# leer password del .env sin imprimirlo
DBPASS=$(grep -E '^DB_PASSWORD=' /root/plataforma/docker/.env | head -1 | cut -d= -f2-)
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 -c "ALTER USER aeternum WITH PASSWORD '${DBPASS}';"
echo "ALTER USER OK"

echo "=== 4) Cerrar puerto 8000 a localhost ==="
if grep -q '"8000:8000"' /root/plataforma/docker/docker-compose.yml; then
  sed -i 's/"8000:8000"/"127.0.0.1:8000:8000"/' /root/plataforma/docker/docker-compose.yml
fi
grep -nE '8000' /root/plataforma/docker/docker-compose.yml || true

echo "=== 5) Recrear nginx + app ==="
cd /root/plataforma/docker
docker compose up -d --force-recreate nginx app
sleep 3
docker compose ps

echo "=== 6) Verificar nginx ==="
docker compose logs nginx --tail 20 || true
curl -sI --max-time 10 http://aeternumlibrary.com | head -20 || true
curl -sI --max-time 10 https://aeternumlibrary.com | head -20 || true
curl -skI --max-time 10 https://127.0.0.1 -H 'Host: aeternumlibrary.com' | head -20 || true

echo "=== 7) Health app via localhost ==="
curl -s --max-time 10 http://127.0.0.1:8000/ | head -c 200 || true
echo
echo "=== DONE ==="
