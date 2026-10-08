# Estado de migración Render → Hetzner

> Archivo vivo. Última revisión: 2026-10-06 — **Flow eliminado** (solo Paddle + Culqi). Google OAuth OK. Admin seed rotado: `admin@plataforma.com` / `Aet2026!Admin`. Paddle production keys SET. Culqi keys **vacías** (físicos Perú no cobran hasta configurar).
>
> Tools no disponibles en esta sesión: skills emil-kowalski/impecable/taste (no existen en repo), Figma MCP y Playwright MCP (no conectados), `github.com/affann/ECC` (404).

## Estado funcional

| Área | Estado |
|------|--------|
| HTTPS + frontend | ✅ 200, assets OK (UI polish 2026-10-05) |
| Users | ✅ 40 restaurados del dump Render 27-ago + admin |
| Books | ✅ 171 |
| Google OAuth | ✅ funciona (redirect backend; consent screen: verificar que esté en **Production**, no Testing) |
| IA Gemini | ✅ `AI_PROVIDER=gemini` + key |
| Email Resend | ✅ key presente (rechaza emails de prueba tipo example.com) |
| Paddle backend | ✅ API key + webhook secret (producción) |
| Paddle frontend | ✅ token runtime `/api/config/public` |
| Culqi (físico Perú) | ❌ keys vacías — checkout físico no funciona hasta cargar `CULQI_*` |
| Flow (Chile) | ❌ **eliminado del código** (endpoints 410) |
| Paddle | ✅ production, keys en .env |
| Storage Hetzner | ✅ ~545 MB/s write (SSD local, más rápido que Render) |
| Roles UI | ✅ Comprador/Vendedor/Admin (DB: user/autor/admin) |

## Pendientes

1. **Culqi keys** (si vendés físicos en Perú): `CULQI_PUBLIC_KEY`, `CULQI_SECRET_KEY`, `CULQI_WEBHOOK_SECRET`
2. **Flow keys** (si vendés en Chile): `FLOW_API_KEY`, `FLOW_API_SECRET`
3. Webhooks Paddle apuntar a `https://aeternumlibrary.com` en el dashboard de Paddle
4. Render Billing (~$18) — mail a soporte
5. ~~Rotar password admin seed~~ — **HECHO** 2026-10-06: `admin@plataforma.com` / `Aet2026!Admin`
6. Certbot renew antes de 2026-12-29
7. Covers faltantes / texto de PDFs disk-only (opcionales)

## Infra

| Dato | Valor |
|------|--------|
| VPS | `root@2.28.134.22` hostname `aeternum-server` |
| Proyecto activo en VPS | `/root/plataforma/docker/` |
| Copia en VPS | `/root/aeternum/` (certs + `.env` con secrets de Render) |
| Compose activo | `/root/plataforma/docker/docker-compose.yml` (bind mounts certbot) |
| Service Render | `srv-d9dt4vbtqb8s739dcmrg` |
| Disk Render | `/var/data/aeternum` (~10GB, cobra ~$2.50/mes) |
| URL Render | `https://aeternum-world.onrender.com` |
| DB Render (URL vieja en `.env`) | `dpg-d9e52s77f7vs739rta30-a.plataforma_ugk5.render.com` → **NXDOMAIN** |
| Pubkey PC en Render | **Pendiente** (todas las regiones: Permission denied) |
| Región Render | **No confirmada** (ver Dashboard → Connect → SSH) |

## Diagnóstico Hetzner (2026-10-03, post-fix)

| Check | Estado |
|-------|--------|
| nginx | **Up** — certs copiados al bind mount `./certbot/conf` |
| HTTPS | `https://aeternumlibrary.com` → **200** (cert hasta 2026-12-29) |
| app | Up, bind `127.0.0.1:8000` (cerrado a 0.0.0.0) |
| db | Up, healthy — password sincronizado con `.env` |
| `.env` proyecto activo | Secrets hex reales, `RENDER=false`, CORS dominio. Backup: `.env.bak-*` |
| Storage volumen | **Restaurado** desde Render: 416MB / 430 files (books + covers + videos + temp) |
| DB local books/users | **0 / 0** — la Postgres de Render ya no existe (NXDOMAIN); solo quedan los archivos del disk |

## Diagnóstico Render (POST-CORTE, 2026-10-03)

| Check | Estado |
|-------|--------|
| `https://aeternum-world.onrender.com` | **404** — service eliminado |
| `/api/books` en Render | **404** |
| Disk `/var/data/aeternum` | **Eliminado por usuario** (backup previo verificado) |
| DB `plataforma-db` | **Eliminada por usuario** (ya no había data: NXDOMAIN) |
| Password DB | **Rotado por usuario** (URL se había pegado en chat) |
| Billing | **Pendiente de confirmar $0** en Dashboard |

## Verificación Hetzner (POST-ENV FULL)

