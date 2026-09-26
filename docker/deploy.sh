#!/bin/bash
# ── AeternumLibrary - Deploy Script para Hetzner VPS ────────────────────────
# Ejecutar en el VPS: bash deploy.sh
set -e

echo "=========================================="
echo "  AeternumLibrary - Deploy en Hetzner"
echo "=========================================="

# ── 1. Actualizar sistema ────────────────────────────────────────────────────
echo "[1/7] Actualizando sistema..."
apt-get update -y && apt-get upgrade -y

# ── 2. Instalar Docker ───────────────────────────────────────────────────────
echo "[2/7] Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# ── 3. Instalar Docker Compose ───────────────────────────────────────────────
echo "[3/7] Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# ── 4. Generar secrets ───────────────────────────────────────────────────────
echo "[4/7] Generando secrets..."
if [ ! -f .env ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    cat > .env << EOF
# ── Secrets (NO compartir) ──────────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}
DB_PASSWORD=${DB_PASSWORD}

# ── Dominio ─────────────────────────────────────────────────────────────────
CORS_ORIGINS=https://aeternumlibrary.com

# ── Google OAuth (opcional) ──────────────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://aeternumlibrary.com/auth/google/callback

# ── Email (Resend) ──────────────────────────────────────────────────────────
RESEND_API_KEY=

# ── Pagos (Paddle) ──────────────────────────────────────────────────────────
PADDLE_API_KEY=
PADDLE_CLIENT_TOKEN=
PADDLE_WEBHOOK_SECRET=
PADDLE_ENVIRONMENT=sandbox
EOF
    echo "  Archivo .env creado. Edita con tus API keys: nano .env"
else
    echo "  .env ya existe, saltando."
fi

# ── 5. Crear directorio de certificados ──────────────────────────────────────
echo "[5/7] Preparando certificados SSL..."
mkdir -p certbot/conf certbot/www

# ── 6. Build y levantar ──────────────────────────────────────────────────────
echo "[6/7] Building y levantando containers..."
docker-compose up -d --build

# ── 7. Obtener certificado SSL ───────────────────────────────────────────────
echo "[7/7] Configurando HTTPS..."
echo ""
echo "=========================================="
echo "  PASO MANUAL: Obtener certificado SSL"
echo "=========================================="
echo ""
echo "Primero, apunta tu dominio al IP de este servidor:"
echo "  IP de este servidor: $(curl -s ifconfig.me)"
echo ""
echo "Luego ejecuta este comando para obtener el certificado:"
echo ""
echo "  docker-compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d aeternumlibrary.com -d www.aeternumlibrary.com --email tu@email.com --agree-tos --no-eff-email"
echo ""
echo "=========================================="
echo "  DEPLOY COMPLETADO"
echo "=========================================="
echo ""
echo "Tu app estará en: https://aeternumlibrary.com"
echo ""
echo "Comandos útiles:"
echo "  docker-compose logs -f app     # Ver logs de la app"
echo "  docker-compose restart app     # Reiniciar la app"
echo "  docker-compose down            # Parar todo"
echo "  docker-compose up -d           # Levantar todo"
echo ""
