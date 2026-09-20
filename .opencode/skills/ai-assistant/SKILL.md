---
name: ai-assistant
description: Sistema de chat AI de AeternumLibrary - Google Gemini, contexto jerarquico, conversaciones persistentes, economia de Aethers
---

## Chat AI de AeternumLibrary

### Arquitectura

```
Usuario -> Frontend Chat -> POST /api/ai/chat -> ai_service.py
                                                     ↓
                                              ai_context.py (construye prompt)
                                                     ↓
                                              ai_providers.py (Gemini/Mock)
                                                     ↓
                                              ai_conversations.py (persistencia)
```

### Contexto jerarquico (ai_context.py)

El AI tiene acceso a 3 niveles de contexto:

1. **Conocimiento oficial** - Instrucciones base del sistema
2. **Contenido del libro** - El libro que el usuario esta leyendo actualmente
3. **Historial de conversacion** - Mensajes anteriores de la sesion

### Proveedores (ai_providers.py)

- **Mock** - Para desarrollo, devuelve respuestas predefinidas
- **Google Gemini** - Produccion, via `google-genai` SDK

### Persistencia (ai_conversations.py)

- Cada conversacion se guarda en PostgreSQL (tabla `ai_conversations`)
- Incluye: usuario_id, book_id, mensajes, timestamp
- Se carga historial al abrir chat

### Economia de Aethers (ai_rayos.py)

- Actualmente desactivado/pendiente de pricing
- Planeado: cobrar Aethers por uso del AI
- Framework listo para integrar

### Observabilidad (ai_observability.py)

- Metricas en memoria: llamadas, reintentos, fallos, latencias
- Endpoint para consultar metricas (admin)

### Manejo de errores

- 1 reintento para fallos transitorios
- Delay configurable
- Logging de errores

### Codigo relevante

- Servicio: `backend/ai_service.py`
- Proveedores: `backend/ai_providers.py`
- Contexto: `backend/ai_context.py`
- Conversaciones: `backend/ai_conversations.py`
- Economia: `backend/ai_rayos.py`
- Observabilidad: `backend/ai_observability.py`
- Frontend chat: `frontend/src/utils/iaChat.js`

### Prompt del AI

El AI responde preguntas sobre el libro que el usuario esta leyendo. No inventa contenido del libro. Si no sabe, lo dice.
