---
name: arquitectura
description: Estructura completa de la plataforma AeternumLibrary - stack, archivos clave, base de datos, rutas API y frontend
---

## Arquitectura de AeternumLibrary

Plataforma gamificada de lectura y educacion. Tagline: "La primera plataforma donde la lectura tiene recompensas".

### Stack

| Capa | Tecnologia |
|------|------------|
| Backend | Python 3.11.9 + FastAPI 0.111.0 + Uvicorn |
| Frontend | React 18.3.1 + Vite 5.2.11 + Tailwind CSS 3.4.4 |
| Base de datos | PostgreSQL via psycopg2-binary 2.9.9 |
| Auth | JWT (pyjwt) + bcrypt + Google OAuth |
| IA | Google Gemini via google-genai 1.46.0 |
| Pagos digital | Paddle (internacional) |
| Pagos fisico | Culqi (Peru, PEN) |
| Deploy | Render.com (web service + PostgreSQL + persistent disk) |

### Archivos clave del Backend

- `backend/server.py` - Todos los endpoints API (6615 lineas).Archivo principal.
- `backend/database.py` - Schema PostgreSQL (users, books, reviews, rayos, courses, forum, etc.)
- `backend/lectura.py` - Extraccion PDF, deteccion de capitulos, paginacion (562 lineas)
- `backend/ai_service.py` - Orquestador AI con Gemini, retry, economia
- `backend/ai_providers.py` - Abstraccion de proveedores AI (Mock + Gemini)
- `backend/ai_context.py` - Constructor de contexto jerarquico para prompts
- `backend/ai_conversations.py` - Persistencia de conversaciones
- `backend/commerce_service.py` - Logica de negocio (ordenes, derechos, stock)
- `backend/payment_providers.py` - Abstraccion de pagos (Paddle + Culqi)
- `backend/webhook_handler.py` - Handler unificado de webhooks de pago
- `backend/import_gutenberg_batch.py` - Importador masivo de Gutenberg
- `backend/import_masiva.py` - Importador masivo desde ZIP
- `backend/storage_config.py` - Gestion centralizada de rutas de almacenamiento

### Archivos clave del Frontend

- `frontend/src/App.jsx` - 39 rutas, protected routes, init Paddle
- `frontend/src/pages/` - 33 componentes de pagina
- `frontend/src/components/` - 6 componentes reutilizables (Navbar, BookPreviewModal, PDFViewer, ReaderToolbar, ThumbnailSidebar, Toast)
- `frontend/src/contexts/AuthContext.jsx` - Estado de autenticacion
- `frontend/src/utils/api.js` - Cliente HTTP Axios

### Base de datos - Tablas principales

- `users` - Usuarios (id, username, email, password_hash, role, rayos_balance, google_id, etc.)
- `books` - Libros (id, title, author, category, content, cover_url, pdf_path, is_gutenberg, etc.)
- `reviews` - Resenas (id, user_id, book_id, rating, comment)
- `rayos` - Transacciones de Aethers/Rayos
- `courses` - Cursos de Aeternum Academy
- `forum_posts` - Posts del foro estudiantil
- `forum_replies` - Respuestas del foro
- `forum_categories` - 10 categorias seed (Books, Writing, Academic Help, etc.)
- `purchases` - Compras digitales
- `physical_orders` - Ordenes fisicas (Peru)
- `ai_conversations` - Conversaciones AI
- `reading_sessions` - Sesiones de lectura (anti-farm)
- `qr_codes` - Codigos QR de referidos

### Rutas API principales

- `POST /api/auth/register` - Registro
- `POST /api/auth/login` - Login
- `GET /api/books` - Catalogo
- `GET /api/books/{id}` - Detalle libro
- `GET /api/books/{id}/pages/{page}` - Pagina especifica
- `POST /api/books/{id}/read` - Registrar lectura (ganar Rayos)
- `POST /api/books/{id}/review` - Crear resena
- `GET /api/courses` - Cursos
- `POST /api/ai/chat` - Chat AI
- `GET /api/forum/posts` - Posts del foro
- `POST /api/admin/books` - Admin: crear libro
- `POST /api/admin/import/gutenberg` - Admin: importar Gutenberg
- `POST /api/checkout/paddle` - Checkout Paddle

### Sistema de Aethers/Rayos

- Moneda virtual que se gana leyendo libros, viendo cursos, participando en el foro
- 10+ Rayos por sesion de lectura (con proteccion anti-farm)
- Balance visible en navbar con badge animado
- Anti-farm: tracking de paginas diarias, sesiones con timestamp

### Estructura de directorios

```
plataforma/
├── backend/
│   ├── server.py
│   ├── database.py
│   ├── ai_*.py (modulos AI)
│   ├── commerce_*.py (pagos)
│   ├── tests/ (36 archivos de test)
│   ├── storage/ (archivos locales)
│   └── frontend_dist/ (build de React en produccion)
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── pages/ (33 paginas)
│       ├── components/ (6 componentes)
│       └── utils/ (api, paddle, etc.)
├── piloto/ (10 PDFs public domain)
├── .opencode/skills/ (este directorio)
└── render.yaml (config Deploy)
```
