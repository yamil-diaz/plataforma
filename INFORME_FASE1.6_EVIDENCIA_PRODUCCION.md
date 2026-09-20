# INFORME FINAL DE AUDITORÍA FASE 1.6
# EXTRACCIÓN DE EVIDENCIA DE PRODUCCIÓN
# SOLO LECTURA — SIN MODIFICACIONES

Fecha: 2026-08-25
Fuente: diag_result.json (diagnóstico de producción existente) + análisis local

---

## A. RESUMEN

| Estado | Detalle |
|--------|---------|
| **Acceso a BD de producción** | **NO DISPONIBLE** — No hay `DATABASE_URL` configurado para producción |
| **Base de datos local (plataforma_dev)** | 4 libros de prueba (IDs 1-4) — **NO ES PRODUCCIÓN** |
| **Datos de producción disponibles** | Solo `diag_result.json` (diagnóstico previo) |
| **Libros objetivo** | 37 (35 duplicados + IDs 82, 145) |
| **Veredicto** | **NO LISTO PARA DISEÑAR FASE 2 — FALTA ACCESO A PRODUCCIÓN** |

---

## B. TABLA COMPLETA DE LOS 37 LIBROS (DATOS DE DIAG_RESULT.JSON)

### Grupo 1 — IDs 133-144 (12 títulos)

| ID | Título | Categoría | Placeholder | Páginas book_pages | PDF | Referencias |
|----|--------|-----------|-------------|-------------------|-----|-------------|
| 133 | Crimen y castigo | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 134 | Los heraldos negros | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 135 | Sangre de Campeón: Sin Cadenas | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 136 | Ciro Alegría El Mundo Es Ancho Y Ajeno | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 137 | CrimenCastigo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 138 | Microsoft Word - Dante Alighieri - Divina comedia.doc | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 139 | El Caballero Carmelo | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 140 | EL MUNDO ES ANCHO Y AJENO | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 141 | edipo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 142 | Romeo y Julieta | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 143 | ¡A CATITA | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 144 | La Odisea | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |

### Grupo 2 — IDs 147-157 (12 títulos, incluye ID 145 sospechoso)

| ID | Título | Categoría | Placeholder | Páginas book_pages | PDF | Referencias |
|----|--------|-----------|-------------|-------------------|-----|-------------|
| 147 | Los heraldos negros | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 148 | Sangre de Campeón: Sin Cadenas | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 149 | Ciro Alegría... | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 150 | CrimenCastigo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 151 | Microsoft Word - Dante... | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 152 | El Caballero Carmelo | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 153 | EL MUNDO ES ANCHO Y AJENO | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 154 | edipo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 155 | Romeo y Julieta | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 156 | ¡A CATITA | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 157 | La Odisea | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| **145** | **Memorias de subsuelo** | **E** | **NO (contenido corrupto)** | **NO DISPONIBLE** | **NO DISPONIBLE** | **NO DISPONIBLE** |

### Grupo 3 — IDs 159-170 (12 títulos)

| ID | Título | Categoría | Placeholder | Páginas book_pages | PDF | Referencias |
|----|--------|-----------|-------------|-------------------|-----|-------------|
| 159 | Crimen y castigo | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 160 | Los heraldos negros | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 161 | Sangre de Campeón... | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 162 | Ciro Alegría... | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 163 | CrimenCastigo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 164 | Microsoft Word - Dante... | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 165 | El Caballero Carmelo | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 166 | EL MUNDO ES ANCHO Y AJENO | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 167 | edipo.PDF | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 168 | Romeo y Julieta | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 169 | ¡A CATITA | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |
| 170 | La Odisea | D | SÍ (1) | 1 | NO DISPONIBLE | NO DISPONIBLE |

### Casos especiales

| ID | Título | Categoría | Detalles conocidos |
|----|--------|-----------|-------------------|
| **82** | Los 7 Hábitos de la Gente Altamente Efectiva | E | `books_suspicious_content`, múltiples `near_identical_content` |
| **145** | Memorias de subsuelo | E | `books_suspicious_content`, 534 ocurrencias de `�` en `repeated_paragraphs`, múltiples `near_identical_content` |

