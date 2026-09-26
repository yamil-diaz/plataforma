# Skill: Memory Optimization

Optimización de memoria para AeternumLibrary en Render (512MB free tier).

## Problema

`server.py` (~6800 lineas) importa TODOS los modulos al nivel de modulo. En Render free tier (512MB), esto causa OOM crashes despues de serve requests.

## Patron: Lazy Imports

En vez de importar modulos al top-level, importarlos DENTRO de la funcion que los necesita.

### Antes (ROMPE memoria):
```python
import lectura
from ai_service import process_chat

@app.post("/books/upload")
async def upload_book():
    procesado = lectura.procesar_contenido_para_publicacion(...)
```

### Despues (AHORRA memoria):
```python
@app.post("/books/upload")
async def upload_book():
    import lectura
    procesado = lectura.procesar_contenido_para_publicacion(...)
```

### Reglas de seguridad:
1. **Solo modulos pesados** - No hacer lazy de imports basicos (os, datetime, fastapi)
2. **Dentro de la funcion** - El import va al inicio de la funcion, no a nivel modulo
3. **Funcion auxiliar** - Si el modulo se usa en muchas funciones, crear helper:

```python
def _get_lectura():
    import lectura
    return lectura

# Uso:
lectura = _get_lectura()
```

### Modulos candidatos a lazy import (server.py):
| Modulo | Endpoint(s) | Peso |
|--------|-------------|------|
| `lectura` | upload, bulk import, repaginate | pesado (pypdf) |
| `ai_service` | /chat | medio |
| `ai_conversations` | /chat | medio |
| `flow_service` | pagos Flow (ELIMINADO - solo Paddle/Culqi) | medio |
| `commerce_service` | orders | medio |
| `payment_providers` | checkout | medio |
| `webhook_handler` | webhooks | ligero |
| `hash_utils` | hash calculation | ligero |

### Modulos que NUNCA hacer lazy:
- `os`, `sys`, `time`, `datetime`, `json`, `re`
- `fastapi`, `pydantic`
- `database` (get_db, init_db)
- `storage_config`

## Verificacion

Despues de cada cambio:
1. `python -c "import server"` - Verificar que importa sin errores
2. Verificar que los endpoints afectados siguen funcionando
3. Monitorear memoria en Render dashboard

## Plan de ejecucion

1. Eliminar modulos no utilizados (flow_service si no se usa)
2. Lazy import de `lectura` (pesado, solo 7 call sites en server.py)
3. Lazy import de `ai_service` + `ai_conversations`
4. Lazy import de `commerce_service` + `payment_providers` + `webhook_handler`
5. Verificar que init_db() no este sobrecargando el startup
