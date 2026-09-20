---
name: agregar-libro
description: Flujo completo para agregar un libro al catalogo de AeternumLibrary - upload PDF, cover, metadata, validacion y importacion masiva
---

## Agregar un libro al catalogo

### Via Admin UI (libro individual)

1. Ir a `/admin/books/new`
2. Completar formulario: titulo, autor, categoria, descripcion, contenido (texto pegado o PDF upload)
3. Subir portada (cover) - formato imagen
4. El backend valida:
   - Titulo y autor no vacios
   - Contenido minimo suficiente
   - Deteccion de contenido patologico (texto repetido/fabricado)
   - Ratio de paginas vacias limitado
5. PDF se procesa con `pypdf` para extraer texto
6. Se aplica deduplicacion: SHA-256 hash del PDF + normalizacion titulo/autor
7. Se guarda en PostgreSQL y archivos en storage

### Via Admin UI (importacion masiva ZIP)

1. Ir a `/admin/import`
2. Subir ZIP con archivos PDF
3. Opcionalmente subir portadas en el ZIP (mismo nombre que el PDF)
4. `import_masiva.py` procesa cada PDF:
   - Extrae contenido con pypdf
   - Busca cover candidates por nombre
   - Aplica deduplicacion
   - Crea registros en batch

### Via Admin UI (importacion Gutenberg)

1. Ir a `/admin/gutenberg`
2. Seleccionar libros del catalogo de Project Gutenberg
3. `import_gutenberg_batch.py` descarga y procesa automaticamente
4. Los libros se marcan como `is_gutenberg=True`

### Codigo relevante

- Endpoint: `POST /api/admin/books` en `backend/server.py`
- Importador ZIP: `backend/import_masiva.py`
- Importador Gutenberg: `backend/import_gutenberg_batch.py`
- Extraccion PDF: `backend/lectura.py`
- Deduplicacion: en `backend/database.py` (unique index + fallback)
- Validacion de contenido: en `backend/server.py` (pathological content detection)

### Categorias disponibles

- Fiction
- Classics
- Science
- Business

### Notas importantes

- Los libros de Gutenberg son de dominio publico
- El storage en produccion es un persistent disk en Render (`/var/data/aeternum`)
- Los covers se guardan en `storage/covers/`
- Los PDFs se guardan en `storage/books/`
- Usar `storage_config.py` para todas las rutas (no hardcodear)