---

## C. LOS 12 GRUPOS DE DUPLICADOS

| Título | Grupo 1 (133-144) | Grupo 2 (147-157) | Grupo 3 (159-170) |
|--------|-------------------|-------------------|-------------------|
| Crimen y castigo | 133 | 147 | 159 |
| Los heraldos negros | 134 | 148 | 160 |
| Sangre de Campeón: Sin Cadenas | 135 | 149 | 161 |
| Ciro Alegría El Mundo Es Ancho Y Ajeno | 136 | 150 | 162 |
| CrimenCastigo.PDF | 137 | 151 | 163 |
| Microsoft Word - Dante Alighieri - Divina comedia.doc | 138 | 152 | 164 |
| El Caballero Carmelo | 139 | 153 | 165 |
| EL MUNDO ES ANCHO Y AJENO | 140 | 154 | 166 |
| edipo.PDF | 141 | 155 | 167 |
| Romeo y Julieta | 142 | 156 | 168 |
| ¡A CATITA | 143 | 157 | 169 |
| La Odisea | 144 | 158 | 170 |

### Evidencia de identidad exacta

| Métrica | Valor |
|---------|-------|
| `identical_book_content` | 35 libros, mismo contenido: `"Contenido de texto no disponible."` |
| `identical_pages_across_books` | 35 páginas, mismo contenido placeholder |
| `book_pages` count por libro | 1 página cada uno (page_ids 3813-3843, 3960-3970, 4032-4043) |
| `chapters` | 0 para todos (total producción = 0) |

### Comparación de contenido (desde diag)

| Grupo | LENGTH(content) | Hash content | Placeholder | Contenido real |
|-------|----------------|--------------|-------------|----------------|
| Todos (35) | **36 chars** | **Idéntico** | **SÍ (100%)** | **NO** |

**Conclusión:** Las 3 copias de cada título son **completamente idénticas** en `books.content` y `book_pages`. Diferencias solo en `id` (y presumiblemente `created_at`/`uploader_id` no disponibles en diag).

---

## D. REFERENCIAS FK (ESQUEMA CONFIRMADO)

### Tablas con FK a books.id (8 tablas)

| Tabla | FK | ON DELETE | Registros producción |
|-------|----|-----------|---------------------|
| book_pages | book_id | CASCADE | 4,043 |
| chapters | book_id | CASCADE | 0 |
| reading_progress | book_id | CASCADE | 7 |
| reading_sessions | book_id | CASCADE | 7 |
| reviews | book_id | CASCADE | 1 |
| book_interactions | book_id | CASCADE | 2 |
| reading_daily_pages | book_id | CASCADE | 67 |
| competitions | book_id | CASCADE | 0 |

### Referencias por book_id (LÍMITE DE DATOS)

**El diagnóstico `diag_result.json` NO incluye desglose de referencias por `book_id` individual.** Solo proporciona totales globales.

| book_id | Referencias confirmadas | EN_USO |
|---------|------------------------|--------|
| 133-144, 147-157, 159-170 | **NO DISPONIBLE** | **NO DETERMINABLE** |
| 82 | **NO DISPONIBLE** | **NO DETERMINABLE** |
| 145 | **NO DISPONIBLE** | **NO DETERMINABLE** |

**FALTA ACCESO A PRODUCCIÓN** para ejecutar:
```sql
SELECT 'book_pages' as tabla, book_id, COUNT(*) FROM book_pages WHERE book_id IN (...) GROUP BY book_id
UNION ALL SELECT 'reading_progress', book_id, COUNT(*) FROM reading_progress WHERE book_id IN (...) GROUP BY book_id
...
```

---

## E. created_at / uploader_id (COMPARACIÓN TEMPORAL)

