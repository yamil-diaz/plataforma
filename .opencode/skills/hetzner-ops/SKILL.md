---
name: hetzner-ops
description: Use when operating the AeternumLibrary Hetzner VPS (2.28.134.22) — Docker compose, nginx SSL, certbot, .env secrets, storage volumes, or verifying https://aeternumlibrary.com after the Render migration.
---

# Hetzner Ops — AeternumLibrary

VPS de producción: **Hetzner** `2.28.134.22`, hostname `aeternum-server`.

## Acceso

```bash
ssh root@2.28.134.22
```

Key de esta PC: `C:\Users\Z\.ssh\id_rsa` (ya en `authorized_keys` del VPS).

## Estructura en el servidor

| Ruta | Rol |
|------|-----|
| `/root/plataforma/docker/` | **Proyecto activo** — compose, nginx, certbot, .env |
| `/root/plataforma/backend/`, `frontend/` | Código buildado en el server |
| `/root/aeternum/` | Copia vieja + certs de certbot + `.env` con secrets reales y DB de Render |

**No confundir directorios.** Los containers activos montan desde `/root/plataforma/docker/`.

## Containers (docker compose)

Proyecto Docker: nombre `docker` (carpeta `docker/`).

```bash
cd /root/plataforma/docker
docker compose ps
docker compose logs -f nginx
docker compose logs -f app
docker compose up -d --force-recreate nginx
```

Servicios: `db` (postgres:16), `app` (uvicorn :8000), `nginx` (:80/:443), `certbot`.

## Volumenes

| Volumen | Montaje |
|---------|---------|
| `docker_aeternum-data` | `/data/aeternum` (books, covers, videos) |
| `docker_pgdata` | Postgres data |
| Bind `./certbot/conf` | `/etc/letsencrypt` en nginx/certbot |
| Bind `./certbot/www` | webroot ACME |

## Nginx / SSL

- Config activa: `./nginx.conf` (en el server **ya es SSL**, mismo contenido que `nginx-ssl.conf` local).
- `nginx-temp.conf` = solo HTTP :80 (para emitir el cert la primera vez).
- `nginx-ssl.conf` = redirect 80→443 + TLS + proxy.

Rutas de cert en el container:

```
/etc/letsencrypt/live/aeternumlibrary.com/fullchain.pem
/etc/letsencrypt/live/aeternumlibrary.com/privkey.pem
```

Los certs **deben estar** en `/root/plataforma/docker/certbot/conf/live/...` (bind mount). Si viven solo en `/root/aeternum/certbot/conf/`, copiarlos:

```bash
cp -a /root/aeternum/certbot/conf/{live,archive,renewal} /root/plataforma/docker/certbot/conf/ 2>/dev/null
ls -la /root/plataforma/docker/certbot/conf/live/aeternumlibrary.com/
docker compose up -d --force-recreate nginx
```

Verificar:

```bash
curl -sI http://aeternumlibrary.com     # 301 → https
curl -sI https://aeternumlibrary.com    # 200 + cert
docker compose logs nginx --tail 40
```

## .env (proyecto activo)

Path: `/root/plataforma/docker/.env`

Debe tener **valores literales**, no `$(openssl ...)`:

```
SECRET_KEY=<hex 64>
DB_PASSWORD=<hex 32>
CORS_ORIGINS=https://aeternumlibrary.com
RENDER=false
ENV=production
```

`DATABASE_URL` lo arma el compose con `${DB_PASSWORD}`. No pegar la URL de Render en el compose de Hetzner.

Secretos de referencia (NO copiar al repo): en `/root/aeternum/.env` están Google, Resend, Paddle, Culqi y la DB de Render.

## Puertos

| Puerto | Debe ser | Hoy (check) |
|--------|----------|-------------|
| 80, 443 | nginx público | OK |
| 8000 | solo `127.0.0.1` (no `0.0.0.0`) | verificar en compose |
| 5432 | `127.0.0.1` | OK en compose |

Para exponer 8000 solo localmente en `docker-compose.yml` del server:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

Luego `docker compose up -d --force-recreate app`.

## DB local

```bash
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT count(*) FROM books;"
docker exec docker-db-1 psql -U aeternum -d aeternum -c "SELECT count(*) FROM users;"
```

Si `books=0` y no se restauró dump de Render, la data de producción no está en Hetzner.

## Restore de dump Postgres

```bash
# dump en /root/aeternum_render.dump
docker exec -i docker-db-1 pg_restore -U aeternum -d aeternum --clean --if-exists < /root/aeternum_render.dump
```

Dump inválido (0 bytes) → no restorear.

## Storage desde el volumen

```bash
docker run --rm -v docker_aeternum-data:/data alpine sh -c 'du -sh /data; ls -la /data; du -sh /data/*'
```

## Checklist “Hetzner en pie”

- [ ] `docker compose ps` — nginx Up, no Restarting
- [ ] `curl -sI https://aeternumlibrary.com` → 200
- [ ] `.env` sin `$(openssl` ni `RENDER=true`
- [ ] Puerto 8000 no expuesto a `0.0.0.0`
- [ ] DB local con data real o dump restaurado
- [ ] `/data/aeternum` con books/covers si había data en Render

## Errores comunes

| Error | Causa | Fix |
|-------|-------|-----|
| nginx `[emerg] cannot load certificate` | certs no en el bind mount | copiar `live/`+`archive/` + recreate |
| `role "root" does not exist` | pg_dump sin URL o contra DB local mal | usar `DATABASE_URL` de Render o `-U aeternum` |
| App no conecta a DB | password literal `$(openssl...)` | regenerar secrets en `.env` + recreate |
| DNS NXDOMAIN a `dpg-...render.com` | free Postgres de Render borrada | no hay dump; backup solo del disk |

## Relación con Render

Hetzner es la meta. Render solo se usa para:
1. Backup del persistent disk `/var/data/aeternum` **antes** de borrar
2. Delete disk → service → DB
3. Billing $0

Ver skill `render-corte`.
