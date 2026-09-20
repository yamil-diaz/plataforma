---
name: bug-fix
description: Flujo para diagnosticar y corregir bugs en AeternumLibrary - logs, debugging, testing, deployment
---

## Flujo para arreglar bugs

### 1. Diagnosticar

```bash
# Ver logs en produccion (Render dashboard)
# O localmente:
cd backend && python -m uvicorn server:app --reload

# Verificar base de datos
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 5;"
```

### 2. Reproducir

- Identificar pasos exactos para reproducir el bug
- Verificar si ocurre en local o solo en produccion
- Verificar si es de frontend, backend, o ambos

### 3. Buscar codigo relevante

- Backend: `backend/server.py` (6615 lineas, buscar endpoints relevantes)
- Frontend: `frontend/src/pages/` (paginas relevantes)
- DB: `backend/database.py` (schema)

### 4. Escribir test que falle

```bash
cd backend
# Crear test que reproduzca el bug
# Ejecutar para confirmar que falla
python -m pytest tests/test_mi_bug.py -v
```

### 5. Corregir

- Cambios最小 necesarios
- Seguir convenciones existentes
- No romper funcionalidad existente

### 6. Verificar

```bash
# Correr todos los tests
python -m pytest tests/ -v

# Verificar lint/typecheck si existen
```

### 7. Deploy

- Commit con mensaje descriptivo
- Push a la rama principal
- Render hace auto-deploy
- Verificar en produccion

### Areas comunes de bugs

- **Deduplicacion**: Verificar hash SHA-256 y normalizacion
- **Webhooks**: Verificar idempotencia y validacion HMAC
- **AI**: Verificar rate limits y manejo de errores de Gemini
- **Storage**: Verificar rutas en `storage_config.py` (no hardcodear)
- **Auth**: Verificar JWT tokens y permisos
- **Foro**: Verificar rate limiting
