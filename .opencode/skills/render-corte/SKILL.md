---
name: render-corte
description: Use when cutting over off Render.com — backup persistent disk, stop charges, delete disk/service/Postgres safely, or diagnose why Render SSH/Postgres is unavailable for AeternumLibrary.
---

# Render Corte — dejar de cobrar sin perder data

Servicio en Render: web service **`plataforma`**, service id **`srv-d9dt4vbtqb8s739dcmrg`**.  
URL pública histórica: `https://aeternum-world.onrender.com`.  
Disk: `aeternum-storage`, mount `/var/data/aeternum`, ~10 GB (**$0.25/GB/mes ≈ $2.50**).

## Reglas de oro

1. **No borrar nada** hasta tener backup del disk (y dump de DB si la DB existe).
2. Free Postgres **expira a los 30 días** y Render **borra la data**. Hostname `dpg-...` con **NXDOMAIN** = DB ya no existe.
3. Free web services **no permiten disk ni SSH**. Si hay disk, el service debería ser pago.
4. Passwords/API keys **nunca en el chat**. Pubkey SSH sí (es pública).

## Dónde está cada cosa en el Dashboard

| Qué | URL |
|-----|-----|
| Account / SSH keys | `https://dashboard.render.com/settings#ssh-public-keys` |
| Service | Dashboard → proyecto → `plataforma` |
| Connect → SSH / Shell | Service → botón **Connect** arriba a la derecha |
| Disk | Service → página del disk |
| DB | Proyecto → `plataforma-db` → Connections |
| Billing | `https://dashboard.render.com/billing` |

En la UI nueva, **SSH Public Keys** puede no aparecer en el menú lateral. Usar la URL directa o pestañas **Security** / **Authentication**, o **Connect → SSH**.

## SSH desde la PC Windows

La pubkey de esta PC (ya sirve para Hetzner) debe estar en **Account → SSH Public Keys**:

```text
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC8qWis4sv0lwuRBPBJCsnRXbTRfhQQkANiwmGYM1A2KRkFoYVQKaYM/9wZG8bpsObykXOg+QsW9bpWaJUOXC44JHy68+8WJgE8rWVv3ui+988eEeA0wcYWf81TBBm4W0SsTIZAd8h6+Q/69LJEbLCn2yH6GiHh9RnJqRpca8cnOXtnzMp0qUdYZZFYEiMAroVms00L1lUZzRbsd+UrQQRUVxRQxJiux+dzUtguvZvv5UvBl/Bh4XAoyLlSVXW/vHMWNvt4xMqGMseKAS+19fjXSxAWZpxl5m2r0JDxGCp3F5I7FDGLle5Nw9l+2tBlEDOve1XSv3P7AUnT1Wp6pYUV7IlUphUCYYh5+UPzxg7tmRxdCtEki/L4xylmJJkE4FY3oy8RJKIjVf6/e/y0PHvQ5bapQz8Fjh2I03JiLc98o2EXRN0iJDzzzlSZQDUFPhPH/N0Eezqbqu8g+sMoy/ZHTjb2TP0nLUwqYlnKZDE4bWRGQTr2kH7AzBr9H/z3vGujHBVHKkhwtZPJf08aIIwr40RAejkPFlH5BBsacg3V4IZsmnVTCekOBfodzyUY2kqI4I0sKT0FEqywUOx3EOy1/MtT4fElIwC+3aSEPmbuKNfh9i3v7GTOvCfH6cIalppOM96D4m805bnsWAOyx20P1NHHpvBCwE9JXIlKEAnZLw==
```

Formato SSH (REGION sale del Dashboard → Connect → SSH):

```bash
ssh srv-d9dt4vbtqb8s739dcmrg@ssh.OREGON.render.com
```

Regiones Render: `oregon`, `ohio`, `virginia`, `frankfurt`, `singapore`.

Si da `Permission denied (publickey)` en **todas** las regiones → la key **no está** agregada en la cuenta.

## Backup del disk (ANTES de delete)

Desde la PC (con key + región correctas):

```bash
ssh srv-d9dt4vbtqb8s739dcmrg@ssh.REGION.render.com "du -sh /var/data/aeternum; ls -la /var/data/aeternum"

scp -r srv-d9dt4vbtqb8s739dcmrg@ssh.REGION.render.com:/var/data/aeternum C:\Users\Z\Desktop\render-backup-aeternum

scp -r C:\Users\Z\Desktop\render-backup-aeternum root@2.28.134.22:/root/render-backup-aeternum
```

Criterio de éxito: `du` muestra tamaño > 0 y hay archivos en `books/`, `covers/`, etc.

### Alternativa si no hay SSH (solo Shell del Dashboard)

En **Service → Shell**:

```bash
du -sh /var/data/aeternum
ls -la /var/data/aeternum
```

Para bajar archivos sin key: Magic-Wormhole (docs de Render) o agregar la pubkey.

## Dump de Postgres (solo si la DB existe)

La URL externa vieja en `/root/aeternum/.env` es de Render free. Si el host **no resuelve**, ya no hay data remota.

Si en Dashboard la DB **aparece**:

1. Connections → copiar External Database URL **nueva**
2. Desde Hetzner (tiene `pg_dump` en la imagen postgres):

```bash
URL='postgresql://user:pass@HOST:5432/dbname'
docker exec docker-db-1 pg_dump "$URL" -Fc -f /tmp/aeternum_render.dump
docker exec docker-db-1 ls -lh /tmp/aeternum_render.dump
```

**Solo restorear si el dump pesa > 0** y `pg_restore --list` muestra tablas.

## Orden de corte (cuando Hetzner ya sirve)

```
1. Backup disk en PC + Hetzner
2. Fix Hetzner (.env, SSL, data)  → skill hetzner-ops
3. Verificar https://aeternumlibrary.com OK
4. Render Dashboard:
   a. Delete disk
   b. Delete web service
   c. Delete database (si existe)
5. Billing → confirmar sin servicios live ni storage
```

Borrar el service suele arrastrar su disk; igual conviene borrar disk primero si el objetivo es cortar el cargo de storage ya.

## Qué está cobrando (según render.yaml + pricing)

| Recurso | Precio aprox. | Corte |
|---------|---------------|-------|
| Disk 10 GB | ~$2.50/mes | Delete disk |
| Web service pago | $7+/mes | Delete/suspend service |
| Postgres paid | $6+/mes | Delete DB |
| Postgres free | $0, expira 30 días | Puede ya no existir |

## Señales de que la DB free murió

- `getent hosts dpg-....render.com` → NXDOMAIN
- `pg_isready -h dpg-...` → no response
- `/api/books` en `onrender.com` → 502
- Hetzner `books=0` sin restore

En ese caso el único valor recuperable es el **disk**.

## Seguridad

- No pegar `PADDLE_*`, `GOOGLE_*`, `RESEND_*`, passwords de DB en el chat ni en git.
- `.env` en la PC local (`docker/.env`) tiene claves live → no commitear; rotar si llegó a un repo público.
- Preferir pubkey SSH o token de Render guardado en el VPS (`chmod 600`), no en la conversación.

## Checklist “Render cortado”

- [ ] Backup del disk en PC y en Hetzner
- [ ] Hetzner sirve por `https://aeternumlibrary.com`
- [ ] Disk eliminado en Dashboard
- [ ] Service eliminado
- [ ] DB eliminada (o confirmada ya borrada)
- [ ] Billing sin cargos de compute ni storage
