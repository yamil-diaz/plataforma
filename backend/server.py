import os
import uuid
import zipfile
import shutil
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

import jwt
import bcrypt
from fastapi import (
    FastAPI,
    APIRouter,
    Request,
    Response,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr

from database import init_db, get_db

# ── Directorios de almacenamiento ───────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")
STORAGE_VIDEOS = os.path.join(STORAGE_DIR, "videos")
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend_dist")

# Crear directorios ANTES de que FastAPI los monte como StaticFiles
# NOTA: FRONTEND_DIR lo crea el build de npm — no lo creamos aquí
for directory in (STORAGE_BOOKS, STORAGE_COVERS, STORAGE_VIDEOS, TEMP_DIR):
    os.makedirs(directory, exist_ok=True)

# ── Inicializar base de datos ────────────────────────────────────────────────
init_db()

try:
    import migrate_db_phase4
    migrate_db_phase4.migrate()
    import migrate_username
    migrate_username.migrate()
    import migrate_db_phase4_2
    migrate_db_phase4_2.migrate()
    import migrate_db_phase4_3
    migrate_db_phase4_3.migrate()
except Exception as e:
    print(f"Error ejecutando migración Fase 4: {e}")

# ── Aplicación FastAPI ───────────────────────────────────────────────────────
app = FastAPI(title="Aeternum API")
api_router = APIRouter()

IS_PRODUCTION = os.getenv("RENDER") == "true" or os.getenv("ENV") == "production"
SECRET_KEY = os.getenv("SECRET_KEY", "clave-super-secreta-lectura-rayos")
ALGORITHM = "HS256"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos (directorios ya existen porque se crearon arriba)
app.mount("/static/covers", StaticFiles(directory=STORAGE_COVERS), name="covers")
app.mount("/static/books", StaticFiles(directory=STORAGE_BOOKS), name="books")
app.mount("/static/videos", StaticFiles(directory=STORAGE_VIDEOS), name="videos")

import_tasks: Dict[str, Dict] = {}


# ── Utilidades de autenticación ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, email: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user_optional(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id: return None
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, role, rayos_balance, is_banned, username FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        db.close()
        if not row or row.get("is_banned"): return None
        return row
    except Exception:
        return None

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    cookie_kwargs = {
        "httponly": True,
        "secure": IS_PRODUCTION,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(key="access_token", value=access_token, max_age=3600, **cookie_kwargs)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=604800, **cookie_kwargs)


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Sesión no iniciada (Token no encontrado)")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token no válido")

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, name, email, role, rayos_balance, is_banned, username FROM users WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
            
        if row.get("is_banned"):
            raise HTTPException(status_code=403, detail="Tu cuenta ha sido suspendida")

        db.close()
        return row
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token no válido")


# ── Modelos Pydantic ─────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RayosTransaction(BaseModel):
    amount: int
    type: str
    description: str

class CompetitionQuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str

class CompetitionCreate(BaseModel):
    title: str
    book_title: str
    scheduled_at: str
    questions: List[CompetitionQuestionCreate]

class CompetitionSubmit(BaseModel):
    score: int
    time_taken_ms: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@api_router.get("/health")
async def health_check():
    result = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        result["db_tables"] = [r["tablename"] for r in cursor.fetchall()]
        db.close()
    except Exception as e:
        result["db_error"] = str(e)
    return result


@api_router.get("/debug/files")
async def debug_files():
    """Endpoint temporal para diagnosticar qué archivos y tablas existen en Render."""
    result = {
        "base_dir": BASE_DIR,
        "frontend_dir": FRONTEND_DIR,
        "frontend_dir_exists": os.path.isdir(FRONTEND_DIR),
        "index_html_exists": os.path.isfile(os.path.join(FRONTEND_DIR, "index.html")),
        "files_in_frontend_dist": [],
        "db_tables": [],
        "db_error": None,
    }
    if os.path.isdir(FRONTEND_DIR):
        for root, dirs, files in os.walk(FRONTEND_DIR):
            for f in files:
                result["files_in_frontend_dist"].append(os.path.join(root, f))
    # Verificar tablas de BD
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        result["db_tables"] = [r["tablename"] for r in cursor.fetchall()]
        db.close()
    except Exception as e:
        result["db_error"] = str(e)
    return result


@api_router.post("/register")
async def register(user_data: UserRegister, response: Response):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    hashed = hash_password(user_data.password)
    now = datetime.now(timezone.utc).isoformat()
    
    base_username = "".join(c for c in user_data.name.lower() if c.isalnum())
    random_suffix = "".join(random.choices(string.digits, k=4))
    username = f"{base_username}{random_suffix}"

    try:
        cursor.execute(
            "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at, username) VALUES (%s, %s, %s, 'user', 100, %s, %s) RETURNING id",
            (user_data.name, user_data.email, hashed, now, username),
        )
        db.commit()
        user_id = cursor.fetchone()["id"]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")

    set_auth_cookies(
        response,
        create_access_token(user_id, user_data.email),
        create_refresh_token(user_id),
    )

    return {
        "_id": str(user_id),
        "id": str(user_id),
        "email": user_data.email,
        "name": user_data.name,
        "role": "user",
        "rayos_balance": 100,
    }


