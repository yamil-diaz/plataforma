---
description: Runbook completo de migración Render → Hetzner (backup, fix VPS, corte de cobro). Usa skills hetzner-ops y render-corte.
agent: build
---

Migración AeternumLibrary de Render a Hetzner. Ejecutá el runbook en orden. No saltes pasos destrucción sin backup.

Contexto conocido:
- VPS: root@2.28.134.22 (aeternum-server)
- Proyecto activo en el server: /root/plataforma/docker
- Service Render: srv-d9dt4vbtqb8s739dcmrg
- Disk Render: /var/data/aeternum
- Postgres Render free: probablemente NXDOMAIN / borrada
- Hetzner puede tener DB vacía, nginx en crash-loop por certs, .env con $(openssl...), RENDER=true, puerto 8000 expuesto

Argumentos del usuario: $ARGUMENTS

Fase 0 — Diagnóstico (solo lectura):
1. Cargar skills hetzner-ops y render-corte si no están en contexto.
2. SSH Hetzner: docker compose ps, logs nginx, cat .env del proyecto activo (enmascarar secretos), du del volumen aeternum-data, counts de books/users.
3. Probar si la pubkey de esta PC está en Render: ssh a las 5 regiones con BatchMode.
4. Reportar: qué está roto en Hetzner, qué se puede salvar de Render, qué falta del usuario (pubkey, región, confirmación de delete).

Fase 1 — Artefactos en el repo (si faltan):
1. Asegurar .opencode/skills/hetzner-ops y render-corte.
2. Asegurar .opencode/command/migrar-render.md.
3. Actualizar AGENTS.md con los skills nuevos.
4. No commitear salvo que el usuario lo pida.

Fase 2 — Fix Hetzner (requiere autorización del usuario para cambios):
1. Copiar certs de /root/aeternum/certbot/conf al proyecto activo si faltan live/archive.
2. Regenerar SECRET_KEY y DB_PASSWORD literales en .env; RENDER=false; CORS_ORIGINS=https://aeternumlibrary.com.
3. Cerrar app a 127.0.0.1:8000 si está en 0.0.0.0.
4. Recrear nginx/app; verificar curl https://aeternumlibrary.com.

Fase 3 — Backup Render (si el usuario agregó la pubkey):
1. du/ls de /var/data/aeternum vía SSH a Render.
2. scp a PC y a Hetzner.
3. Si hay dump Postgres válido, restaurar en docker-db-1.

Fase 4 — Corte (solo con visto bueno explícito del usuario, recurso por recurso):
1. Pedir confirmación para Delete disk.
2. Delete service.
3. Delete DB si existe.
4. Pedir que revise Billing a $0.

Fase 5 — Verificación final:
1. https://aeternumlibrary.com responde 200.
2. Hetzner con data esperada.
3. Resumen de qué se borró y qué quedó.

Si algo falla, detener y explicar el bloqueo. No inventar credenciales. No pegar secrets en la respuesta.
