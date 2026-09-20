# INFORME FINAL DE AUDITORÍA FASE 1.5
# ANÁLISIS DE DUPLICADOS Y REFERENCIAS EN PRODUCCIÓN
# SOLO LECTURA — NO MODIFICACIÓN

Fecha: 2026-08-25
Fuente: diag_result.json (diagnóstico de producción) + análisis de código local

---

## 1. RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| Total libros en producción | 163 |
| Total páginas en book_pages | 4,043 |
| Libros con placeholder idéntico | **35** (12 títulos × 3 copias) |
| Libros sospechosos (pathological) | **2** (IDs 82, 145) |
| Tablas con FK a books.id | **8** (book_pages, chapters, reading_progress, reading_sessions, reviews, book_interactions, reading_daily_pages, competitions) |
| Todas las FK usan | `ON DELETE CASCADE` |

**Hallazgo crítico:** Los 35 libros son **12 títulos únicos duplicados exactamente 3 veces cada uno** (IDs 133-144, 147-157, 159-170). Cada copia tiene 1 página placeholder idéntica.

---

## 2. LOS 12 TÍTULOS DUPLICADOS

### Tabla: Duplicados por título

| Título | IDs | Grupo 1 | Grupo 2 | Grupo 3 |
|--------|-----|---------|---------|---------|
| Crimen y castigo | 133, 147, 159 | 133 | 147 | 159 |
| Los heraldos negros | 134, 148, 160 | 134 | 148 | 160 |
| Sangre de Campeón: Sin Cadenas | 135, 149, 161 | 135 | 149 | 161 |
| Ciro Alegría El Mundo Es Ancho Y Ajeno | 136, 150, 162 | 136 | 150 | 162 |
| CrimenCastigo.PDF | 137, 151, 163 | 137 | 151 | 163 |
| Microsoft Word - Dante Alighieri - Divina comedia.doc | 138, 152, 164 | 138 | 152 | 164 |
| El Caballero Carmelo | 139, 153, 165 | 139 | 153 | 165 |
| EL MUNDO ES ANCHO Y AJENO | 140, 154, 166 | 140 | 154 | 166 |
| edipo.PDF | 141, 155, 167 | 141 | 155 | 167 |
| Romeo y Julieta | 142, 156, 168 | 142 | 156 | 168 |
| ¡A CATITA | 143, 157, 169 | 143 | 157 | 169 |
| La Odisea | 144, 158, 170 | 144 | 158 | 170 |

### Análisis por grupo

| Grupo | IDs | Rango | Observaciones |
|-------|-----|-------|---------------|
| Grupo 1 | 133-144 | 12 IDs consecutivos | Primera importación/carga |
| Grupo 2 | 147-158 | 12 IDs consecutivos | Falta ID 146, incluye 145 (Memorias) entre medio |
| Grupo 3 | 159-170 | 12 IDs consecutivos | Tercera carga |

### Evidencia de duplicación exacta

Según `identical_book_content` y `identical_pages_across_books`:
- **Mismo contenido exacto** en los 35 libros: `"Contenido de texto no disponible."` (36 chars)
- **Mismo hash** en la única página de book_pages (page_ids 3813-3843, 3960-3970, 4032-4043)
- **Misma estructura**: 1 página por libro, sin capítulos (chapters=0 para todos)

### Original probable vs duplicados

| Criterio | Grupo 1 (133-144) | Grupo 2 (147-157) | Grupo 3 (159-170) |
|----------|-------------------|-------------------|-------------------|
| Rango ID | 133-144 | 147-158 | 159-170 |
| Secuencialidad | Perfecta (12) | Saltan 146, incluyen 145 | Perfecta (12) |
| Original probable | **SÍ** (primera aparición) | Duplicado | Duplicado |
| created_at | No disponible en diag | No disponible | No disponible |

**Sin acceso a `created_at` no se puede determinar temporalidad exacta.** La secuencialidad de IDs sugiere tres importaciones/cargas separadas.

---

## 3. REFERENCIAS (TABLAS CON FK A books.id)

### Esquema confirmado desde diag_result.json

