# AeternumLibrary

Plataforma gamificada de lectura y educacion. "La primera plataforma donde la lectura tiene recompensas".

## Skills disponibles

Usa la herramienta `skill` para cargar cualquiera de estos:

- `arquitectura` - Estructura completa del proyecto (stack, archivos, DB, rutas)
- `agregar-libro` - Flujo para agregar libros (upload, Gutenberg, importacion masiva)
- `agregar-curso` - Crear cursos en Aeternum Academy
- `deploy` - Deploy en Render.com
- `pagos` - Sistema de pagos (Paddle, Culqi, Flow)
- `ai-assistant` - Chat AI con Google Gemini
- `foro` - Foro estudiantil
- `tests` - Suite de 36 tests backend
- `bug-fix` - Flujo para diagnosticar y corregir bugs

## Convenciones

- Backend: Python/FastAPI en `backend/server.py`
- Frontend: React/Vite en `frontend/src/`
- DB: PostgreSQL, schema en `backend/database.py`
- Storage: usar `backend/storage_config.py` (no hardcodear rutas)
- Tests: `python -m pytest backend/tests/ -v`
- Deploy: auto-deploy via Render en push a main
