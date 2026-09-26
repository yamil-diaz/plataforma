# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + frontend estático ──────────────────────────────
FROM python:3.11-slim

# Dependencias del sistema para psycopg2 y pypdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY backend/ ./

# Copiar frontend buildado desde stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend_dist

# Crear directorios de storage
RUN mkdir -p /data/aeternum/books /data/aeternum/covers /data/aeternum/videos /data/aeternum/temp

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
