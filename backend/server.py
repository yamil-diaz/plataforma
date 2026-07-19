import os
import uuid
import zipfile
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr

from database import init_db, get_db

# ── Directorios de almacenamiento ───────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend_dist")

# Crear directorios ANTES de que FastAPI los monte como StaticFiles
# NOTA: FRONTEND_DIR lo crea el build de npm — no lo creamos aquí
for directory in (STORAGE_BOOKS, STORAGE_COVERS, TEMP_DIR):
    os.makedirs(directory, exist_ok=True)

# ── Inicializar base de datos ────────────────────────────────────────────────
init_db()

# ── Aplicación FastAPI ───────────────────────────────────────────────────────
app = FastAPI(title="Lectura Rayos API")
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
            "SELECT id, name, email, role, rayos_balance FROM users WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        user = dict(row)
        user["_id"] = str(user["id"])
        return user
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


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}


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

    try:
        cursor.execute(
            "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at) VALUES (%s, %s, %s, 'user', 100, %s) RETURNING id",
            (user_data.name, user_data.email, hashed, now),
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
async def login(login_data: UserLogin, response: Response):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id, name, email, hashed_password, role, rayos_balance FROM users WHERE email = %s",
        (login_data.email,),
    )
    row = cursor.fetchone()
    if not row or not verify_password(login_data.password, row["hashed_password"]):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

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


@api_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Sesión cerrada correctamente"}


@api_router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user


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
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para borrar libros")

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id, pdf_path, cover_image_url FROM books WHERE id = %s",
            (int(book_id),),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")

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
        return {"message": "Book deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid book ID or error: {str(e)}")


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
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para crear libros")

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

    try:
        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, 1, %s)
            RETURNING id
            """,
            (title, author_name, content, category, price, cover_url, pdf_path, now),
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


# ── Montar rutas ─────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")

if os.path.isdir(FRONTEND_DIR) and os.path.isfile(os.path.join(FRONTEND_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
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