| Check | Estado |
|-------|--------|
| Frontend assets JS/CSS | **200** (fix nginx: `/assets/` → app, no volumen) |
| `/api/auth/google` | **OK** — devuelve `auth_url` con redirect `https://aeternumlibrary.com/auth/google/callback` |
| `/api/books` | **200**, 171 libros |
| `/api/health` | OK |
| Container env | GOOGLE_* ✅, GEMINI_API_KEY ✅, AI_PROVIDER=gemini ✅, RESEND ✅, PADDLE ✅, RENDER=false, STORAGE_DIR=/data/aeternum |
| CULQI_* | Vacíos (físico Perú no migrado) |
| Puerto 8000 | 127.0.0.1 |

### Fix fondo blanco

Nginx tenía `location /assets/ { alias /data/aeternum/; }` → los bundles del frontend devolvían 404. Ahora `/assets/` y favicons van al **app** (build React dentro de la imagen).

### Login usuarios

- **Google**: botón en `/login` → `GET /api/auth/google` → callback `/auth/google/callback`. Creo/linkea cuenta por email.
- **Email**: registro + login normales (`/register`, `/login`). No hace falta ser admin.
- Admin seed sigue disponible solo para gestión.

### Google Cloud Console (usuario)

Debe tener autorizado el redirect:
`https://aeternumlibrary.com/auth/google/callback`

## Restore ejecutado (2026-10-03)

1. Schema: `books.cover_image_url`, `books.uploader_id` (+ FK uploader)
2. Compose server: `RENDER=true` → `RENDER=false`
3. Admin seed: `admin@plataforma.com` / `admin123`
4. Import: `/app/production_books.json` (93 libros con content/covers/pdf)
5. Disk-only: 78 PDFs sin fila previa → entradas mínimas (`source=disk`, content vacío)
6. App recreate + verify API/covers

Scripts: `/root/restore_all.py`, `/root/restore-run2.sh` en el VPS.

## Backup del disk (HECHO y retenido)

| Destino | Path | Estado |
|---------|------|--------|
| PC | `C:\Users\Z\Desktop\render-backup-aeternum\aeternum-disk.tar.gz` | 355MB |
| Hetzner tarball | `/root/aeternum-disk.tar.gz` | 355MB |
| Hetzner extract | `/root/render-backup-aeternum/` | 417MB, 430 files |
| Volumen Docker | `docker_aeternum-data` | 416MB, books/covers visibles |

## Pendientes (post-restore)

1. Usuario: **Billing Render** — esperar soporte / pagar o cancelar ~$18.23 ($17.15 sept + $1.08 oct).
2. **Rotar password admin** (`admin123` es temporal).
3. Opcional: covers para los ~143 libros sin portada; extract de texto/page_count para los 78 disk-only.
4. Opcional: certbot renew antes de 2026-12-29.

## Archivos de ops creados

- `.opencode/skills/hetzner-ops/SKILL.md`
- `.opencode/skills/render-corte/SKILL.md`
- `.opencode/command/migrar-render.md`
- `opencode.json`: permisos ssh/docker/curl → allow; MCP github enabled=false
- `AGENTS.md`: lista skills nuevos

## Orden de ejecución

```
1. [HECHO] Pubkey PC en Render + SSH oregon con -i
2. [HECHO] Fix Hetzner: certs, .env, SSL, puerto 8000
3. [HECHO] Backup disk Render → PC + Hetzner + volumen Docker
4. [HECHO] Usuario: password DB rotado
5. [HECHO] Usuario: delete disk + web service + DB en Render
6. [PENDIENTE] Billing → confirmar $0
7. [PENDIENTE] Reconstruir filas de books en DB local de Hetzner
```

## Qué NO hacer

- No borrar disk/service/DB en Render sin backup verificado
- No pegar Paddle/Google/Resend/DB passwords en el chat
- No restaurar dumps de 0 bytes
- No instalar Open Interpreter / computer-use (ya hay bash en opencode)
- No asumir región de Render ni que la pubkey ya está

## Prompt para pegar al reiniciar opencode

Copia y pega esto como primer mensaje (completo o el bloque largo):

```text
Seguimos la migración Render → Hetzner de AeternumLibrary.
Leé .opencode/estado-migracion.md y cargá skills hetzner-ops y render-corte.
Estado: Hetzner root@2.28.134.22, proyecto en /root/plataforma/docker; nginx en crash-loop porque los certs de Let's Encrypt están en /root/aeternum/certbot/conf y NO en el bind mount del compose activo; .env del server tiene SECRET_KEY y DB_PASSWORD literales "$(openssl rand -hex ...)" y RENDER=true; puerto 8000 expuesto en 0.0.0.0; DB local books=0. En Render: service srv-d9dt4vbtqb8s739dcmrg, disk /var/data/aeternum, Postgres free NXDOMAIN (probablemente borrada), la pubkey de esta PC NO está agregada en el dashboard. No borres nada en Render todavía.
Primero: diagnosticá Hetzner y arreglá certs+.env+SSL si te autorizo escribir en el VPS; si pregunto por Render pedime la pubkey/comando SSH. No pegues secrets en la respuesta. No hagas delete en Render sin mi OK recurso por recurso.
```

Versión corta:

```text
/migrar-render
Estado en .opencode/estado-migracion.md. Seguimos Render→Hetzner. Pubkey Render pendiente. No borrar nada en Render sin mi OK.
```