@api_router.post("/login")
async def login(login_data: UserLogin, response: Response, request: Request):
    db = get_db()
    cursor = db.cursor()
    
    # Rate Limiting check
    identifier = login_data.email
    cursor.execute("SELECT attempts, lockout_until FROM login_attempts WHERE ip_address = %s", (identifier,))
    attempt_row = cursor.fetchone()
    now_dt = datetime.now(timezone.utc)
    
    if attempt_row and attempt_row["lockout_until"]:
        lockout_time = datetime.fromisoformat(attempt_row["lockout_until"])
        if now_dt < lockout_time:
            remaining = int((lockout_time - now_dt).total_seconds() / 60)
            raise HTTPException(status_code=429, detail=f"Demasiados intentos. Intenta de nuevo en {remaining} minutos.")
        else:
            cursor.execute("UPDATE login_attempts SET attempts = 0, lockout_until = NULL WHERE ip_address = %s", (identifier,))
            db.commit()

    cursor.execute(
        "SELECT id, name, email, hashed_password, role, rayos_balance, is_banned FROM users WHERE email = %s",
        (login_data.email,),
    )
    row = cursor.fetchone()
    if not row or not verify_password(login_data.password, row["hashed_password"]):
        # Increment attempt
        if attempt_row:
            new_attempts = attempt_row["attempts"] + 1
            lockout_until = None
            if new_attempts >= 5:
                lockout_until = (now_dt + timedelta(minutes=15)).isoformat()
            cursor.execute("UPDATE login_attempts SET attempts = %s, lockout_until = %s WHERE ip_address = %s", (new_attempts, lockout_until, identifier))
        else:
            cursor.execute("INSERT INTO login_attempts (ip_address, attempts) VALUES (%s, 1)", (identifier,))
        db.commit()
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
        
    # Reset attempts on success
    cursor.execute("DELETE FROM login_attempts WHERE ip_address = %s", (identifier,))
    db.commit()
        
    if row.get("is_banned"):
        raise HTTPException(status_code=403, detail="Tu cuenta ha sido suspendida")

    user_id = row["id"]
    set_auth_cookies(
        response,
        create_access_token(user_id, row["email"]),
        create_refresh_token(user_id),
    )

    return {
        "_id": str(user_id),
        "id": str(user_id),
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "rayos_balance": row["rayos_balance"],
    }


class ForgotPasswordRequest(BaseModel):
    email: str

@api_router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    row = cursor.fetchone()
    if not row:
        # Prevent email enumeration by always returning success
        return {"message": "Si el correo existe, se enviará un enlace de recuperación."}
        
    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    
    cursor.execute(
        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (row["id"], token, expires_at)
    )
    db.commit()
    # In a real app, send an email. For now, print to console.
    print(f"[CORREO SIMULADO] Enlace de recuperación para {req.email}: https://aeternum-world.onrender.com/reset-password?token={token}")
    return {"message": "Si el correo existe, se enviará un enlace de recuperación."}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@api_router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT user_id, expires_at, used FROM password_resets WHERE token = %s", (req.token,))
    row = cursor.fetchone()
    
    if not row or row["used"]:
        raise HTTPException(status_code=400, detail="Enlace inválido o ya utilizado.")
        
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="El enlace ha expirado.")
        
    hashed_pw = get_password_hash(req.new_password)
    cursor.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (hashed_pw, row["user_id"]))
    cursor.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (req.token,))
    db.commit()
    return {"message": "Contraseña actualizada exitosamente."}

@api_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Sesión cerrada correctamente"}


@api_router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user


