---
name: agregar-curso
description: Como crear y gestionar cursos en Aeternum Academy - upload videos, YouTube embed, categorias, progreso de usuarios
---

## Agregar un curso en Aeternum Academy

### Via Admin UI

1. Ir a `/admin/courses/new`
2. Completar formulario:
   - Titulo del curso
   - Descripcion
   - Categoria (Math, Science, Technology, Art)
   - Instructor (nombre)
   - Video: subir archivo local O pegar link de YouTube
3. Guardar curso

### Sistema de video

- Videos locales se guardan en `storage/videos/`
- YouTube se integra via embed (iframe)
- Backend sirve videos con streaming

### Categorias de cursos

- Math
- Science
- Technology
- Art

### Progreso de usuarios

- Se tracks completacion de lecciones
- Los usuarios ganan Aethers/Rayos al completar cursos
- Se almacena en tabla `course_progress`

### Codigo relevante

- Endpoint: `POST /api/admin/courses` en `backend/server.py`
- Modelo: tabla `courses` en `backend/database.py`
- Frontend: `frontend/src/pages/AdminCourseFormPage.jsx`
- Player: `frontend/src/pages/CoursePlayerPage.jsx`
- Catalogo: `frontend/src/pages/CoursesPage.jsx`

### Notas

- Los videos locales pueden ser pesados; considerar YouTube para contenido largo
- El persistent disk en Render tiene 10 GB limitados
