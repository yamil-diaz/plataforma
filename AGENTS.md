# AeternumLibrary

Plataforma gamificada de lectura y educacion. "La primera plataforma donde la lectura tiene recompensas".

## Estado de migración (leer primero si el usuario pide deploy/Render/Hetzner/SSL)

La producción está en **Hetzner**; **Render** es legacy y se está cortando (cobro).

- **Estado vivo:** `.opencode/estado-migracion.md` (diagnóstico, pendientes, orden de corte)
- **Skills ops:** `hetzner-ops`, `render-corte`
- **Comando runbook:** `/migrar-render`
- **Pendiente del usuario:** pubkey SSH en Render + comando SSH del Dashboard
- **Hetzner puede estar roto:** nginx crash-loop por certs en el mount equivocado, `.env` con `$(openssl...)`, puerto 8000 expuesto, DB vacía

Si el usuario dice “seguimos la migración”, “arreglá Hetzner”, “cortá Render” o similar: leer `.opencode/estado-migracion.md` y cargar `hetzner-ops` + `render-corte`.

## Skills disponibles

Usa la herramienta `skill` para cargar cualquiera de estos:

- `arquitectura` - Estructura completa del proyecto (stack, archivos, DB, rutas)
- `agregar-libro` - Flujo para agregar libros (upload, Gutenberg, importacion masiva)
- `agregar-curso` - Crear cursos en Aeternum Academy
- `deploy` - Deploy en Render.com
- `hetzner-ops` - VPS Hetzner (Docker, nginx SSL, certbot, .env, volumenes)
- `render-corte` - Backup del disk de Render y baja de cobro sin perder data
- `pagos` - Sistema de pagos (Paddle, Culqi, Flow)
- `ai-assistant` - Chat AI con Google Gemini
- `foro` - Foro estudiantil
- `tests` - Suite de 36 tests backend
- `bug-fix` - Flujo para diagnosticar y corregir bugs

## Comandos

- `/migrar-render` - Runbook completo Render → Hetzner (backup, fix VPS, corte)

## Convenciones

- Backend: Python/FastAPI en `backend/server.py`
- Frontend: React/Vite en `frontend/src/`
- DB: PostgreSQL, schema en `backend/database.py`
- Storage: usar `backend/storage_config.py` (no hardcodear rutas)
- Tests: `python -m pytest backend/tests/ -v`
- Producción actual: Hetzner `2.28.134.22` + Docker (`docker/docker-compose.yml` en el VPS bajo `/root/plataforma/docker/`)
- Deploy legacy: Render.com (en proceso de corte — ver skill `render-corte` y `estado-migracion.md`)
- No commitear `.env` ni secrets; no pegar claves en el chat