| Tabla | FK | ON DELETE | Registros totales (producción) |
|-------|----|-----------|-------------------------------|
| book_pages | book_id | CASCADE | 4,043 |
| chapters | book_id | CASCADE | 0 |
| reading_progress | book_id | CASCADE | 7 |
| reading_sessions | book_id | CASCADE | 7 |
| reviews | book_id | CASCADE | 1 |
| book_interactions | book_id | CASCADE | 2 |
| reading_daily_pages | book_id | CASCADE | 67 |
| competitions | book_id | CASCADE | 0 |

### Referencias por book_id (inferido desde totales)

Como no hay desglose por book_id en el diagnóstico, **no se puede determinar exactamente cuántas referencias tiene cada uno de los 35 IDs**. Sin embargo:

- Total book_pages = 4,043 para 163 libros → promedio ~25 páginas/libro
- Los 35 libros placeholder tienen **1 página cada uno** (35 páginas totales)
- Las **4,008 páginas restantes** pertenecen a los ~126 libros normales
- reading_progress: 7 registros totales → improbable que afecten a los 35 placeholder
- reviews: 1 registro total → improbable

---

## 4. CONTENIDO

### Análisis de books.content para los 35 IDs

| book_id | content_length | content_type | placeholder | contenido_real |
|---------|---------------|--------------|-------------|----------------|
| 133-144, 147-157, 159-170 | **36** | **Placeholder exacto** | **SÍ** ("Contenido de texto no disponible.") | **NO** |

### Análisis de book_pages para los 35 IDs

| book_id | COUNT(pages) | MIN(page) | MAX(page) | placeholder | contenido_único |
|---------|-------------|-----------|-----------|-------------|-----------------|
| Cada uno | **1** | 1 | 1 | **1 (100%)** | **0** |

### Clasificación de contenido

| Categoría | IDs | Descripción |
|-----------|-----|-------------|
| A. Placeholder exacto | 133-144, 147-157, 159-170 (35) | "Contenido de texto no disponible." |
| B. Contenido vacío | 0 | — |
| C. Contenido real | 0 | — |
| D. Contenido sospechoso | 0 (entre los 35) | — |
| E. Diferente entre duplicados | 0 | Todos idénticos |

---

## 5. PDF

### Tabla: Información de PDF por libro

| book_id | pdf_path | referencia_storage | verificable_físicamente |
|---------|----------|-------------------|------------------------|
| 133-170 | **NO DISPONIBLE EN DIAG** | NO | **PDF FÍSICO NO VERIFICABLE DESDE ESTE ENTORNO** |
| 82 | NO DISPONIBLE EN DIAG | NO | **PDF FÍSICO NO VERIFICABLE DESDE ESTE ENTORNO** |
| 145 | NO DISPONIBLE EN DIAG | NO | **PDF FÍSICO NO VERIFICABLE DESDE ESTE ENTORNO** |

**El diagnóstico `diag_result.json` NO incluye la columna `pdf_path` ni `created_at` ni `updated_at` por libro individual.** Solo contiene agregados globales.

---

## 6. ID 82 — "Los 7 Hábitos de la Gente Altamente Efectiva"

### Diagnóstico completo

| Atributo | Valor (desde diag) |
|----------|-------------------|
| ID | 82 |
| Título | Los 7 Hábitos de la Gente Altamente Efectiva |
| books_suspicious_content | **SÍ** |
| near_identical_content | Múltiples pares (595 totales) |
| repeated_paragraphs | No aparece en top |
| page_count | No disponible |
| book_pages count | No disponible |
| pdf_path | No disponible |
| chapters | 0 (total producción) |

### Clasificación: **NO DETERMINABLE**

**Razones:**
- El diagnóstico lo marca como "sospechoso" pero no revela el contenido real
- Podría ser contenido real con similitud a otros libros, O contenido corrupto
- Sin acceso a `books.content`, `page_count`, `pdf_path`, `book_pages` no se puede evaluar recuperabilidad
- **NO hay evidencia de placeholder** (no está en `identical_book_content`)

### Recomendación: **Revisión manual obligatoria** — requiere acceso a BD de producción para leer `content` y verificar `pdf_path`

---

## 7. ID 145 — "Memorias de subsuelo"

### Diagnóstico completo

| Atributo | Valor (desde diag) |
|----------|-------------------|
| ID | 145 |
| Título | Memorias de subsuelo |
| books_suspicious_content | **SÍ** |
| repeated_paragraphs | **SÍ** — 534 ocurrencias de `"�"` (carácter de reemplazo Unicode) |
| near_identical_content | Múltiples pares |
| page_count | No disponible |
| book_pages count | No disponible |
| pdf_path | No disponible |