| Dato | Disponibilidad en diag_result.json |
|------|-----------------------------------|
| `created_at` por book_id | **NO DISPONIBLE** |
| `updated_at` por book_id | **NO DISPONIBLE** |
| `uploader_id` por book_id | **NO DISPONIBLE** |

### Secuencialidad de IDs (única evidencia temporal disponible)

| Grupo | Rango IDs | Observación |
|-------|-----------|-------------|
| Grupo 1 | 133-144 | 12 IDs consecutivos perfectos |
| Grupo 2 | 147-158 | 12 IDs (salta 146, ID 145 incluido) |
| Grupo 3 | 159-170 | 12 IDs consecutivos perfectos |

**Sin `created_at` no se puede determinar si fueron creados el mismo día, en momentos diferentes, o cuál es el original.** La secuencialidad sugiere 3 cargas/importaciones separadas.

**FALTA ACCESO A PRODUCCIÓN** para:
```sql
SELECT id, title, created_at, uploader_id FROM books WHERE id IN (133,147,159, ...)
```

---

## F. pdf_path

| book_id | pdf_path | Disponibilidad |
|---------|----------|----------------|
| 133-144, 147-157, 159-170 | **NO DISPONIBLE EN DIAG** | **FALTA ACCESO A PRODUCCIÓN** |
| 82 | **NO DISPONIBLE EN DIAG** | **FALTA ACCESO A PRODUCCIÓN** |
| 145 | **NO DISPONIBLE EN DIAG** | **FALTA ACCESO A PRODUCCIÓN** |

El diagnóstico `diag_result.json` NO incluye la columna `pdf_path` (ni `isbn`, `description`, `cover_url`, etc.) por libro individual.

---

## G. ESTADO FÍSICO DE PDFs

| book_id | pdf_path | Existe | Tamaño | Tipo | Verificable |
|---------|----------|--------|--------|------|-------------|
| Todos (37) | NO DISPONIBLE | **NO VERIFICABLE** | — | — | **NO** |

**Entorno actual:** Solo lectura local. No hay conexión a almacenamiento persistente de Render (Persistent Disk) ni S3 de producción.

**PDF FÍSICO NO VERIFICABLE DESDE ESTE ENTORNO** para todos los 37 libros.

---

## H. page_count VS book_pages

| book_id | books.page_count | COUNT(book_pages) | Diferencia | Estado |
|---------|------------------|-------------------|------------|--------|
| 133-144, 147-157, 159-170 | **NO DISPONIBLE** | 1 (confirmado por diag) | **NO DETERMINABLE** | FALTA ACCESO |
| 82 | **NO DISPONIBLE** | **NO DISPONIBLE** | **NO DETERMINABLE** | FALTA ACCESO |
| 145 | **NO DISPONIBLE** | **NO DISPONIBLE** | **NO DETERMINABLE** | FALTA ACCESO |

El diagnóstico incluye totales globales (`row_counts`: books=163, book_pages=4043) pero NO por libro individual.

---

## I. ANÁLISIS ID 82 — "Los 7 Hábitos de la Gente Altamente Efectiva"

### Datos disponibles (diag_result.json)

| Atributo | Valor |
|----------|-------|
| ID | 82 |
| Título | Los 7 Hábitos de la Gente Altamente Efectiva |
| `books_suspicious_content` | **SÍ** |
| `near_identical_content` | Múltiples pares (595 totales en producción) |
| `repeated_paragraphs` | No aparece en listado (no está en top) |
| `identical_book_content` | **NO** (no es placeholder) |
| `books_published_status` | No individual |
| `page_count` | NO DISPONIBLE |
| `COUNT(book_pages)` | NO DISPONIBLE |
| `pdf_path` | NO DISPONIBLE |
| `uploader_id` | NO DISPONIBLE |
| `created_at` | NO DISPONIBLE |
| `content` real | NO DISPONIBLE |

### Clasificación: **NO DETERMINABLE**

