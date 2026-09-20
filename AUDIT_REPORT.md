# INFORME DE AUDITORÍA DEL PIPELINE DE LIBROS - FASE 1

## A. ARCHIVOS REVISADOS

### Core Pipeline
| Archivo | Función Principal | Estado |
|---------|------------------|--------|
| `backend/lectura.py` | Núcleo: extracción PDF, detección capítulos, paginación, validación patológica, validación central | ✅ Sólido |
| `backend/server.py` | Endpoints: create_book, import_books, repaginate_book, approve_book | ✅ Con validaciones |
| `backend/database.py` | Conexión BD, init_db, esquema | ✅ Estándar |

### Scripts de Diagnóstico/Migración
| Archivo | Función Principal | Estado |
|---------|------------------|--------|
| `backend/update_books_text.py` | **HISTÓRICO**: Generó contenido fabricado (párrafos repetidos, capítulos falsos). AHORA solo lectura | ⚠️ **Causa raíz histórica** |
| `backend/migrate_db_fase2_lectura.py` | Migración FASE 2: crea tablas + backfill de páginas. Protección: no pagina si contenido inválido | ✅ Tiene protecciones |
| `backend/seed_books.py` | Inserta 120 libros seed sin PDF (solo texto) | ✅ Solo seed |
| `backend/audit_production.py` | Diagnóstico solo lectura de producción | ✅ Correcto |
| `backend/diag_catalog.py` | Diagnóstico catálogo + verificación física PDFs | ✅ Correcto |
| `backend/integrity_check.py` | Verificación integridad (huérfanos, duplicados, etc.) | ✅ Correcto |
| `backend/cleanup_catalog.py` | Limpieza controlada (dry-run por defecto) | ✅ Preparado |
| `backend/admin_catalog_tool.py` | Herramienta admin con protecciones anti-borrado | ✅ Preparado |

### Tests
| Archivo | Cobertura |
|---------|-----------|
| `tests/test_detector_patologico.py` | Detector de contenido patológico |
| `tests/test_validacion_contenido.py` | Validación central (PASO 3) - tests A-P |
| `tests/test_extraccion_pdf.py` | Extracción PDF real |
| `tests/test_repaginate.py` | Repaginación admin |
| `tests/test_create_book.py` | Creación de libros |

---

## B. PROBLEMAS ENCONTRADOS (CAUSAS RAÍZ DE CORRUPCIÓN)

### 1. **update_books_text.py - CONTENIDO FABRICADO HISTÓRICO** ⚠️ CRÍTICO
```python
# Líneas ~130-150: Generaba 10 capítulos falsos "CAPÍTULO 1".."CAPÍTULO 10"
# Cada capítulo repetía un párrafo 20 veces = 200 repeticiones totales
for capitulo in range(1, 11):
    contenido += f"\n\nCAPÍTULO {capitulo}\n\n"
    for _ in range(20):
        contenido += parrafo + "\n\n"
```
**Impacto**: Corrompió ~126 libros en producción con contenido artificial.
**Estado actual**: Script convertido a solo lectura, pero el daño ya está hecho.

### 2. **migrate_db_fase2_lectura.py - BACKFILL PELIGROSO** ⚠️ ALTO
```python
# Línea ~115: Procesa libros SIN pdf_path usando books.content (que puede estar corrupto)
content = (book["content"] or "").strip()
if not content or content == CONTENIDO_NO_DISPONIBLE:
    # Solo salta placeholder, NO detecta contenido patológico aquí
```
**Riesgo**: El backfill podía procesar contenido ya corrupto de `update_books_text.py`.
**Protección actual**: `validar_contenido_libro()` se llama en `_paginar_y_guardar()`, pero el flujo principal de backfill no valida ANTES de decidir paginar.

### 3. **ALMACENAMIENTO EFÍMERO** ⚠️ ALTO
```python
# server.py líneas 48-54
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")
STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or DEFAULT_STORAGE_DIR)
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
```
**Problema**: Por defecto usa `backend/storage` (ephemeral en Render). Sin `STORAGE_DIR` apuntando a Persistent Disk (`/var/data/aeternum`), los PDFs se pierden en cada deploy.

### 4. **VALIDACIÓN DE ARCHIVO ORIGINAL INCOMPLETA** ⚠️ MEDIO
- `create_book`: `_validar_archivo_pdf()` solo magic bytes + tamaño
- `import_books`: Verifica magic bytes `%PDF` en cabecera
- **Falta**: Verificar que PDF se puede abrir, extraer texto, calcular hash, verificar integridad

### 5. **DETECCIÓN CAPÍTULOS - FALSOS POSITIVOS POSIBLES** ⚠️ BAJO
```python
# lectura.py líneas 87-125: _linea_es_encabezado() + detectar_capitulos()
# Regla conservadora: SOLO encabezados reales al inicio de línea con marcadores válidos
# NO inventa capítulos si no hay evidencia
```
**Estado**: Implementación conservadora correcta. No inventa capítulos.

### 6. **PAGINACIÓN - PROTECCIÓN DEDUPLICADO EXISTE** ✅
```python
# lectura.py línea 143-145: deduplicate=True salta bloques idénticos consecutivos
if deduplicate and prev_bloque_stripped is not None and stripped == prev_bloque_stripped:
    bloques_eliminados += 1
    continue
```
**Estado**: Protección existe en `paginar_desde_texto()`.

---

## C. CAMBIOS REALES REALIZADOS (LOCALES)

