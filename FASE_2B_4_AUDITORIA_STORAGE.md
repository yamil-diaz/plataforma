# FASE 2B-4 — RESULTADO

## 1. STORAGE ACTUAL

* **ruta correcta:** `/var/data/aeternum` (configurada vía variable de entorno `STORAGE_DIR` en Render)
* **rutas antiguas detectadas:**
  - `backend/storage` (DEFAULT_STORAGE_DIR en `server.py:49`)
  - `/opt/render/project/src/backend/storage` (hardcodeada en scripts de test y migración)
* **riesgo:** El código usa `DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")` como fallback si no existe `STORAGE_DIR`. En producción (Render), la variable `STORAGE_DIR=/var/data/aeternum` está inyectada, pero si falla el despliegue o la variable no se propaga, el sistema escribiría en `backend/storage` (efímero).

---

## 2. SUBIDA DE PDF

* **archivo:** `backend/server.py`
* **función:** `create_book` (línea ~2109)
* **endpoint:** `POST /api/books`
* **directorio final:** `STORAGE_BOOKS` = `{STORAGE_DIR}/books` (línea 54)
* **nombre final:** `{uuid.uuid4()}_{original_filename}` (línea 2140)
* **cómo se genera el UUID:** `uuid.uuid4()` estándar (línea 2140)
* **cómo se almacena `pdf_path`:** Ruta absoluta completa del archivo guardado (línea 2190: `pdf_path` en INSERT)

---

## 3. PORTADAS

* **archivo:** `backend/server.py`
* **función:** `create_book` (líneas 2169-2174) y `update_book` (líneas 1961-1970)
* **directorio:** `STORAGE_COVERS` = `{STORAGE_DIR}/covers` (línea 55)
* **nombre final:** `{uuid.uuid4().hex}.{ext}` (línea 1965 / 2170)
* **cómo se almacena la referencia:** URL relativa `/static/covers/{filename}` en columna `cover_image_url` (líneas 1970, 2174)

---

## 4. DESCARGA

* **endpoint:** `GET /api/books/{book_id}/download` (línea 2008)
* **fuente del PDF:**
  1. Primero intenta resolver `pdf_path` de la BD con `_resolver_pdf_path()` (línea 2021)
  2. Si existe archivo físico → `FileResponse` directo (líneas 2022-2027)
  3. Si NO existe → genera PDF on-the-fly desde `books.content` con fpdf2 (líneas 2029-2042)
* **resultado:** **SIEMPRE funciona** — si el PDF físico desaparece, se regenera desde el contenido textual. El `pdf_path` en BD puede apuntar a ruta antigua; `_resolver_pdf_path` (líneas 156-171) intenta: ruta absoluta → nombre en `STORAGE_BOOKS` → None.

---

## 5. LECTOR

* **fuente:** `book_pages` tabla (páginas pre-extraídas) — **NO** `books.content` ni PDF físico
* **endpoint:** `GET /api/books/{book_id}/pages/{page}` (línea 2949)
* **resultado:** El lector paginado (FASE 2) obtiene contenido exclusivamente de `book_pages.content` por página. Si el libro no tiene paginación (`page_count=0` o `book_pages` vacío), el frontend muestra "Libro sin paginación". El PDF físico **no** se usa para lectura.

---

## 6. IMPORTACIÓN

* **flujo:** `POST /api/books/import` (línea 2386) → `process_bulk_zip` (línea 2241)
* **riesgos detectados:**
  1. **Validación estricta:** El pipeline central `lectura.procesar_contenido_para_publicacion` valida archivo (magic bytes %PDF), extracción, detección de capítulos, y validación de contenido (patológico, basura, insuficiente). Un PDF que falle **no se publica** (líneas 2280-2299).
  2. **Duplicados:** Se verifica por hash SHA-256 del PDF **y** por título+autor normalizado antes de insertar (líneas 2322-2328).
  3. **Portadas:** Se buscan imágenes con mismo basename que el PDF en el ZIP (líneas 2335-2342).
  4. **Limpieza:** Al final se borra el ZIP temporal y el directorio de extracción (líneas 2369-2373).
  5. **Riesgo residual:** Si `STORAGE_DIR` no está configurado en el worker de background tasks, los archivos irían a `backend/storage` (efímero). En Render, la variable de entorno es global al servicio.
* **resultado:** Flujo robusto con validación central, anti-duplicados, y limpieza de temporales.

---

## 7. LOS 4 ARCHIVOS DEL DISK

| Archivo | Tipo | Tamaño | ¿PDF válido? | Posible origen | Acción |
| ------- | ---: | -----: | ------------ | -------------- | ------ |
| `/var/data/aeternum/books/4400ba09-c36c-42bc-b5b8-1037fc520e7c_91.pdf` | PDF | ~desconocido | Probable (nombre con UUID + número) | Libro subido por usuario o importación | **Conservar** — verificar hash contra BD cuando haya libros |
| `/var/data/aeternum/books/80ad2a2e-e7a5-44e5-b76c-cd570cada258_84.pdf` | PDF | ~desconocido | Probable (nombre con UUID + número) | Libro subido por usuario o importación | **Conservar** — verificar hash contra BD cuando haya libros |
| `/var/data/aeternum/books/94959e31-ce67-4054-8494-659cb843fec4_rayuelas mentales.pdf` | PDF | ~desconocido | Probable (nombre con UUID + título) | Importación ZIP o subida con nombre original | **Conservar** — verificar hash contra BD cuando haya libros |
| `/var/data/aeternum/covers/66627525-21b0-48f6-8ef0-05ef72d509bc_imagen_2026-08-18_193231941.png` | PNG | ~desconocido | N/A (imagen) | Portada subida por usuario | **Conservar** — verificar referencia en `cover_image_url` cuando haya libros |