**Evidencia:**
- Marcado como `suspicious_content` pero **NO es placeholder** (no está en `identical_book_content`)
- Aparece en múltiples pares `near_identical_content` → podría tener contenido real similar a otros libros, O contenido corrupto parcial
- Sin acceso a `content`, `page_count`, `pdf_path`, `book_pages`, `referencias` → **imposible evaluar recuperabilidad**

**Requiere:** `SELECT id, title, content, page_count, pdf_path, uploader_id, created_at FROM books WHERE id = 82` + consultas de referencias.

---

## J. ANÁLISIS ID 145 — "Memorias de subsuelo"

### Datos disponibles (diag_result.json)

| Atributo | Valor |
|----------|-------|
| ID | 145 |
| Título | Memorias de subsuelo |
| `books_suspicious_content` | **SÍ** |
| `repeated_paragraphs` | **SÍ** — 534 ocurrencias de `�` (U+FFFD, carácter de reemplazo Unicode) |
| `near_identical_content` | Múltiples pares |
| `identical_book_content` | **NO** (no es placeholder) |
| `page_count` | NO DISPONIBLE |
| `COUNT(book_pages)` | NO DISPONIBLE |
| `pdf_path` | NO DISPONIBLE |
| `chapters` | NO DISPONIBLE (total producción = 0) |

### Análisis del carácter `�` (U+FFFD)

- **Significado:** Carácter de reemplazo Unicode — **fallo de decodificación** (bytes inválidos en UTF-8)
- **534 ocurrencias** = corrupción masiva del texto
- **Causa probable:** PDF procesado con encoding incorrecto, o archivo binario tratado como texto

### Clasificación: **NO RECUPERABLE (desde contenido actual)**

**Evidencia:**
- El contenido en `books.content` está **corrupto irreversiblemente** (534 caracteres `�`)
- El carácter `�` no se puede "revertir" al texto original sin el PDF original
- 534 ocurrencias sugieren que **la mayor parte del texto es basura**
- **Requiere re-procesar el PDF original** (si existe en almacenamiento)

**Requiere:** Verificar `pdf_path` y existencia física del PDF en almacenamiento.

---

## K. CLASIFICACIÓN DE RECUPERABILIDAD

| book_id | Título | Clasificación | Justificación |
|---------|--------|---------------|---------------|
| 133-144, 147-157, 159-170 (35) | 12 títulos × 3 | **D — Placeholder / Duplicado** | Contenido = placeholder exacto, 1 página cada uno, idénticos entre copias |
| **82** | Los 7 Hábitos... | **NO DETERMINABLE** | `suspicious_content` pero no placeholder; sin acceso a content real |
| **145** | Memorias de subsuelo | **NO RECUPERABLE (actual)** | 534 `�` = corrupción masiva encoding; requiere PDF original |

---

## L. RIESGOS

| book_id | Riesgo | Justificación |
|---------|--------|---------------|
| 133-144, 147-157, 159-170 | **BAJO** | Placeholder, 0 referencias probables (totales globales bajos), duplicados exactos |
| **82** | **ALTO** | `suspicious_content`, posible uso real, desconocido |
| **145** | **CRÍTICO** | Contenido corrupto, `suspicious_content`, posible uso real |

**Nota:** Riesgos BAJO asumen 0 referencias en tablas FK (probable). **Requiere confirmación con consultas por book_id.**

---

## M. DATOS QUE TODAVÍA FALTAN

| Dato Crítico | Para Qué | Estado |
|--------------|----------|--------|
| `created_at` por book_id (37 IDs) | Determinar original vs duplicado temporal | **FALTA ACCESO A PRODUCCIÓN** |
| `pdf_path` por book_id (37 IDs) | Saber si PDF existe en almacenamiento | **FALTA ACCESO A PRODUCCIÓN** |
| `uploader_id` por book_id (37 IDs) | Identificar origen de carga | **FALTA ACCESO A PRODUCCIÓN** |
| Referencias FK por book_id (37 IDs × 8 tablas) | Confirmar 0 uso antes de eliminar | **FALTA ACCESO A PRODUCCIÓN** |
| `content` real de IDs 82, 145 | Evaluar recuperabilidad | **FALTA ACCESO A PRODUCCIÓN** |
| `page_count` por book_id (37 IDs) | Comparar con COUNT(book_pages) | **FALTA ACCESO A PRODUCCIÓN** |
| Verificación física PDFs (37 IDs) | Confirmar existencia en Render Disk/S3 | **FALTA ACCESO A ALMACENAMIENTO** |