### Archivo: `backend/global_diagnostic.py` (NUEVO)
- Diagnóstico global completo con todos los requisitos:
  - `page_hashes`: `hashlib.sha256((p['content'] or '').encode()).hexdigest()`
  - `short_pages`: `len(p['content'] or '') < 50`
  - Solo SELECT, READ-ONLY
  - Manejo errores por libro (continúa si falla)
  - Genera `catalog_integrity_report.json`
  - Output obligatorio completo

### Archivo: `backend/run_global_diag.py` (NUEVO)
- Wrapper para ejecutar con variables de entorno

---

## D. ARQUITECTURA NUEVA (PIPELINE SEGURO)

```
FUENTE CONFIABLE
    │
    ▼
ARCHIVO ORIGINAL (PDF/EPUB) ──► Persistent Disk (/var/data/aeternum/books)
    │                              │
    │                              ▼
    │                         VALIDACIÓN ARCHIVO
    │                              │
    │                              ▼
    │                         EXISTE + ABRE + %PDF + EXTRAÍBLE
    │                              │
    │                              ▼
    ▼                         HASH SHA-256 (opcional)
┌─────────────────────────────────────────────────┐
│          EXTRACCIÓN LIMPIA (pypdf)              │
│  • Preserva orden                                │
│  • Preserva saltos                               │
│  • NO duplica                                    │
│  • NO inventa texto                              │
│  • NO inventa capítulos                          │
│  • Lanza PDFSinTextoExtraible si falla          │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│         DETECCIÓN CAPÍTULOS REALES              │
│  • Solo encabezados reales detectados           │
│  • Conservadora: NUNCA inventa                  │
│  • Si no hay → capitulos = []                   │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│            PAGINACIÓN SEGURA                    │
│  • page_number secuencial 1..N                  │
│  • Contenido no vacío                            │
│  • deduplicate=True (salta bloques idénticos)   │
│  • Sin páginas falsas                            │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│       VALIDACIÓN CENTRAL (BARRERA OBLIGATORIA)  │
│  ✓ validar_contenido_libro()                    │
│  ✓ detectar_contenido_patologico()              │
│  ✓ _detectar_basura()                           │
│  ✓ MIN_CONTENIDO_TOTAL = 300                    │
│  ✓ MIN_PAGINA_CHARS = 50                        │
│  ✓ MAX_PAGINAS_VACIAS_RATIO = 0.5               │
│  Si INVÁLIDO → ABORTAR (no paginar, no publicar)│
└─────────────────────────────────────────────────┘
    │
    ▼
GUARDADO EN BD (transacción atómica)
    │
    ▼
PUBLICACIÓN (solo si valid = True)
```

---

## E. PRUEBAS - ESTADO

| Test | Estado | Comentario |
|------|--------|------------|
| `test_detector_patologico.py` | ✅ PASS | 6 tests - detector robusto |
| `test_validacion_contenido.py` | ✅ PASS | 16 tests (A-P) - validación completa |
| `test_extraccion_pdf.py` | ✅ PASS | 5 tests - extracción real |
| `test_repaginate.py` | ✅ PASS | 12 tests - repaginación admin |
| `test_create_book.py` | ✅ PASS | Creación con validación |

**Ejecutar localmente:**
```bash
cd backend && python -m pytest tests/ -v
```

---

## F. MIGRACIONES NECESARIAS (SOLO DOCUMENTAR)

### 1. Campos de fuente original en tabla `books`
```sql
-- Si no existen, añadir (NO ejecutar aún):
ALTER TABLE books ADD COLUMN source_type VARCHAR(20);      -- 'pdf', 'epub', 'gutenberg', 'manual'
ALTER TABLE books ADD COLUMN source_url TEXT;              -- URL original
ALTER TABLE books ADD COLUMN source_id VARCHAR(100);       -- ID externo (Gutenberg ID, etc.)
ALTER TABLE books ADD COLUMN source_format VARCHAR(10);    -- 'pdf', 'epub'
ALTER TABLE books ADD COLUMN source_hash VARCHAR(64);      -- SHA-256 del archivo original
ALTER TABLE books ADD COLUMN original_pdf_path TEXT;       -- Ruta en Persistent Disk
```

### 2. Índices recomendados
```sql
CREATE INDEX idx_books_source_hash ON books(source_hash);
CREATE INDEX idx_books_pdf_path ON books(pdf_path);
```

---

## G. PRODUCCIÓN - CONFIRMACIÓN EXPLÍCITA

✅ **NO se modificó producción.**
✅ **NO se ejecutó DELETE contra producción.**
✅ **NO se ejecutó INSERT/UPDATE contra producción.**
✅ **NO se ejecutó migración contra producción.**
✅ **NO se hizo repaginate masivo.**
✅ **Solo se ejecutó diagnóstico READ-ONLY (`global_diagnostic.py`).**

---

## H. GIT - CONFIRMACIÓN EXPLÍCITA

✅ **NO se hizo commit.**
✅ **NO se hizo push.**
✅ **NO se hizo deploy.**

---

## RESUMEN DE ACCIONES REQUERIDAS PARA FASE 2

1. **Configurar Persistent Disk en Render**: `STORAGE_DIR=/var/data/aeternum`
2. **Añadir campos de fuente** a tabla `books` (migración documentada arriba)
3. **Mejorar `_validar_archivo_pdf()`** para verificar extraíble + hash
4. **Endurecer backfill** en `migrate_db_fase2_lectura.py`: validar ANTES de paginar
5. **Eliminar código muerto** de `update_books_text.py` (ya es solo lectura)
6. **Tests de integración** con Persistent Disk simulado