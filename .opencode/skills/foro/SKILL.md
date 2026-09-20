---
name: foro
description: Foro estudiantil de AeternumLibrary - categorias, posts, respuestas, likes, bookmarks, follow, reportes, moderacion, rate limiting
---

## Foro estudiantil

### Categorias seed (10)

1. Books
2. Writing
3. Academic Help
4. Literature
5. Science
6. History
7. Debate
8. Recommendations
9. General
10. Student Community

### Funcionalidades

- **Posts**: Crear, editar, eliminar
- **Respuestas**: Comentar en posts
- **Likes**: Dar/quitar likes a posts y respuestas
- **Bookmarks**: Guardar posts para leer despues
- **Follow**: Seguir usuarios
- **Reportes**: Reportar contenido inapropiado
- **Moderacion**: Admin puede gestionar reports y contenido

### Rate limiting

- Se aplica limite de posts por usuario
- Evita spam y abuso

### Tablas de la DB

- `forum_categories` - Categorias
- `forum_posts` - Posts principales
- `forum_replies` - Respuestas a posts
- `forum_likes` - Likes
- `forum_bookmarks` - Bookmarks
- `forum_follows` - Follows entre usuarios
- `forum_reports` - Reportes de contenido

### Endpoints API

- `GET /api/forum/posts` - Listar posts
- `POST /api/forum/posts` - Crear post
- `GET /api/forum/posts/{id}` - Ver post con respuestas
- `POST /api/forum/posts/{id}/reply` - Responder
- `POST /api/forum/posts/{id}/like` - Like/unlike
- `POST /api/forum/posts/{id}/bookmark` - Bookmark/unbookmark
- `GET /api/forum/categories` - Listar categorias
- `POST /api/admin/forum/moderate` - Admin: moderar

### Frontend

- `frontend/src/pages/ForumPage.jsx` - Lista de posts
- `frontend/src/pages/ForumPostPage.jsx` - Ver post
- `frontend/src/pages/ForumCategoryPage.jsx` - Posts por categoria
- `frontend/src/pages/ForumCreatePage.jsx` - Crear post