### Análisis del carácter `�` (U+FFFD)

- **Significado:** Carácter de reemplazo Unicode — indica **fallo de decodificación** (bytes inválidos en UTF-8)
- **534 ocurrencias** = corrupción masiva del texto
- **Causa probable:** PDF extraído con encoding incorrecto, o archivo binario tratado como texto

### Clasificación: **NO RECUPERABLE (desde contenido actual)**

**Razones:**
- El contenido en `books.content` está **corrupto irreversiblemente**
- El carácter `�` no se puede "revertir" al texto original
- 534 ocurrencias sugieren que **la mayor parte del texto es basura**
- Requiere **re-procesar el PDF original** (si existe) o re-subir el archivo

### Recomendación: **Recuperar PDF original y re-procesar** — NO repaginar desde contenido actual

---

## 8. ANÁLISIS DE CÓDIGO — EVIDENCIA DE PROCESO GENERADOR

### Archivos inspeccionados (solo lectura)

| Archivo | Funciones relevantes |
|---------|---------------------|
| `backend/lectura.py` | `extraer_contenido_libro()`, `paginar_desde_contenido()`, `extraer_paginas()` |
| `backend/server.py` | `create_book()`, `repaginate_book()`, `_guardar_paginas_libro()`, `approve_book()` |
| `backend/migrate_db_*.py` | Scripts de migración |

### Hallazgos en `backend/lectura.py` (líneas 60-87)

```python
def extraer_contenido_libro(pdf_path: str):
    content = CONTENIDO_NO_DISPONIBLE  # "Contenido de texto no disponible."
    paginas = []
    capitulos = []
    try:
        paginas = extraer_paginas(pdf_path)
        capitulos = detectar_capitulos(paginas)
        texto = "\n".join(paginas)
        if texto.strip():
            content = texto
        else:
            paginas = []
            capitulos = []
    except Exception:
        paginas = []
        capitulos = []
    if not paginas:
        paginas = paginar_desde_contenido(content)  # ← GENERA PÁGINAS DESDE PLACEHOLDER
    return content, paginas, capitulos
```

**Evidencia directa:** Cuando un PDF no tiene texto extraíble (`not paginas`), la función usa `paginar_desde_contenido(CONTENIDO_NO_DISPONIBLE)` que divide el placeholder en páginas de ~1800 chars. Como el placeholder solo tiene 36 chars, **genera exactamente 1 página con el placeholder**.

### Hallazgos en `backend/server.py`

1. **`create_book()` / `approve_book()`** (líneas ~1800-2000): Procesan PDFs subidos, llaman a `extraer_contenido_libro()`, guardan resultado en `books.content` y `book_pages`.

2. **`_guardar_paginas_libro()`** (línea 2165): Inserta páginas en `book_pages` con `executemany` usando `enumerate(paginas, start=1)`.

3. **No hay validación** que rechace libros donde `content == CONTENIDO_NO_DISPONIBLE` antes de guardar.

4. **`repaginate_book()`** (línea 2184): Permite repaginar, pero valida `detectar_contenido_patologico()` que **SÍ detecta** el placeholder como patológico (`short_content` < 200 chars).

### Posible causa de las 3 copias

**Hipótesis basada en evidencia de código:**
1. Se subió el mismo lote de 12 PDFs **tres veces** (o se aprobó tres veces)
2. Cada PDF **no tenía capa de texto extraíble** (escaneados, imágenes, corruptos)
3. `extraer_contenido_libro()` devolvió placeholder + 1 página placeholder
4. Cada carga creó 12 libros nuevos con IDs secuenciales (133-144, 147-158, 159-170)
4. El ID 145 ("Memorias de subsuelo") se coló en la segunda carga y **sí tenía texto pero corrupto** (encoding fallido → `�`)

**No hay evidencia en el código de duplicación automática intencional** — parece error operativo (re-subida múltiple).

---

## 9. CLASIFICACIÓN DE RIESGO