@api_router.get("/users")
async def get_all_users(request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.name, u.email, u.role, u.is_banned, u.created_at,
               (SELECT COUNT(*) FROM books b WHERE b.uploader_id = u.id) as books_count
        FROM users u
        ORDER BY u.id DESC
    """)
    rows = cursor.fetchall()
    return rows


@api_router.put("/users/{target_id}/ban")
async def toggle_ban_user(target_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT role, is_banned FROM users WHERE id = %s", (target_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if row["role"] == "admin":
        raise HTTPException(status_code=400, detail="No se puede banear a otro administrador")
        
    new_status = not row.get("is_banned", False)
    cursor.execute("UPDATE users SET is_banned = %s WHERE id = %s", (new_status, target_id))
    db.commit()
    return {"message": "Estado de baneo actualizado exitosamente", "is_banned": new_status}

@api_router.get("/users/profile/{username}")
async def get_user_profile(username: str, request: Request):
    db = get_db()
    cursor = db.cursor()
    
    # Soporte retrocompatible por si acaso aún mandan un ID
    if username.isdigit():
        cursor.execute("""
            SELECT id, name, username, role, rayos_balance, historical_rayos, bio, favorite_genres, profile_image_url, created_at
            FROM users WHERE id = %s
        """, (int(username),))
    else:
        cursor.execute("""
            SELECT id, name, username, role, rayos_balance, historical_rayos, bio, favorite_genres, profile_image_url, created_at
            FROM users WHERE username = %s
        """, (username,))
        
    user_data = cursor.fetchone()
    
    if not user_data:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    user_id = user_data["id"]
        
    cursor.execute("""
        SELECT b.*, ub.awarded_at
        FROM user_badges ub
        JOIN badges b ON ub.badge_id = b.id
        WHERE ub.user_id = %s
    """, (user_id,))
    badges = cursor.fetchall()
    
    cursor.execute("""
        SELECT id, title, cover_image_url, category, likes, views 
        FROM books 
        WHERE uploader_id = %s AND published = 1
    """, (user_id,))
    published_books = cursor.fetchall()
    
    # Followers count
    cursor.execute("SELECT COUNT(*) as count FROM followers WHERE following_id = %s", (user_id,))
    followers_count = cursor.fetchone()["count"]
    
    # Following count
    cursor.execute("SELECT COUNT(*) as count FROM followers WHERE follower_id = %s", (user_id,))
    following_count = cursor.fetchone()["count"]
    
    # Check if current user is following
    current_user = await get_current_user_optional(request)
    is_following = False
    if current_user:
        cursor.execute("SELECT 1 FROM followers WHERE follower_id = %s AND following_id = %s", (current_user["id"], user_id))
        is_following = bool(cursor.fetchone())
        
    db.close()
    
    return {
        "profile": user_data,
        "badges": badges,
        "books": published_books,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following
    }

@api_router.put("/users/profile/me")
async def update_my_profile(
    request: Request,
    username: str = Form(None),
    bio: str = Form(None),
    favorite_genres: str = Form(None),
    profile_image: UploadFile = File(None)
):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
        
    db = get_db()
    cursor = db.cursor()
    
    updates = []
    params = []
    
    if username is not None:
        # Check if username is already taken
        cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user["id"]))
        if cursor.fetchone():
            db.close()
            raise HTTPException(status_code=400, detail="Ese nombre de usuario ya está en uso")
        updates.append("username = %s")
        params.append(username)
        
    if bio is not None:
        updates.append("bio = %s")
        params.append(bio)
    if favorite_genres is not None:
        updates.append("favorite_genres = %s")
        params.append(favorite_genres)
        
    if profile_image is not None:
        import uuid
        import shutil
        ext = profile_image.filename.split('.')[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(STORAGE_IMAGES, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(profile_image.file, buffer)
        updates.append("profile_image_url = %s")
        params.append(f"/static/images/{filename}")
        
    if not updates:
        db.close()
        return {"detail": "Sin cambios"}
        
    params.append(user["id"])
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
    
    try:
        cursor.execute(query, tuple(params))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
        
    return {"message": "Perfil actualizado exitosamente"}


@api_router.get("/books/pending")
async def get_pending_books(request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books WHERE published = 0 ORDER BY created_at DESC")
    return cursor.fetchall()

@api_router.put("/books/{book_id}/approve")
async def approve_book(book_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE books SET published = 1 WHERE id = %s RETURNING uploader_id, title", (book_id,))
    row = cursor.fetchone()
    if row:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO notifications (user_id, message, created_at) VALUES (%s, %s, %s)",
                       (row["uploader_id"], f"Tu publicación '{row['title']}' ha sido aprobada y ya es pública.", now))
    db.commit()
    return {"message": "Libro aprobado"}

@api_router.delete("/books/{book_id}/reject")
async def reject_book(book_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT uploader_id, title FROM books WHERE id = %s", (book_id,))
    row = cursor.fetchone()
    if row:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO notifications (user_id, message, created_at) VALUES (%s, %s, %s)",
                       (row["uploader_id"], f"Tu publicación '{row['title']}' no fue aprobada y ha sido eliminada.", now))
        cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
    db.commit()
    return {"message": "Libro rechazado y eliminado"}

@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (user["id"],))
    return cursor.fetchall()

@api_router.put("/notifications/{notif_id}/read")
async def read_notification(notif_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s", (notif_id, user["id"]))
    db.commit()
    return {"message": "Notificación leída"}

@api_router.get("/settings")
async def get_settings():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT key, value FROM settings")
    return {row["key"]: row["value"] for row in cursor.fetchall()}

@api_router.get("/books")
async def get_books(category: Optional[str] = None):
    db = get_db()
    cursor = db.cursor()

    query = "SELECT * FROM books WHERE published = 1"
    params = []
    if category:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY views DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    books = []
    for row in rows:
        book = dict(row)
        book["_id"] = str(book["id"])
        books.append(book)

    return books


@api_router.get("/books/{book_id}")
async def get_book(book_id: str):
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM books WHERE id = %s", (int(book_id),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")

        book = dict(row)
        cursor.execute("UPDATE books SET views = views + 1 WHERE id = %s", (int(book_id),))
        db.commit()

        book["views"] += 1
        book["_id"] = str(book["id"])
        book["id"] = book["_id"]
        return book
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/books/{book_id}")
async def delete_book(book_id: str, request: Request):
    user = await get_current_user(request)
    
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id, pdf_path, cover_image_url, uploader_id FROM books WHERE id = %s",
            (int(book_id),),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")

        if user["role"] != "admin" and row["uploader_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="No autorizado para borrar este libro")

        if row["pdf_path"] and os.path.exists(row["pdf_path"]):
            try:
                os.remove(row["pdf_path"])
            except OSError:
                pass

        if row["cover_image_url"] and "static/covers" in row["cover_image_url"]:
            cover_filename = row["cover_image_url"].split("/static/covers/")[-1]
            cover_path = os.path.join(STORAGE_COVERS, cover_filename)
            if os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                except OSError:
                    pass

        cursor.execute("DELETE FROM books WHERE id = %s", (int(book_id),))
        db.commit()
        return {"detail": "Libro borrado exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@api_router.put("/books/{book_id}")
async def update_book(
    book_id: int,
    request: Request,
    title: str = Form(None),
    author_name: str = Form(None),
    category: str = Form(None),
    price: float = Form(None),
    cover_image: UploadFile = File(None)
):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT uploader_id FROM books WHERE id = %s", (book_id,))
    row = cursor.fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Libro no encontrado")
        
    if user["role"] != "admin" and row["uploader_id"] != user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="No autorizado para editar este libro")
        
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = %s")
        params.append(title)
    if author_name is not None:
        updates.append("author_name = %s")
        params.append(author_name)
    if category is not None:
        updates.append("category = %s")
        params.append(category)
    if price is not None:
        updates.append("price = %s")
        params.append(price)
        
    if cover_image is not None:
        import uuid
        import shutil
        cover_ext = cover_image.filename.split('.')[-1]
        cover_filename = f"{uuid.uuid4().hex}.{cover_ext}"
        cover_path = os.path.join(STORAGE_IMAGES, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
        updates.append("cover_image_url = %s")
        params.append(f"/static/images/{cover_filename}")
        
    if not updates:
        db.close()
        return {"detail": "Sin cambios"}
        
    params.append(book_id)
    query = f"UPDATE books SET {', '.join(updates)} WHERE id = %s"
    
    try:
        cursor.execute(query, tuple(params))
        db.commit()
        return {"detail": "Libro actualizado exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@api_router.get("/users/me/books")
async def get_my_books(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM books WHERE uploader_id = %s ORDER BY created_at DESC", (user["id"],))
        rows = cursor.fetchall()
        for row in rows:
            row["_id"] = str(row["id"])
            row["id"] = row["_id"]
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@api_router.get("/books/{book_id}/download")
async def download_book_pdf(book_id: int):
    """Genera un PDF del contenido del libro y lo devuelve para descarga."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()
    db.close()

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    # Si el libro ya tiene un PDF almacenado, devolverlo
    if book["pdf_path"] and os.path.isfile(book["pdf_path"]):
        return FileResponse(
            book["pdf_path"],
            media_type="application/pdf",
            filename=f"{book['title']}.pdf",
        )

    # Generar PDF del contenido de texto
    pdf_filename = f"{uuid.uuid4()}_{book_id}.pdf"
    pdf_path = os.path.join(STORAGE_BOOKS, pdf_filename)

    try:
        _generate_text_pdf(pdf_path, book["title"], book["author_name"], book["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{book['title']}.pdf",
    )


def _generate_text_pdf(output_path: str, title: str, author: str, content: str):
    """Genera un PDF con portada y contenido formateado usando fpdf2."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    # Pagina de portada
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.ln(60)
    pdf.cell(0, 15, title, ln=True, align="C")
    pdf.set_font("Helvetica", "I", 16)
    pdf.ln(10)
    pdf.cell(0, 10, f"por {author}", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(20)
    pdf.cell(0, 10, "Generado por Aeternum - Plataforma de Lectura", ln=True, align="C")

    # Paginas de contenido
    pdf.add_page()
    pdf.set_font("Helvetica", "", 12)

    paragraphs = content.split("\n")
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if paragraph:
            pdf.multi_cell(0, 7, paragraph)
            pdf.ln(4)

    pdf.output(output_path)


@api_router.post("/books")
async def create_book(
    title: str = Form(...),
    author_name: str = Form(...),
    category: str = Form(...),
    price: float = Form(0.0),
    pdf_file: Optional[UploadFile] = File(None),
    cover_file: Optional[UploadFile] = File(None),
    request: Request = None,
):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()

    pdf_path = None
    content = "Contenido de texto no disponible."
    cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"

    if pdf_file:
        import pypdf

        unique_pdf_name = f"{uuid.uuid4()}_{pdf_file.filename}"
        pdf_path = os.path.join(STORAGE_BOOKS, unique_pdf_name)
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        try:
            reader = pypdf.PdfReader(pdf_path)
            extracted_text = ""
            max_pages = min(len(reader.pages), 30)
            for page_index in range(max_pages):
                page_text = reader.pages[page_index].extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            if extracted_text.strip():
                content = extracted_text
        except Exception as e:
            content = f"Error al extraer texto del PDF: {str(e)}"

    if cover_file:
        unique_cover_name = f"{uuid.uuid4()}_{cover_file.filename}"
        cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_file.file, buffer)
        cover_url = f"/static/covers/{unique_cover_name}"

    now = datetime.now(timezone.utc).isoformat()

    published_status = 1 if user["role"] == "admin" else 0

    try:
        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at, uploader_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, %s, %s, %s)
            RETURNING id
            """,
            (title, author_name, content, category, price, cover_url, pdf_path, published_status, now, user["id"]),
        )
        db.commit()
        book_id = cursor.fetchone()["id"]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el libro: {str(e)}")

    return {
        "_id": str(book_id),
        "id": str(book_id),
        "title": title,
        "author_name": author_name,
        "category": category,
        "price": price,
        "cover_image_url": cover_url,
        "average_rating": 0.0,
        "total_reviews": 0,
    }


def process_bulk_zip(task_id: str, zip_path: str, default_category: str, default_price: float):
    import pypdf

    db = get_db()
    cursor = db.cursor()
    task_status = import_tasks[task_id]

    try:
        task_temp_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)

        task_status["message"] = "Descomprimiendo archivo ZIP..."
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(task_temp_dir)

        all_files = []
        for root, _, files in os.walk(task_temp_dir):
            for file in files:
                all_files.append(os.path.join(root, file))

        pdf_files = [file for file in all_files if file.lower().endswith(".pdf")]
        image_files = [
            file for file in all_files if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ]

        task_status["total"] = len(pdf_files)
        task_status["message"] = f"Encontrados {len(pdf_files)} PDFs. Iniciando procesamiento..."

        image_map = {}
        for image in image_files:
            basename = os.path.basename(image)
            name_without_ext = os.path.splitext(basename)[0].lower()
            image_map[name_without_ext] = image

        for pdf in pdf_files:
            filename = os.path.basename(pdf)
            name_without_ext = os.path.splitext(filename)[0]

            try:
                title = None
                author = None
                content = "Contenido de texto no disponible."

                try:
                    reader = pypdf.PdfReader(pdf)
                    meta = reader.metadata
                    if meta:
                        title = meta.title
                        author = meta.author

                    extracted_text = ""
                    max_pages = min(len(reader.pages), 30)
                    for page_index in range(max_pages):
                        page_text = reader.pages[page_index].extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                    if extracted_text.strip():
                        content = extracted_text
                except Exception:
                    pass

                if not title:
                    title = name_without_ext.replace("_", " ").replace("-", " ").title()
                if not author:
                    author = "Autor Desconocido"

                unique_pdf_name = f"{uuid.uuid4()}_{filename}"
                final_pdf_path = os.path.join(STORAGE_BOOKS, unique_pdf_name)
                shutil.copy2(pdf, final_pdf_path)

                cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"
                match_name = name_without_ext.lower()
                if match_name in image_map:
                    matched_img = image_map[match_name]
                    img_ext = os.path.splitext(matched_img)[1]
                    unique_cover_name = f"{uuid.uuid4()}_{name_without_ext}{img_ext}"
                    final_cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
                    shutil.copy2(matched_img, final_cover_path)
                    cover_url = f"/static/covers/{unique_cover_name}"

                now = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """
                    INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, 1, %s)
                    """,
                    (title, author, content, default_category, default_price, cover_url, final_pdf_path, now),
                )
                db.commit()

                task_status["processed"] += 1
                task_status["message"] = (
                    f"Procesados {task_status['processed']}/{task_status['total']} libros."
                )
            except Exception as e:
                task_status["errors"].append(f"Error procesando {filename}: {str(e)}")

        try:
            shutil.rmtree(task_temp_dir)
            os.remove(zip_path)
        except OSError:
            pass

        task_status["status"] = "completed"
        task_status["message"] = (
            f"Importación masiva completada. Se importaron {task_status['processed']} libros con éxito."
        )
    except Exception as e:
        task_status["status"] = "failed"
        task_status["message"] = f"Error crítico en la importación: {str(e)}"
    finally:
        db.close()


