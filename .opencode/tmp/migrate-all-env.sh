#!/bin/bash
set -euo pipefail

# ── 0) Merge env sin imprimir valores ───────────────────────────────────────
OLD_ENV=/root/aeternum/.env
ACTIVE=/root/plataforma/docker/.env
BACKUP="${ACTIVE}.bak-$(date +%Y%m%d-%H%M%S)"
cp -a "$ACTIVE" "$BACKUP"

python3 - <<'PY'
import os, re, shutil

old_path = "/root/aeternum/.env"
active_path = "/root/plataforma/docker/.env"
gemini_path = "/root/gemini_key.txt"  # uploaded separately

def parse_env(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data

old = parse_env(old_path)
active = parse_env(active_path)
gemini = ""
if os.path.exists(gemini_path):
    with open(gemini_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                gemini = line.split("=", 1)[1].strip()
                break

# Preferir secrets reales del env viejo de Render
prefer_from_old = [
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "RESEND_API_KEY",
    "CULQI_PUBLIC_KEY", "CULQI_SECRET_KEY", "CULQI_WEBHOOK_SECRET",
    "PADDLE_API_KEY", "PADDLE_CLIENT_TOKEN", "PADDLE_WEBHOOK_SECRET",
    "FRONTEND_URL",
]
for k in prefer_from_old:
    if old.get(k):
        active[k] = old[k]

if gemini:
    active["GEMINI_API_KEY"] = gemini

active["AI_PROVIDER"] = "gemini"
active["GOOGLE_REDIRECT_URI"] = "https://aeternumlibrary.com/auth/google/callback"
active["CORS_ORIGINS"] = "https://aeternumlibrary.com"
active["RENDER"] = "false"
active["ENV"] = "production"
active["STORAGE_DIR"] = "/data/aeternum"
active["PADDLE_ENVIRONMENT"] = old.get("PADDLE_ENVIRONMENT") or active.get("PADDLE_ENVIRONMENT") or "production"
active["CULQI_ENVIRONMENT"] = old.get("CULQI_ENVIRONMENT") or "production"
active["VITE_PADDLE_CLIENT_TOKEN"] = active.get("PADDLE_CLIENT_TOKEN") or old.get("PADDLE_CLIENT_TOKEN") or ""
active["VITE_PADDLE_ENVIRONMENT"] = active["PADDLE_ENVIRONMENT"]

# No tocar DATABASE_URL / SECRET_KEY / DB_PASSWORD actuales (ya correctos en Hetzner)

order = [
    "SECRET_KEY", "DB_PASSWORD", "DATABASE_URL", "CORS_ORIGINS", "ENV", "RENDER",
    "STORAGE_DIR", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
    "RESEND_API_KEY", "GEMINI_API_KEY", "AI_PROVIDER",
    "PADDLE_API_KEY", "PADDLE_CLIENT_TOKEN", "PADDLE_WEBHOOK_SECRET", "PADDLE_ENVIRONMENT",
    "CULQI_PUBLIC_KEY", "CULQI_SECRET_KEY", "CULQI_WEBHOOK_SECRET", "CULQI_ENVIRONMENT",
    "FRONTEND_URL", "VITE_PADDLE_CLIENT_TOKEN", "VITE_PADDLE_ENVIRONMENT",
]
seen = set()
lines = []
for k in order:
    if k in active:
        lines.append(f"{k}={active[k]}")
        seen.add(k)
for k, v in active.items():
    if k not in seen:
        lines.append(f"{k}={v}")

with open(active_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
os.chmod(active_path, 0o600)

# Reporte de presencia (sin valores)
print("=== .env keys status ===")
for k in order:
    if k not in active:
        print(f"{k}=MISSING")
    elif not active[k]:
        print(f"{k}=EMPTY")
    else:
        print(f"{k}=SET(len={len(active[k])})")
PY

# ── 1) Compose: env completo + build args + RENDER=false ────────────────────
cd /root/plataforma/docker
cp -a docker-compose.yml "docker-compose.yml.bak-$(date +%Y%m%d-%H%M%S)"

python3 - <<'PY'
from pathlib import Path
p = Path("/root/plataforma/docker/docker-compose.yml")
text = p.read_text(encoding="utf-8")

# Puerto solo localhost
text = text.replace('- "8000:8000"', '- "127.0.0.1:8000:8000"')
text = text.replace('- RENDER=true', '- RENDER=false')

# Build args para VITE
old_build = """    build:
      context: ..
      dockerfile: docker/Dockerfile
"""
new_build = """    build:
      context: ..
      dockerfile: docker/Dockerfile
      args:
        VITE_PADDLE_CLIENT_TOKEN: ${VITE_PADDLE_CLIENT_TOKEN:-}
        VITE_PADDLE_ENVIRONMENT: ${VITE_PADDLE_ENVIRONMENT:-sandbox}
"""
if "VITE_PADDLE_CLIENT_TOKEN: ${VITE_PADDLE_CLIENT_TOKEN" not in text:
    text = text.replace(old_build, new_build)

# Agregar env que faltan si no están
need = [
    "      - GEMINI_API_KEY=${GEMINI_API_KEY:-}\n",
    "      - AI_PROVIDER=${AI_PROVIDER:-gemini}\n",
    "      - CULQI_PUBLIC_KEY=${CULQI_PUBLIC_KEY:-}\n",
    "      - CULQI_SECRET_KEY=${CULQI_SECRET_KEY:-}\n",
    "      - CULQI_WEBHOOK_SECRET=${CULQI_WEBHOOK_SECRET:-}\n",
    "      - CULQI_ENVIRONMENT=${CULQI_ENVIRONMENT:-production}\n",
    "      - FRONTEND_URL=${FRONTEND_URL:-https://aeternumlibrary.com}\n",
]
anchor = "      - PADDLE_ENVIRONMENT=${PADDLE_ENVIRONMENT:-sandbox}\n"
if anchor in text:
    block = anchor
    for line in need:
        key = line.strip().split("=")[0].replace("- ", "")
        if key not in text:
            block += line
    text = text.replace(anchor, block, 1)

p.write_text(text, encoding="utf-8")
print("compose updated")
print("--- RENDER/port/build ---")
for i, line in enumerate(text.splitlines(), 1):
    if "RENDER" in line or "8000" in line or "VITE_PADDLE" in line or "GEMINI" in line or "AI_PROVIDER" in line or "CULQI" in line:
        print(f"{i}:{line}")
PY

# ── 2) Fix nginx: /assets/ debe ir al app (frontend_dist), no al volumen ────
cp -a nginx.conf "nginx.conf.bak-$(date +%Y%m%d-%H%M%S)"
python3 - <<'PY'
from pathlib import Path
p = Path("/root/plataforma/docker/nginx.conf")
text = p.read_text(encoding="utf-8")
old = """        # Archivos estáticos del frontend (React)
        location /assets/ {
            alias /data/aeternum/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
"""
new = """        # Frontend assets (React build dentro de la imagen app)
        location /assets/ {
            proxy_pass http://app;
            proxy_set_header Host $host;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location = /favicon.svg {
            proxy_pass http://app;
        }
        location = /favicon.ico {
            proxy_pass http://app;
        }
        location = /favicon.jpg {
            proxy_pass http://app;
        }
"""
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("nginx /assets/ fixed -> proxy app")
else:
    print("nginx pattern not found; writing full https block check")
    print(text)
PY

echo "=== env merged, compose+nginx updated ==="
echo DONE_PHASE1
