from fastapi.responses import FileResponse
import os
import uuid
import zipfile
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import jwt
import bcrypt

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr

from database import init_db, get_db

# Inicializar Base de Datos
init_db()

app = FastAPI(title="Lectura Rayos API")

# Configurar Directorios de Almacenamiento
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")

for d in [STORAGE_BOOKS, STORAGE_COVERS, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)

# Configurar CORS (Permitir cookies y credenciales)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Dirección por defecto de Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static/covers", StaticFiles(directory=os.path.join(STORAGE_DIR, "covers")), name="covers")
app.mount("/static/books", StaticFiles(directory=os.path.join(STORAGE_DIR, "books")), name="books")
@app.get("/")
def read_index():
    index_path = os.path.join(BASE_DIR, "frontend_dist", "index.html")
    return FileResponse(index_path)

app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "frontend_dist"), html=True), name="frontend")

app.include_router(api_router, prefix="/api")

SECRET_KEY = "clave-super-secreta-lectura-rayos"
ALGORITHM = "HS256"

# ==================== TAREAS EN SEGUNDO PLANO (ZIP IMPORT) ====================
# Guardará el estado de las tareas de importación masiva en memoria
import_tasks: Dict[str, Dict] = {}

# ==================== DEPENDENCIAS Y CONTROLADORES DE USUARIO ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: int, email: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)  # 60 minutos de expiración
    return jwt.encode({"sub": str(user_id), "email": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7 días de expiración
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Sesión no iniciada (Token no encontrado)")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token no válido")
        
        # Buscar usuario en base de datos SQLite
        db = next(get_db())
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, role, rayos_balance FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        user = dict(row)
        user["_id"] = str(user["id"])  # Para compatibilidad con tu código anterior
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token no válido")

# ==================== MODELOS PYDANTIC ====================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BookCreate(BaseModel):
    title: str
    author_name: str
    category: str
    price: float = 0.0
    content: str = ""

class BookUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    cover_image_url: Optional[str] = None

class RayosTransaction(BaseModel):
    amount: int
    type: str
    description: str

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str

# ==================== RUTAS DE AUTENTICACIÓN ====================

@api_router.post("/register")
async def register(user_data: UserRegister, response: Response):
    db = next(get_db())
    cursor = db.cursor()
    
    # Comprobar si el usuario existe
    cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed = hash_password(user_data.password)
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        cursor.execute(
            "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at) VALUES (?, ?, ?, 'user', 100, ?)",
            (user_data.name, user_data.email, hashed, now)
        )
        db.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")
    
    # Crear Tokens
    access_token = create_access_token(user_id, user_data.email)
    refresh_token = create_refresh_token(user_id)
    
    # Configurar cookies
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "_id": str(user_id),
        "id": str(user_id),
        "email": user_data.email,
        "name": user_data.name,
        "role": "user",
        "rayos_balance": 100
    }

@api_router.post("/login")
async def login(login_data: UserLogin, response: Response):
    db = next(get_db())
    cursor = db.cursor()
    
    cursor.execute("SELECT id, name, email, hashed_password, role, rayos_balance FROM users WHERE email = ?", (login_data.email,))
    row = cursor.fetchone()
    if not row or not verify_password(login_data.password, row["hashed_password"]):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    
    user_id = row["id"]
    access_token = create_access_token(user_id, row["email"])
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "_id": str(user_id),
        "id": str(user_id),
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "rayos_balance": row["rayos_balance"]
    }

@api_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Sesión cerrada correctamente"}

@api_router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return user

# ==================== RUTAS DE LIBROS ====================

@api_router.get("/books")
async def get_books(category: Optional[str] = None):
    db = next(get_db())
    cursor = db.cursor()
    
    query = "SELECT * FROM books WHERE published = 1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
        
    query += " ORDER BY views DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    books = []
    for r in rows:
        b = dict(r)
        b["_id"] = str(b["id"])  # Para compatibilidad con MongoDB
        books.append(b)
        
    return books

