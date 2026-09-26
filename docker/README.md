# Deploy AeternumLibrary en Hetzner VPS

## Requisitos
- Cuenta en [Hetzner Cloud](https://cloud.hetzner.com)
- Dominio propio (ej: aeternumlibrary.com)

## Paso 1: Crear VPS (manual, 2 minutos)
1. Ir a https://cloud.hetzner.com
2. Crear proyecto → "aeternum"
3. Add Server → **CX22** ($5/mes, 2 vCPU, 4GB RAM, 40GB SSD)
4. Seleccionar: Ubuntu 24.04, ubicación más cercana
5. Agregar SSH key (si no tienes: `ssh-keygen` en tu PC y copia el contenido de `~/.ssh/id_rsa.pub`)
6. Crear servidor
7. Copiar la IP del servidor

## Paso 2: Conectar al VPS (manual)
```bash
ssh root@IP_DEL_SERVIDOR
```

## Paso 3: Subir archivos y deployar (semi-automático)
Desde tu PC (Windows/Mac/Linux), copia la carpeta `docker/` al VPS:
```bash
scp -r docker/* root@IP_DEL_SERVIDOR:/root/aeternum/
```

Luego en el VPS:
```bash
ssh root@IP_DEL_SERVIDOR
cd /root/aeternum
bash deploy.sh
```

## Paso 4: Configurar dominio (manual)
1. En tu proveedor de DNS, apunta:
   - `aeternumlibrary.com` → IP del VPS
   - `www.aeternumlibrary.com` → IP del VPS

2. Espera ~5 minutos a que propague

3. Obtener certificado HTTPS:
```bash
cd /root/aeternum
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d aeternumlibrary.com \
  -d www.aeternumlibrary.com \
  --email tu@email.com --agree-tos --no-eff-email
```

4. Reiniciar nginx:
```bash
docker-compose restart nginx
```

## Paso 5: Migrar datos de Render (opcional)
Si quieres llevar la base de datos de Render a Hetzner:
```bash
# En Render: ir a Database → Connection → copiar URL
# En Hetzner:
docker-compose exec db pg_dump -U aeternum -h TU_HOST_RENDER aeternum > dump.sql
docker-compose exec -T db psql -U aeternum aeternum < dump.sql
```

## Comandos útiles
```bash
docker-compose logs -f app      # Ver logs en tiempo real
docker-compose restart app      # Reiniciar la app
docker-compose down             # Parar todo
docker-compose up -d            # Levantar todo
docker-compose up -d --build    # Re-build y levantar
```

## Estructura de archivos
```
/root/aeternum/
├── Dockerfile          # Build de la app
├── docker-compose.yml  # App + PostgreSQL + Nginx
├── nginx.conf          # Configuración de Nginx
├── deploy.sh           # Script de instalación
├── .env                # Variables de entorno (NO subir a git)
└── .env.example        # Ejemplo de variables
```