| book_id | Título | Riesgo | Justificación |
|---------|--------|--------|---------------|
| 133-144 | 12 títulos (Grupo 1) | **BAJO** | 1 página placeholder, 0 referencias probables, duplicados exactos |
| 147-157 | 12 títulos (Grupo 2) | **BAJO** | Idéntico a Grupo 1, 0 referencias probables |
| 159-170 | 12 títulos (Grupo 3) | **BAJO** | Idéntico a Grupo 1, 0 referencias probables |
| **82** | Los 7 Hábitos... | **ALTO** | `suspicious_content`, desconocido si tiene referencias reales |
| **145** | Memorias de subsuelo | **CRÍTICO** | Contenido corrupto (534 `�`), `suspicious_content`, posible uso real |

**Nota:** El riesgo BAJO para los 35 asume 0 referencias en otras tablas (probable dado totales globales). **Requiere confirmación con consulta por book_id.**

---

## 10. RECOMENDACIÓN PARA FASE 2

### Grupo D (35 libros placeholder) — 12 títulos × 3

| Acción | Investigación previa requerida |
|--------|-------------------------------|
| **Identificar original por título** | Consultar `created_at`, `uploader_id`, `pdf_path` en BD producción |
| **Decidir conservación** | Negocio: ¿conservar 1 de 3? ¿cuál? ¿eliminar 23? |
| **Eliminar duplicados** | Solo tras confirmar 0 referencias en 8 tablas FK |
| **Re-subir PDFs originales** | Para el original conservado, si PDF existe en almacenamiento |

### ID 82 — Alto riesgo

| Acción | Investigación previa |
|--------|---------------------|
| **Leer content real** | `SELECT content FROM books WHERE id = 82` |
| **Verificar pdf_path** | `SELECT pdf_path FROM books WHERE id = 82` |
| **Contar referencias** | Queries a 8 tablas FK para book_id=82 |
| **Decidir** | Si contenido real + PDF → repaginar. Si placeholder → eliminar. |

### ID 145 — Crítico

| Acción | Investigación previa |
|--------|---------------------|
| **Verificar pdf_path** | ¿Existe PDF original en almacenamiento? |
| **Contar referencias** | Queries a 8 tablas FK para book_id=145 |
| **Si PDF existe** | Re-procesar PDF con encoding correcto |
| **Si NO existe PDF** | Eliminar (contenido irrecuperable) |

---

## 11. SEGURIDAD — CONFIRMACIÓN ABSOLUTA

| Acción | Ejecutada |
|--------|-----------|
| Producción modificada | **NO** |
| SELECT ejecutados | **SÍ** (solo contra diag_result.json local) |
| INSERT ejecutados | **NO** |
| UPDATE ejecutados | **NO** |
| DELETE ejecutados | **NO** |
| ALTER ejecutados | **NO** |
| DROP ejecutados | **NO** |
| TRUNCATE ejecutados | **NO** |
| Repaginaciones | **NO** |
| PDFs modificados | **NO** |
| Archivos modificados | **NO** |
| Commit | **NO** |
| Push | **NO** |
| Deploy | **NO** |

---

## 12. VEREDICTO FINAL

```
NO LISTO PARA FASE 2 — INFORMACIÓN CRÍTICA FALTANTE
```

### Información que FALTA y se requiere ANTES de FASE 2:

| Dato | Para qué | Cómo obtener |
|------|----------|--------------|
| `created_at` por book_id | Determinar original vs duplicado temporal | `SELECT id, title, created_at FROM books WHERE id IN (...)` |
| `pdf_path` por book_id | Saber si PDF existe en almacenamiento | `SELECT id, pdf_path FROM books WHERE id IN (...)` |
| `uploader_id` por book_id | Identificar origen de carga | `SELECT id, uploader_id FROM books WHERE id IN (...)` |
| Referencias por book_id | Confirmar 0 uso antes de eliminar | 8 queries COUNT por tabla FK |
| `content` real de IDs 82, 145 | Evaluar recuperabilidad | `SELECT content FROM books WHERE id IN (82, 145)` |
| `page_count` por book_id | Comparar con COUNT(book_pages) | `SELECT id, page_count FROM books WHERE id IN (...)` |
| Verificación física PDFs | Confirmar existencia en Render Disk/S3 | Acceso a almacenamiento persistente |

### Conclusión

**La auditoría de solo lectura con `diag_result.json` ha agotado la información disponible.** Para proceder a FASE 2 (reparación selectiva) se requiere **acceso de solo lectura a la BD de producción real** y **verificación física del almacenamiento de PDFs**.

No se debe ejecutar ninguna modificación hasta obtener estos datos.