> **Nota:** No se pueden ejecutar `file`, `pdfinfo`, `sha256sum` en este entorno Windows local. En Render (Linux), ejecutar:
> ```bash
> file /var/data/aeternum/books/*
> sha256sum /var/data/aeternum/books/*
> ```

---

## 8. RIESGOS DETECTADOS

### CRÍTICO
1. **`STORAGE_DIR` sin validación de arranque** — En `server.py:53`, si la variable de entorno no existe en Render (fallo de configuración, nuevo deploy sin variable), el sistema usa `backend/storage` (efímero). **No hay assert/log de alerta al arrancar.**

### ALTO
2. **Migración legacy automática al arranque** — `_migrar_storage_legacy()` (líneas 66-90) copia archivos de `backend/storage/*` a `STORAGE_DIR` en **cada inicio**. Si `STORAGE_DIR` apunta a disco persistente pero el directorio legacy tiene archivos nuevos (subidos durante un deploy fallido), se copian. **No borra origen** (correcto), pero puede duplicar almacenamiento.
3. **`_resolver_pdf_path` permite rutas rotas** — Si `pdf_path` en BD es ruta absoluta antigua (`/opt/render/...`) y el archivo no existe en `STORAGE_BOOKS`, devuelve `None`. La descarga cae a generación on-the-fly (OK), pero el lector **no** usa PDF físico.

### MEDIO
4. **Background tasks (importación ZIP) heredan `STORAGE_DIR` del proceso principal** — En Render, las background tasks corren en el mismo proceso, así que la variable está disponible. Si se migra a worker separado (RQ/Celery), habría que propagar la variable.
5. **Covers: directorio `STORAGE_COVERS` creado al arranque** (línea 62) pero **no verificado** que sea persistente. Igual riesgo que `STORAGE_BOOKS`.
6. **`admin_catalog_tool.py`, `cleanup_catalog.py`, `diag_catalog.py` definen sus propias `STORAGE_DIR`/`STORAGE_BOOKS`** (líneas 41-43, 36-37, 43-44) — duplican lógica; si cambian, divergen.

### BAJO
7. **Rutas hardcodeadas en tests/scripts** — `/opt/render/project/src/backend/storage` aparece en `phase1_verify.py:95`, `verify_phase1.py:88`, `test_storage_persistente.py:41`. Solo afecta tests, no producción.
8. **`TEMP_DIR` bajo `STORAGE_DIR`** (línea 57) — correcto, usa disco persistente para extracciones ZIP temporales.

---

## 9. RECOMENDACIÓN

**ANTES de volver a cargar libros, corregir:**

1. **Añadir validación estricta al arranque** en `server.py` (tras línea 63):
   ```python
   if not os.getenv("STORAGE_DIR"):
       import logging
       logging.warning("STORAGE_DIR no configurado: usando almacenamiento EFÍMERO (backend/storage). "
                       "Configura STORAGE_DIR=/var/data/aeternum en Render.")
   ```
   Mejor: **fallar rápido** si `IS_PRODUCTION` y no hay `STORAGE_DIR`:
   ```python
   if IS_PRODUCTION and not os.getenv("STORAGE_DIR"):
       raise RuntimeError("STORAGE_DIR obligatorio en producción")
   ```

2. **Centralizar constantes de storage** — Mover `STORAGE_DIR`, `STORAGE_BOOKS`, `STORAGE_COVERS`, `TEMP_DIR` a `database.py` o módulo `storage.py` e importar en `server.py`, `admin_catalog_tool.py`, `cleanup_catalog.py`, `diag_catalog.py`.

3. **Documentar en `render.yaml`** (crear si no existe) la variable `STORAGE_DIR=/var/data/aeternum` obligatoria.

4. **Verificar los 4 archivos existentes** en Render con `sha256sum` y cruzar con `rayos_transactions.book_id` (10 transacciones) para identificar a qué libros pertenecen antes de recrear registros en `books`.

---

## 10. VEREDICTO

**STORAGE NECESITA CORRECCIONES ANTES DE RECONSTRUIR**

---

## ARCHIVOS A MODIFICAR EN FUTURA FASE (NO MODIFICAR AHORA)

1. `backend/server.py` — añadir validación de `STORAGE_DIR` al arranque (línea ~63)
2. `backend/server.py` — considerar extraer constantes de storage a módulo compartido
3. `backend/render.yaml` — **crear** con variable `STORAGE_DIR=/var/data/aeternum` obligatoria
4. `backend/admin_catalog_tool.py` — importar constantes centralizadas (líneas 41-43)
5. `backend/cleanup_catalog.py` — importar constantes centralizadas (líneas 36-37)
6. `backend/diag_catalog.py` — importar constantes centralizadas (líneas 43-44)