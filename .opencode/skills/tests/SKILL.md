---
name: tests
description: Suite de tests de AeternumLibrary - 36 archivos backend, cubre PDF, libros, commerce, forum, AI, QR, featured books, storage
---

## Tests de AeternumLibrary

### Ejecutar tests

```bash
cd backend
python -m pytest tests/ -v
```

### Estructura

```
backend/tests/
├── test_*.py (36 archivos)
```

### Cobertura por area

| Area | Archivos de test | Que cubren |
|------|------------------|------------|
| PDF/Lectura | test_pdf_*.py | Extraccion, paginacion, deteccion de capitulos |
| Libros | test_book_*.py | CRUD, deduplicacion, validacion de contenido |
| Commerce | test_commerce_*.py | Compras, alquileres, webhooks, stock |
| Forum | test_forum_*.py | Posts, respuestas, likes, bookmarks, rate limiting |
| AI | test_ai_*.py | Chat, contexto, providers, conversaciones |
| QR | test_qr_*.py | Generacion, escaneo, deduplicacion |
| Featured | test_featured_*.py | Libros destacados del mes |
| Storage | test_storage_*.py | Persistencia de archivos, rutas |
| Repagination | test_repagination_*.py | Re-paginacion de libros existentes |
| Auth | test_auth_*.py | Registro, login, JWT |

### Notas

- Tests usan SQLite en memoria para velocidad
- Mock del AI provider para tests de AI
- Fixtures comunes en `conftest.py`
- Correr tests antes de cada deploy