---

## N. RECOMENDACIÓN PARA FASE 2

### Prerrequisitos INELUDIBLES

1. **Configurar `DATABASE_URL` de producción** (solo lectura) en el entorno
2. **Acceso a almacenamiento persistente de Render** (Persistent Disk) para verificar PDFs físicos
3. **Ejecutar las 37+ consultas SELECT** documentadas arriba

### Una vez obtenido acceso:

| Grupo | Acción FASE 2 (pendiente datos) |
|-------|--------------------------------|
| 35 duplicados (D) | 1. Identificar original por `created_at`/`uploader_id`<br>2. Confirmar 0 referencias<br>3. Decidir negocio: conservar 1 de 3 por título<br>4. Eliminar 23 duplicados con CASCADE<br>5. Re-subir PDF original para el conservado (si existe) |
| ID 82 | 1. Leer `content` real<br>2. Si contenido real + PDF → repaginar<br>3. Si placeholder → eliminar |
| ID 145 | 1. Verificar `pdf_path` y existencia física<br>2. Si PDF existe → re-procesar con encoding correcto<br>3. Si NO existe PDF → eliminar (contenido irrecuperable) |

---

## 13. CONDICIÓN PARA TERMINAR — VERIFICACIÓN

| Punto Crítico | Estado |
|---------------|--------|
| created_at (37 IDs) | **FALTA ACCESO A PRODUCCIÓN** |
| pdf_path (37 IDs) | **FALTA ACCESO A PRODUCCIÓN** |
| uploader_id (37 IDs) | **FALTA ACCESO A PRODUCCIÓN** |
| Referencias FK (37 IDs) | **FALTA ACCESO A PRODUCCIÓN** |
| content de 82/145 | **FALTA ACCESO A PRODUCCIÓN** |
| page_count (37 IDs) | **FALTA ACCESO A PRODUCCIÓN** |
| PDFs físicos (37 IDs) | **PDF FÍSICO NO VERIFICABLE DESDE ESTE ENTORNO** |

### Separación clara:

| Componente | Auditoría |
|------------|-----------|
| **BD (datos relacionales)** | **NO SUFICIENTEMENTE AUDITADA** — Faltan 7 consultas críticas por book_id |
| **PDF físico (archivos)** | **NO VERIFICABLE** — Sin acceso a almacenamiento de producción |

---

## 14. SEGURIDAD — CONFIRMACIÓN ABSOLUTA

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
| Migraciones | **NO** |
| Repaginación | **NO** |
| PDFs modificados | **NO** |
| Código modificado | **NO** |
| Commit | **NO** |
| Push | **NO** |
| Deploy | **NO** |

---

## VEREDICTO FINAL

```
NO LISTO — FALTA INFORMACIÓN CRÍTICA
```

### Detalle:

- **BD de producción:** **NO ACCESIBLE** — No hay `DATABASE_URL` configurado. El diagnóstico `diag_result.json` proporciona solo agregados y muestras, no los datos por libro necesarios para decidir reparación.
- **Almacenamiento PDFs:** **NO VERIFICABLE** — Sin acceso al Persistent Disk de Render ni S3.

### Próximo paso requerido:

**Proveer acceso de solo lectura a:**
1. `DATABASE_URL` de producción (PostgreSQL en Render)
2. Almacenamiento persistente (para `ls -la /var/data/aeternum/books/` o equivalente)

**Sin este acceso, NO es posible diseñar FASE 2 de forma segura.**