@api_router.get("/books/{book_id}")
async def get_book(book_id: str):
    try:
        db = next(get_db())
        cursor = db.cursor()
        
        # Obtener libro
        cursor.execute("SELECT * FROM books WHERE id = ?", (int(book_id),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book = dict(row)
        
        # Incrementar vistas
        cursor.execute("UPDATE books SET views = views + 1 WHERE id = ?", (int(book_id),))
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
        db = next(get_db())
        cursor = db.cursor()
        
        # Comprobar si existe
        cursor.execute("SELECT id, pdf_path, cover_image_url FROM books WHERE id = ?", (int(book_id),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
            
        # Borrar archivos asociados si los hay
        if row["pdf_path"] and os.path.exists(row["pdf_path"]):
            try: os.remove(row["pdf_path"])
            except: pass
            
        if row["cover_image_url"] and "static/covers" in row["cover_image_url"]:
            cover_filename = row["cover_image_url"].split("/static/covers/")[-1]
            cover_path = os.path.join(STORAGE_COVERS, cover_filename)
            if os.path.exists(cover_path):
                try: os.remove(cover_path)
                except: pass
                
        cursor.execute("DELETE FROM books WHERE id = ?", (int(book_id),))
        db.commit()
        return {"message": "Book deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid book ID or error: {str(e)}")

# ==================== CREACIÓN INDIVIDUAL DE LIBRO ====================

@api_router.post("/books")
async def create_book(
    title: str = Form(...),
    author_name: str = Form(...),
    category: str = Form(...),
    price: float = Form(0.0),
    pdf_file: Optional[UploadFile] = File(None),
    cover_file: Optional[UploadFile] = File(None),
    request: Request = None
):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para crear libros")
        
    db = next(get_db())
    cursor = db.cursor()
    
    # Procesar archivos
    pdf_path = None
    content = "Contenido de texto no disponible."
    cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400" # Por defecto
    
    # Guardar PDF y extraer texto
    if pdf_file:
        import pypdf
        unique_pdf_name = f"{uuid.uuid4()}_{pdf_file.filename}"
        pdf_path = os.path.join(STORAGE_BOOKS, unique_pdf_name)
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)
            
        # Extraer texto usando pypdf
        try:
            reader = pypdf.PdfReader(pdf_path)
            extracted_text = ""
            max_pages = min(len(reader.pages), 30) # Limitar a 30 páginas para evitar colapso de DB
            for i in range(max_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            if extracted_text.strip():
                content = extracted_text
        except Exception as e:
            content = f"Error al extraer texto del PDF: {str(e)}"
            
    # Guardar Foto de Portada
    if cover_file:
        unique_cover_name = f"{uuid.uuid4()}_{cover_file.filename}"
        cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_file.file, buffer)
        # Guardar la URL relativa accesible por HTTP
        cover_url = f"http://localhost:8000/static/covers/{unique_cover_name}"
        
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        cursor.execute("""
        INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0.0, 0, 1, ?)
        """, (title, author_name, content, category, price, cover_url, pdf_path, now))
        db.commit()
        book_id = cursor.lastrowid
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
        "total_reviews": 0
    }

# ==================== PROCESAMIENTO ZIP EN SEGUNDO PLANO ====================

def process_bulk_zip(task_id: str, zip_path: str, default_category: str, default_price: float):
    import pypdf
    db = next(get_db())
    cursor = db.cursor()
    
    task_status = import_tasks[task_id]
    
    try:
        # Carpeta temporal exclusiva de esta tarea
        task_temp_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)
        
        # Descomprimir
        task_status["message"] = "Descomprimiendo archivo ZIP..."
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(task_temp_dir)
            
        # Buscar PDFs e Imágenes
        all_files = []
        for root, dirs, files in os.walk(task_temp_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
                
        pdf_files = [f for f in all_files if f.lower().endswith(".pdf")]
        image_files = [f for f in all_files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        
        task_status["total"] = len(pdf_files)
        task_status["message"] = f"Encontrados {len(pdf_files)} PDFs. Iniciando procesamiento..."
        
        # Mapear nombres de imágenes para emparejamiento por nombre de archivo
        image_map = {}
        for img in image_files:
            basename = os.path.basename(img)
            name_without_ext = os.path.splitext(basename)[0].lower()
            image_map[name_without_ext] = img
            
        for index, pdf in enumerate(pdf_files):
            try:
                filename = os.path.basename(pdf)
                name_without_ext = os.path.splitext(filename)[0]
                
                # Intentar leer metadatos del PDF
                title = None
                author = None
                content = "Contenido de texto no disponible."
                
                try:
                    reader = pypdf.PdfReader(pdf)
                    meta = reader.metadata
                    if meta:
                        title = meta.title
                        author = meta.author
                    
                    # Extraer texto de las primeras 30 páginas
                    extracted_text = ""
                    max_pages = min(len(reader.pages), 30)
                    for p_idx in range(max_pages):
                        page_text = reader.pages[p_idx].extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                    if extracted_text.strip():
                        content = extracted_text
                except:
                    pass
                
                # Asignar valores por defecto si los metadatos fallan
                if not title:
                    title = name_without_ext.replace("_", " ").replace("-", " ").title()
                if not author:
                    author = "Autor Desconocido"
                    
                # Guardar el PDF en almacenamiento local
                unique_pdf_name = f"{uuid.uuid4()}_{filename}"
                final_pdf_path = os.path.join(STORAGE_BOOKS, unique_pdf_name)
                shutil.copy2(pdf, final_pdf_path)
                
                # Intentar emparejar portada
                cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"
                match_name = name_without_ext.lower()
                if match_name in image_map:
                    matched_img = image_map[match_name]
                    img_ext = os.path.splitext(matched_img)[1]
                    unique_cover_name = f"{uuid.uuid4()}_{name_without_ext}{img_ext}"
                    final_cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
                    shutil.copy2(matched_img, final_cover_path)
                    cover_url = f"http://localhost:8000/static/covers/{unique_cover_name}"
                    
                # Guardar en Base de Datos
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0.0, 0, 1, ?)
                """, (title, author, content, default_category, default_price, cover_url, final_pdf_path, now))
                db.commit()
                
                task_status["processed"] += 1
                task_status["message"] = f"Procesados {task_status['processed']}/{task_status['total']} libros."
                
            except Exception as e:
                task_status["errors"].append(f"Error procesando {filename}: {str(e)}")
                
        # Limpiar carpeta temporal y archivo ZIP subido
        try:
            shutil.rmtree(task_temp_dir)
            os.remove(zip_path)
        except:
            pass
            
        task_status["status"] = "completed"
        task_status["message"] = f"Importación masiva completada. Se importaron {task_status['processed']} libros con éxito."
        
    except Exception as e:
        task_status["status"] = "failed"
        task_status["message"] = f"Error crítico en la importación: {str(e)}"
    finally:
        db.close()

# ==================== RUTA DE IMPORTACIÓN MASIVA ====================

@api_router.post("/books/import")
async def import_books(
    file: UploadFile = File(...),
    category: str = Form("General"),
    price: float = Form(0.0),
    background_tasks: BackgroundTasks = None,
    request: Request = None
):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para importar libros")
        
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .zip")
        
    # Guardar el archivo ZIP subido temporalmente
    task_id = str(uuid.uuid4())
    temp_zip_path = os.path.join(TEMP_DIR, f"{task_id}.zip")
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Registrar tarea
    import_tasks[task_id] = {
        "status": "processing",
        "total": 0,
        "processed": 0,
        "errors": [],
        "message": "Guardando archivo y preparando proceso en segundo plano..."
    }
    
    # Lanzar la tarea en segundo plano para no colgar la API
    background_tasks.add_task(process_bulk_zip, task_id, temp_zip_path, category, price)
    
    return {"task_id": task_id, "message": "Importación masiva iniciada en segundo plano"}

@api_router.get("/books/import/status/{task_id}")
async def get_import_status(task_id: str, request: Request):
    await get_current_user(request) # Verificar que está logueado
    if task_id not in import_tasks:
        raise HTTPException(status_code=404, detail="Tarea de importación no encontrada")
    return import_tasks[task_id]

# ==================== RUTAS DE RESEÑAS ====================

@api_router.post("/books/{book_id}/reviews")
async def create_review(book_id: str, review_data: ReviewCreate, request: Request):
    user = await get_current_user(request)
    db = next(get_db())
    cursor = db.cursor()
    
    try:
        # Verificar si el libro existe
        cursor.execute("SELECT id FROM books WHERE id = ?", (int(book_id),))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")
            
        # Verificar si el usuario ya lo reseñó
        cursor.execute("SELECT id FROM reviews WHERE book_id = ? AND user_id = ?", (int(book_id), int(user["_id"])))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ya has dejado una reseña para este libro")
            
        # Crear reseña
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO reviews (book_id, user_id, user_name, rating, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (int(book_id), int(user["_id"]), user["name"], review_data.rating, review_data.comment, now))
        db.commit()
        review_id = cursor.lastrowid
        
        # Calcular nuevo promedio y total
        cursor.execute("SELECT rating FROM reviews WHERE book_id = ?", (int(book_id),))
        ratings = [r["rating"] for r in cursor.fetchall()]
        total_reviews = len(ratings)
        average_rating = sum(ratings) / total_reviews if total_reviews > 0 else 0.0
        
        cursor.execute(
            "UPDATE books SET average_rating = ?, total_reviews = ? WHERE id = ?",
            (round(average_rating, 1), total_reviews, int(book_id))
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
            "created_at": now
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
        db = next(get_db())
        cursor = db.cursor()
        cursor.execute("SELECT * FROM reviews WHERE book_id = ? ORDER BY created_at DESC", (int(book_id),))
        rows = cursor.fetchall()
        
        reviews = []
        for r in rows:
            rev = dict(r)
            rev["id"] = str(rev["id"])
            rev["_id"] = rev["id"]
            reviews.append(rev)
            
        return reviews
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== RUTAS DE RAYOS (PUNTOS) ====================

@api_router.post("/rayos/earn")
async def earn_rayos(transaction_data: RayosTransaction, request: Request):
    user = await get_current_user(request)
    db = next(get_db())
    cursor = db.cursor()
    
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # Registrar transacción
        cursor.execute("""
        INSERT INTO rayos_transactions (user_id, amount, type, description, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (int(user["_id"]), transaction_data.amount, transaction_data.type, transaction_data.description, now))
        
        # Actualizar balance del usuario
        cursor.execute(
            "UPDATE users SET rayos_balance = rayos_balance + ? WHERE id = ?",
            (transaction_data.amount, int(user["_id"]))
        )
        db.commit()
        
        return {"success": True, "message": "Puntos Rayos sumados con éxito"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/rayos/transactions")
async def get_rayos_transactions(request: Request):
    user = await get_current_user(request)
    db = next(get_db())
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM rayos_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (int(user["_id"]),))
    rows = cursor.fetchall()
    
    transactions = []
    for r in rows:
        t = dict(r)
        t["id"] = str(t["id"])
        transactions.append(t)
        
    return transactions

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
