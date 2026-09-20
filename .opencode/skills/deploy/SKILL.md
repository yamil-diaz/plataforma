---
name: deploy
description: Proceso de deploy en Render.com - build, start, variables de entorno, persistent disk, troubleshooting comun
---

## Deploy en Render.com

### Configuracion

- `render.yaml` define el servicio: web service + PostgreSQL + persistent disk
- Dominio: `aeternumlibrary.com` / `aeternum-world.onrender.com`

### Build y Start

```bash
# Build
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build

# Start (produccion)
cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
```

### Variables de entorno criticas

- `DATABASE_URL` - Conexion PostgreSQL (se genera automaticamente en Render)
- `JWT_SECRET` - Secreto para tokens JWT
- `GEMINI_API_KEY` - API key de Google Gemini
- `PADDLE_API_KEY` / `PADDLE_WEBHOOK_SECRET` - Pagos Paddle
- `CULQUI_SECRET_KEY` - Pagos Culqi
- `STORAGE_PATH` - Ruta del persistent disk (`/var/data/aeternum`)

### Persistent Disk

- Montado en `/var/data/aeternum` (10 GB)
- Contiene: books, covers, videos de usuarios
- NO se pierde entre deploys
- Usar `storage_config.py` para todas las rutas

### Troubleshooting comun

1. **Build falla**: Verificar `requirements.txt` y `package.json`
2. **DB connection**: Verificar `DATABASE_URL` y que PostgreSQL este corriendo
3. **Storage lost**: Verificar que el persistent disk este montado en `/var/data/aeternum`
4. **Memory limit**: Render free tier tiene 512MB. Upgrade si es necesario
5. **Timeout**: Uvicorn timeout default es 120s. Aumentar si hay uploads grandes

### Archivos clave

- `render.yaml` - Config declarativa de Render
- `backend/server.py` - Punto de entrada de la app
- `backend/storage_config.py` - Gestion de rutas de almacenamiento
- `iniciar.ps1` - Bootstrapper local (venv + npm + dual servers)