@api_router.post("/books/import")
async def import_books(
    file: UploadFile = File(...),
    category: str = Form("General"),
    price: float = Form(0.0),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para importar libros")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .zip")

    task_id = str(uuid.uuid4())
    temp_zip_path = os.path.join(TEMP_DIR, f"{task_id}.zip")
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    import_tasks[task_id] = {
        "status": "processing",
        "total": 0,
        "processed": 0,
        "errors": [],
        "message": "Guardando archivo y preparando proceso en segundo plano...",
    }

    background_tasks.add_task(process_bulk_zip, task_id, temp_zip_path, category, price)
    return {"task_id": task_id, "message": "Importación masiva iniciada en segundo plano"}


@api_router.get("/books/import/status/{task_id}")
async def get_import_status(task_id: str, request: Request):
    await get_current_user(request)
    if task_id not in import_tasks:
        raise HTTPException(status_code=404, detail="Tarea de importación no encontrada")
    return import_tasks[task_id]


@api_router.post("/books/{book_id}/reviews")
async def create_review(book_id: str, review_data: ReviewCreate, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM books WHERE id = %s", (int(book_id),))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")

        cursor.execute(
            "SELECT id FROM reviews WHERE book_id = %s AND user_id = %s",
            (int(book_id), int(user["_id"])),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ya has dejado una reseña para este libro")

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO reviews (book_id, user_id, user_name, rating, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (int(book_id), int(user["_id"]), user["name"], review_data.rating, review_data.comment, now),
        )
        db.commit()
        review_id = cursor.fetchone()["id"]

        cursor.execute("SELECT rating FROM reviews WHERE book_id = %s", (int(book_id),))
        ratings = [row["rating"] for row in cursor.fetchall()]
        total_reviews = len(ratings)
        average_rating = sum(ratings) / total_reviews if total_reviews > 0 else 0.0

        cursor.execute(
            "UPDATE books SET average_rating = %s, total_reviews = %s WHERE id = %s",
            (round(average_rating, 1), total_reviews, int(book_id)),
        )
        db.commit()

        return {
            "id": str(review_id),
            "_id": str(review_id),
            "book_id": book_id,
            "user_id": user["_id"],
            "user_name": user["name"],
            "rating": review_data.rating,
            "comment": review_data.comment,
            "created_at": now,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de ID del libro inválido")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@api_router.get("/books/{book_id}/reviews")
async def get_book_reviews(book_id: str):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM reviews WHERE book_id = %s ORDER BY created_at DESC",
            (int(book_id),),
        )
        rows = cursor.fetchall()

        reviews = []
        for row in rows:
            review = dict(row)
            review["id"] = str(review["id"])
            review["_id"] = review["id"]
            reviews.append(review)

        return reviews
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/rayos/earn")
async def earn_rayos(transaction_data: RayosTransaction, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()

    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO rayos_transactions (user_id, amount, type, description, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                int(user["_id"]),
                transaction_data.amount,
                transaction_data.type,
                transaction_data.description,
                now,
            ),
        )
        cursor.execute(
            "UPDATE users SET rayos_balance = rayos_balance + %s WHERE id = %s",
            (transaction_data.amount, int(user["_id"])),
        )
        db.commit()
        return {"success": True, "message": "Puntos Rayos sumados con éxito"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/rayos/transactions")
async def get_rayos_transactions(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM rayos_transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
        (int(user["_id"]),),
    )
    rows = cursor.fetchall()

    transactions = []
    for row in rows:
        transaction = dict(row)
        transaction["id"] = str(transaction["id"])
        transactions.append(transaction)

    return transactions


# --- CURSOS ENDPOINTS ---
@api_router.get("/courses")
async def get_courses():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY created_at DESC")
    return cursor.fetchall()

@api_router.get("/courses/{course_id}")
async def get_course(course_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return row

@api_router.post("/courses")
async def create_course(
    title: str = Form(...),
    description: str = Form(...),
    instructor: str = Form(...),
    category: str = Form(...),
    reward_amount: int = Form(50),
    video_file: UploadFile = File(...),
    cover_file: UploadFile = File(...),
    request: Request = None,
):
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()

    unique_video_name = f"{uuid.uuid4()}_{video_file.filename}"
    video_path = os.path.join(STORAGE_VIDEOS, unique_video_name)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video_file.file, buffer)
    video_url = f"/static/videos/{unique_video_name}"

    unique_cover_name = f"{uuid.uuid4()}_{cover_file.filename}"
    cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
    with open(cover_path, "wb") as buffer:
        shutil.copyfileobj(cover_file.file, buffer)
    cover_url = f"/static/covers/{unique_cover_name}"

    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute(
            """
            INSERT INTO courses (title, description, instructor, category, video_url, cover_url, reward_amount, created_at, uploader_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (title, description, instructor, category, video_url, cover_url, reward_amount, now, user["id"])
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Curso creado exitosamente"}

@api_router.post("/courses/{course_id}/complete")
async def complete_course(course_id: int, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión para obtener recompensas")
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT reward_amount FROM courses WHERE id = %s", (course_id,))
    course = cursor.fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
        
    cursor.execute("SELECT id FROM course_progress WHERE user_id = %s AND course_id = %s", (user["id"], course_id))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Ya reclamaste la recompensa de este curso")
        
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute(
            "INSERT INTO course_progress (user_id, course_id, completed_at) VALUES (%s, %s, %s)",
            (user["id"], course_id, now)
        )
        cursor.execute(
            "UPDATE users SET rayos_balance = rayos_balance + %s WHERE id = %s",
            (course["reward_amount"], user["id"])
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar la recompensa")
        
    return {"message": f"¡Felicidades! Has ganado {course['reward_amount']} Rayos."}

@api_router.delete("/courses/{course_id}")
async def delete_course(course_id: int, request: Request):
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()
    try:
        # PostgreSQL CASCADE should handle course_progress table if set, 
        # but just in case, we can manually delete or rely on cascade.
        cursor.execute("DELETE FROM course_progress WHERE course_id = %s", (course_id,))
        cursor.execute("DELETE FROM courses WHERE id = %s RETURNING video_url, cover_url", (course_id,))
        deleted = cursor.fetchone()
        
        if not deleted:
            db.rollback()
            raise HTTPException(status_code=404, detail="Curso no encontrado")
            
        # Opcional: Eliminar los archivos físicos (video_url, cover_url)
        # por ahora lo dejamos para no complicar la limpieza de archivos
        
        db.commit()
        return {"message": "Curso eliminado correctamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    request: Request,
    title: str = Form(None),
    description: str = Form(None),
    instructor: str = Form(None),
    category: str = Form(None),
    reward_amount: int = Form(None),
    cover_image: UploadFile = File(None)
):
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM courses WHERE id = %s", (course_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Curso no encontrado")
        
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = %s")
        params.append(title)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if instructor is not None:
        updates.append("instructor = %s")
        params.append(instructor)
    if category is not None:
        updates.append("category = %s")
        params.append(category)
    if reward_amount is not None:
        updates.append("reward_amount = %s")
        params.append(reward_amount)
        
    if cover_image is not None:
        import uuid
        import shutil
        cover_ext = cover_image.filename.split('.')[-1]
        cover_filename = f"{uuid.uuid4().hex}.{cover_ext}"
        cover_path = os.path.join(STORAGE_IMAGES, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
        updates.append("cover_url = %s")
        params.append(f"/static/images/{cover_filename}")
        
    if not updates:
        db.close()
        return {"message": "No hay cambios para actualizar"}
        
    params.append(course_id)
    query = f"UPDATE courses SET {', '.join(updates)} WHERE id = %s"
    
    try:
        cursor.execute(query, tuple(params))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
        
    return {"message": "Curso actualizado exitosamente"}


# --- GUTENBERG ENDPOINT ---
@api_router.post("/admin/gutenberg/fetch")
async def fetch_gutenberg_book(book_id: int = Form(...), request: Request = None):
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    import urllib.request
    import json
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        meta_url = f"https://gutendex.com/books/{book_id}"
        req = urllib.request.Request(meta_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            meta_data = json.loads(response.read().decode())
            
        title = meta_data.get("title", f"Gutenberg Book {book_id}")
        authors = meta_data.get("authors", [])
        author_name = authors[0]["name"] if authors else "Project Gutenberg"
        
        text_url = None
        for fmt, url in meta_data.get("formats", {}).items():
            if fmt.startswith("text/plain"):
                text_url = url
                break
                
        if not text_url:
            raise HTTPException(status_code=400, detail="No se encontró versión en texto para este libro.")
            
        try:
            req2 = urllib.request.Request(text_url, headers=headers)
            with urllib.request.urlopen(req2) as response:
                content = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if "403" in str(e):
                # Fallback to a public proxy if Gutenberg blocks the datacenter IP
                proxy_url = f"https://api.allorigins.win/raw?url={text_url}"
                req_proxy = urllib.request.Request(proxy_url, headers=headers)
                with urllib.request.urlopen(req_proxy) as response:
                    content = response.read().decode('utf-8', errors='ignore')
            else:
                raise e
            
        cover_url = meta_data.get("formats", {}).get("image/jpeg", "https://via.placeholder.com/400x600?text=Gutenberg")
        
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at, uploader_id)
            VALUES (%s, %s, %s, %s, 0, %s, NULL, 0, 0, 0.0, 0, 1, %s, %s)
            RETURNING id
            """,
            (title, author_name, content[:100000], "Clásicos", cover_url, now, user["id"])
        )
        db.commit()
        return {"message": f"Libro '{title}' importado exitosamente."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Competencias de Lectura ───────────────────────────────────────────────────

@api_router.post("/admin/competitions")
async def create_competition(comp: CompetitionCreate, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear competencias.")
        
    db = get_db()
    cursor = db.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute(
            "INSERT INTO competitions (title, book_title, scheduled_at, status, created_at) VALUES (%s, %s, %s, 'pending', %s) RETURNING id",
            (comp.title, comp.book_title, comp.scheduled_at, now)
        )
        comp_id = cursor.fetchone()["id"]
        
        for q in comp.questions:
            cursor.execute(
                "INSERT INTO competition_questions (competition_id, question_text, option_a, option_b, option_c, option_d, correct_option) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (comp_id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option)
            )
            
        # Notificar a todos los usuarios
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        notif_msg = f"¡Nuevo torneo disponible: {comp.title} sobre {comp.book_title}!"
        for u in all_users:
            cursor.execute(
                "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'system', %s, %s)",
                (u["id"], notif_msg, now)
            )
            
        db.commit()
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    db.close()
    return {"message": "Competencia creada con éxito y usuarios notificados", "id": comp_id}

@api_router.get("/competitions")
async def get_competitions():
    db = get_db()
    cursor = db.cursor()
    
    # Auto-update status based on time
    now_dt = datetime.now(timezone.utc)
    
    cursor.execute("SELECT * FROM competitions")
    all_comps = cursor.fetchall()
    
    for c in all_comps:
        comp_dt = datetime.fromisoformat(c["scheduled_at"])
        time_diff = (now_dt - comp_dt).total_seconds()
        
        new_status = c["status"]
        if c["status"] == "pending" and time_diff >= 0:
            new_status = "active"
        
        # If it's been active for more than 15 minutes, auto-complete
        if c["status"] == "active" and time_diff > 900:
            new_status = "completed"
            
        if new_status != c["status"]:
            cursor.execute("UPDATE competitions SET status = %s WHERE id = %s", (new_status, c["id"]))
            c["status"] = new_status
            
    db.commit()
            
    cursor.execute("""
        SELECT c.*
        FROM competitions c
        ORDER BY c.scheduled_at DESC
    """)
    comps = cursor.fetchall()
    db.close()
    return comps

@api_router.get("/competitions/{comp_id}")
async def get_competition_details(comp_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT c.*
        FROM competitions c
        WHERE c.id = %s
    """, (comp_id,))
    comp = cursor.fetchone()
    
    if not comp:
        db.close()
        raise HTTPException(status_code=404, detail="Competencia no encontrada")
        
    # Check if user is registered
    cursor.execute("SELECT * FROM competition_participants WHERE competition_id = %s AND user_id = %s", (comp_id, user["id"]))
    participant = cursor.fetchone()
    
    questions = []
    # If active and registered, return questions
    if comp["status"] == "active" and participant and participant["status"] == "registered":
        cursor.execute("SELECT id, question_text, option_a, option_b, option_c, option_d FROM competition_questions WHERE competition_id = %s", (comp_id,))
        questions = cursor.fetchall()
        
    db.close()
    return {
        "competition": comp,
        "participant": participant,
        "questions": questions
    }

@api_router.post("/competitions/{comp_id}/join")
async def join_competition(comp_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT status FROM competitions WHERE id = %s", (comp_id,))
    comp = cursor.fetchone()
    if not comp:
        db.close()
        raise HTTPException(status_code=404, detail="Competencia no encontrada")
        
    if comp["status"] != "pending":
        db.close()
        raise HTTPException(status_code=400, detail="La competencia ya inició o finalizó")
        
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO competition_participants (competition_id, user_id, registered_at) VALUES (%s, %s, %s)",
            (comp_id, user["id"], now)
        )
        db.commit()
    except psycopg2.errors.UniqueViolation:
        db.rollback()
        pass # Ya está registrado
    finally:
        db.close()
        
    return {"message": "Registrado exitosamente"}

@api_router.post("/competitions/{comp_id}/submit")
async def submit_competition(comp_id: int, submission: CompetitionSubmit, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT status FROM competitions WHERE id = %s", (comp_id,))
    comp = cursor.fetchone()
    if not comp or comp["status"] != "active":
        db.close()
        raise HTTPException(status_code=400, detail="La competencia no está activa")
        
    cursor.execute("SELECT * FROM competition_participants WHERE competition_id = %s AND user_id = %s", (comp_id, user["id"]))
    participant = cursor.fetchone()
    
    if not participant or participant["status"] == "submitted":
        db.close()
        raise HTTPException(status_code=400, detail="No puedes enviar respuestas")
        
    cursor.execute(
        "UPDATE competition_participants SET score = %s, time_taken_ms = %s, status = 'submitted' WHERE id = %s",
        (submission.score, submission.time_taken_ms, participant["id"])
    )
    db.commit()
    db.close()
    return {"message": "Respuestas enviadas correctamente"}

@api_router.get("/competitions/{comp_id}/leaderboard")
async def get_competition_leaderboard(comp_id: int):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT p.score, p.time_taken_ms, p.status, u.id, u.name, u.username, u.profile_image_url
        FROM competition_participants p
        JOIN users u ON p.user_id = u.id
        WHERE p.competition_id = %s AND p.status = 'submitted'
        ORDER BY p.score DESC, p.time_taken_ms ASC
    """, (comp_id,))
    leaderboard = cursor.fetchall()
    db.close()
    
    return leaderboard

@api_router.post("/admin/competitions/{comp_id}/finish")
async def finish_competition(comp_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT status FROM competitions WHERE id = %s", (comp_id,))
    comp = cursor.fetchone()
    if not comp or comp["status"] == "completed":
        db.close()
        raise HTTPException(status_code=400, detail="Competencia no válida")
        
    cursor.execute("UPDATE competitions SET status = 'completed' WHERE id = %s", (comp_id,))
    
    # Repartir premios
    cursor.execute("""
        SELECT p.user_id 
        FROM competition_participants p
        WHERE p.competition_id = %s AND p.status = 'submitted'
        ORDER BY p.score DESC, p.time_taken_ms ASC
        LIMIT 3
    """, (comp_id,))
    winners = cursor.fetchall()
    
    now = datetime.now(timezone.utc).isoformat()
    prizes = [100, 50, 25]
    
    for i, winner in enumerate(winners):
        user_id = winner["user_id"]
        prize = prizes[i]
        
        # Add Rayos
        cursor.execute("UPDATE users SET rayos_balance = rayos_balance + %s, historical_rayos = historical_rayos + %s WHERE id = %s", (prize, prize, user_id))
        cursor.execute("INSERT INTO rayos_transactions (user_id, amount, type, description, created_at) VALUES (%s, %s, 'earned', %s, %s)", 
            (user_id, prize, f"Premio {i+1}er lugar en competencia", now))
            
        # Add Badge to 1st place
        if i == 0:
            cursor.execute("SELECT id FROM badges WHERE criteria_type = 'competition_winner'")
            badge = cursor.fetchone()
            if badge:
                try:
                    cursor.execute("INSERT INTO user_badges (user_id, badge_id, awarded_at) VALUES (%s, %s, %s)", (user_id, badge["id"], now))
                except psycopg2.errors.UniqueViolation:
                    pass
                    
    db.commit()
    db.close()
    return {"message": "Competencia finalizada y premios repartidos"}


# ── Social & Notificaciones ───────────────────────────────────────────────────

@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT * FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (user["id"],))
    notifs = cursor.fetchall()
    
    # Get unread count
    cursor.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = FALSE", (user["id"],))
    unread_count = cursor.fetchone()["count"]
    
    db.close()
    return {"notifications": notifs, "unread_count": unread_count}

@api_router.put("/notifications/read")
async def mark_notifications_read(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (user["id"],))
    db.commit()
    db.close()
    return {"message": "Notificaciones marcadas como leídas"}

@api_router.post("/users/{username}/follow")
async def follow_user(username: str, request: Request):
    current_user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    target = cursor.fetchone()
    if not target:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if current_user["id"] == target["id"]:
        db.close()
        raise HTTPException(status_code=400, detail="No puedes seguirte a ti mismo")
        
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute("INSERT INTO followers (follower_id, following_id, created_at) VALUES (%s, %s, %s)", 
            (current_user["id"], target["id"], now))
            
        # Notificar al usuario seguido
        cursor.execute("INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'follow', %s, %s)",
            (target["id"], f"@{current_user['username']} ha empezado a seguirte.", now))
            
        db.commit()
    except psycopg2.errors.UniqueViolation:
        pass # Already following
    finally:
        db.close()
        
    return {"message": "Has empezado a seguir a este usuario"}

@api_router.post("/users/{username}/unfollow")
async def unfollow_user(username: str, request: Request):
    current_user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    target = cursor.fetchone()
    if not target:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    cursor.execute("DELETE FROM followers WHERE follower_id = %s AND following_id = %s", (current_user["id"], target["id"]))
    db.commit()
    db.close()
    return {"message": "Has dejado de seguir a este usuario"}


# ── Montar rutas ─────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")

if os.path.isdir(FRONTEND_DIR) and os.path.isfile(os.path.join(FRONTEND_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    
    # Catch-all route para SPA (React Router)
    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: HTTPException):
        # Si la ruta comienza con /api/, devolver 404 real
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        
        # Para cualquier otra ruta, devolver el index.html de React
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

else:
    @app.get("/")
    async def root_fallback():
        return {
            "message": "API activa. Falta el build del frontend en backend/frontend_dist.",
            "health": "/api/health",
        }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=not IS_PRODUCTION)
