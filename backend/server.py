import os
import uuid
import zipfile
import shutil
import random
import string
import threading
import re
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

import jwt
import bcrypt
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
from pydantic import BaseModel, Field, EmailStr, field_validator

from database import init_db, get_db
import psycopg2
import lectura
from ai_service import process_chat, AIServiceError
import ai_conversations

# Logger del servidor (FASE 8.4): registro mínimo y seguro del endpoint IA.
# Nunca se registran tokens, cookies, contraseñas ni contenido de mensajes.
logger_server = logging.getLogger("aeternum.server")

# ── Directorios de almacenamiento ───────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")
# STORAGE_DIR permite apuntar el almacenamiento a un medio persistente (p. ej.
# el Persistent Disk de Render montado en /var/data/aeternum). Sin la variable
# se mantiene exactamente el comportamiento actual (backend/storage).
STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or DEFAULT_STORAGE_DIR)
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")
STORAGE_VIDEOS = os.path.join(STORAGE_DIR, "videos")
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend_dist")

# Crear directorios ANTES de que FastAPI los monte como StaticFiles
# NOTA: FRONTEND_DIR lo crea el build de npm — no lo creamos aquí
for directory in (STORAGE_BOOKS, STORAGE_COVERS, STORAGE_VIDEOS, TEMP_DIR):
    os.makedirs(directory, exist_ok=True)


def _migrar_storage_legacy():
    """Copia idempotente (NUNCA mueve ni borra) de los archivos del directorio
    por defecto al directorio configurado vía STORAGE_DIR (p. ej. el Persistent
    Disk de Render). Se ejecuta en cada arranque: si el destino ya tiene el
    archivo, no se vuelve a copiar; si el origen no existe, no hace nada."""
    if os.path.abspath(STORAGE_DIR) == os.path.abspath(DEFAULT_STORAGE_DIR):
        return
    for subdir in ("books", "covers", "videos"):
        origen = os.path.join(DEFAULT_STORAGE_DIR, subdir)
        destino = os.path.join(STORAGE_DIR, subdir)
        if not os.path.isdir(origen):
            continue
        os.makedirs(destino, exist_ok=True)
        for nombre in os.listdir(origen):
            ruta_origen = os.path.join(origen, nombre)
            if os.path.isfile(ruta_origen):
                ruta_destino = os.path.join(destino, nombre)
                if not os.path.exists(ruta_destino):
                    try:
                        shutil.copy2(ruta_origen, ruta_destino)
                    except OSError:
                        pass


_migrar_storage_legacy()


def _normalizar_texto(texto: str) -> str:
    """Normaliza título/autor para comparación: minúsculas, sin acentos, sin puntuación extra."""
    if not texto:
        return ""
    import unicodedata
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", "", texto.lower())
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _calcular_hash_pdf(pdf_path: str) -> str:
    """Calcula SHA-256 del archivo PDF."""
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _verificar_duplicado(cursor, title: str, author_name: str, content: str, pdf_path: str = None, pdf_hash: str = None) -> Optional[int]:
    """
    Verifica si ya existe un libro duplicado.
    Prioridad:
    1. Si hay PDF: buscar por SHA-256 del PDF (duplicado real de archivo).
       Si el hash coincide → duplicado real (mismo archivo).
       Si el hash NO coincide → NO es duplicado, permitir aunque título/autor coincidan.
    2. Si NO hay PDF (pdf_hash is None): buscar por título+autor normalizado (fallback para contenido sin PDF).
    Retorna el ID del libro existente si hay duplicado, None si no.
    """
    # 1. Si hay PDF, buscar por hash. Si coincide → duplicado.
    # Si NO coincide → NO es duplicado, NO verificar título+autor.
    if pdf_hash:
        cursor.execute(
            "SELECT id, pdf_path FROM books WHERE pdf_path IS NOT NULL",
        )
        for row in cursor.fetchall():
            existing_pdf = _resolver_pdf_path(row["pdf_path"])
            if existing_pdf and os.path.isfile(existing_pdf):
                existing_hash = _calcular_hash_pdf(existing_pdf)
                if existing_hash == pdf_hash:
                    return row["id"]
        # Hash no coincidió con ningún PDF existente → NO es duplicado
        return None

    # 2. Fallback: solo si NO hay PDF (pdf_hash is None), verificar título+autor
    title_norm = _normalizar_texto(title)
    author_norm = _normalizar_texto(author_name)
    cursor.execute(
        """
        SELECT id, title, author_name, content, pdf_path
        FROM books
        WHERE title IS NOT NULL AND author_name IS NOT NULL
        """,
    )
    for row in cursor.fetchall():
        if _normalizar_texto(row["title"]) == title_norm and _normalizar_texto(row["author_name"]) == author_norm:
            return row["id"]

    return None


def _resolver_pdf_path(pdf_path):
    """Resuelve un pdf_path almacenado en la BD contra el almacenamiento actual.

    - Ruta absoluta que existe -> se usa tal cual (compatibilidad con la BD actual).
    - Ruta absoluta inexistente -> se intenta el nombre de archivo dentro de
      STORAGE_BOOKS (cubre PDFs migrados a un nuevo directorio persistente).
    - Ruta relativa -> se busca dentro de STORAGE_BOOKS.
    Devuelve la ruta resuelta o None si no existe ningún archivo."""
    if not pdf_path:
        return None
    if os.path.isabs(pdf_path) and os.path.isfile(pdf_path):
        return pdf_path
    candidata = os.path.join(STORAGE_BOOKS, os.path.basename(pdf_path))
    if os.path.isfile(candidata):
        return candidata
    return None

# ── Configuración de Correo Electrónico (SMTP Gmail) ──────────────────────────
import urllib.request
import json
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

def send_email_async(to_email: str, subject: str, html_content: str):
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AeternumBackend/1.0"
        }
        data = {
            "from": "AETERNUM <soporte@aeternumlibrary.com>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            print("Correo Resend enviado con éxito:", response.read())
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'read'):
            try:
                error_msg = e.read().decode()
            except:
                pass
        print(f"Error enviando correo por Resend a {to_email}: {error_msg}")
        traceback.print_exc()
        raise Exception(f"Fallo al enviar correo: {error_msg}")

def send_mass_email_async(bcc_emails: list, subject: str, html_content: str):
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AeternumBackend/1.0"
        }
        data = {
            "from": "AETERNUM <soporte@aeternumlibrary.com>",
            "to": ["soporte@aeternumlibrary.com"],
            "bcc": bcc_emails,
            "subject": subject,
            "html": html_content
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            print("Correo Masivo Resend enviado con éxito:", response.read())
    except Exception as e:
        print(f"Error enviando correo masivo por Resend: {e}")
        traceback.print_exc()

# ── Inicializar base de datos ────────────────────────────────────────────────
init_db()

try:
    import migrate_fix_duplicates
    migrate_fix_duplicates.migrate()
except Exception as e:
    print(f"Error ejecutando migración de duplicados: {e}")

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

# FASE 2: el backfill de páginas corre en segundo plano (daemon) para no
# bloquear el arranque de FastAPI con bibliotecas grandes. La migración sigue
# siendo standalone e idempotente.
def _run_fase2_lectura_migration():
    try:
        import migrate_db_fase2_lectura
        migrate_db_fase2_lectura.migrate()
    except Exception as e:
        print(f"Error ejecutando migración Fase 2 (Lectura): {e}")

threading.Thread(target=_run_fase2_lectura_migration, daemon=True).start()

# Foro Estudiantil: migración idempotente
try:
    import migrate_db_foro
    migrate_db_foro.migrate()
except Exception as e:
    print(f"Error ejecutando migración del foro: {e}")

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


# ── Economía de Rayos (FASE 1) ────────────────────────────────────────────────
# Únicos tipos de transacción permitidos. El backend siempre decide el tipo,
# el monto y la descripción (el cliente nunca los envía).
VALID_RAYOS_TYPES = frozenset({
    "registration_reward",
    "reading_reward",
    "daily_goal_reward",
    "book_completion_reward",
    "course_reward",
    "competition_reward",
    "purchase_reward",
    "donation_sent",
    "donation_received",
    "donation_burn",
    # FASE 8.5: identificador económico de IA PREPARADO (sin precios activos).
    # Solo se usa cuando exista un costo definido para una operación de IA;
    # con costos PENDIENTES, la economía permanece inactiva y nunca cobra.
    "ai_request_cost",
})

REGISTRATION_REWARD_AMOUNT = 100
READING_REWARD_AMOUNT = 10
DAILY_GOAL_PAGES = 15
DAILY_GOAL_REWARD_AMOUNT = 20
MIN_SECONDS_BETWEEN_PAGE_REPORTS = 5
MIN_COURSE_REWARD_SECONDS = 30
MAX_REGISTRATIONS_PER_IP_PER_DAY = 3
MAX_COMPETITION_TIME_MS = 7200000


def compute_donation_split(amount: int):
    """Función pura de la quema del 10%: el receptor recibe amount - 10%,
    la diferencia se quema (nunca es progreso de nadie)."""
    burned = amount // 10
    received = amount - burned
    return received, burned


def _record_rayos_transaction(
    cursor,
    user_id,
    amount: int,
    txn_type: str,
    description: str,
    book_id=None,
    course_id=None,
    competition_id=None,
):
    """Registra una transacción de Rayos. El caller ejecuta el commit único."""
    if txn_type not in VALID_RAYOS_TYPES:
        raise ValueError(f"Tipo de transacción Rayos no válido: {txn_type}")
    cursor.execute(
        """
        INSERT INTO rayos_transactions
            (user_id, amount, type, description, book_id, course_id, competition_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            amount,
            txn_type,
            description,
            book_id,
            course_id,
            competition_id,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def _credit_rayos(
    cursor,
    user_id: int,
    amount: int,
    txn_type: str,
    description: str,
    book_id=None,
    course_id=None,
    competition_id=None,
):
    """Acredita Rayos al saldo y al progreso histórico (mismo monto) y lo
    registra en rayos_transactions. Devuelve el nuevo saldo."""
    cursor.execute(
        """
        UPDATE users
        SET rayos_balance = rayos_balance + %s, historical_rayos = historical_rayos + %s
        WHERE id = %s
        RETURNING rayos_balance
        """,
        (amount, amount, user_id),
    )
    balance_row = cursor.fetchone()
    _record_rayos_transaction(
        cursor,
        user_id,
        amount,
        txn_type,
        description,
        book_id=book_id,
        course_id=course_id,
        competition_id=competition_id,
    )
    return balance_row["rayos_balance"]


def _debit_rayos_atomic(
    cursor,
    user_id: int,
    amount: int,
    txn_type: str,
    description: str,
    book_id=None,
    course_id=None,
    competition_id=None,
):
    """Débito atómico condicional: solo debita si el saldo es suficiente
    (evita TOCTOU y saldos negativos). Devuelve el nuevo saldo o None si
    el saldo era insuficiente."""
    cursor.execute(
        """
        UPDATE users
        SET rayos_balance = rayos_balance - %s
        WHERE id = %s AND rayos_balance >= %s
        RETURNING rayos_balance
        """,
        (amount, user_id, amount),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    _record_rayos_transaction(
        cursor,
        user_id,
        -amount,
        txn_type,
        description,
        book_id=book_id,
        course_id=course_id,
        competition_id=competition_id,
    )
    return row["rayos_balance"]


# ── Modelos Pydantic ─────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    # FASE 4: código QR opcional capturado por el frontend (?ref=). El backend
    # lo vuelve a validar (nunca se confía en el frontend): solo formato
    # básico; si es None, vacío, inválido o el QR no existe/está inactivo, el
    # registro continúa normal sin asociación (referred_by_qr_id = NULL).
    ref: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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

class CompetitionAnswerSubmit(BaseModel):
    question_id: int
    selected: str

class CompetitionSubmit(BaseModel):
    answers: List[CompetitionAnswerSubmit]
    time_taken_ms: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str


# ── FASE 6: modelos administrativos de códigos QR ─────────────────────────────
# extra="forbid": el body jamás acepta campos administrativos arbitrarios
# (role, is_active, etc.) en endpoints donde no corresponden.
class QrCodeCreate(BaseModel):
    model_config = {"extra": "forbid"}

    code: str
    name: str

    @field_validator("code", "name", mode="before")
    @classmethod
    def _deben_ser_texto(cls, v):
        if not isinstance(v, str):
            raise ValueError("Debe ser texto")
        return v


class QrCodePatch(BaseModel):
    model_config = {"extra": "forbid"}

    is_active: bool

    @field_validator("is_active", mode="before")
    @classmethod
    def _booleano_real(cls, v):
        if not isinstance(v, bool):
            raise ValueError("is_active debe ser un booleano real (true/false)")
        return v


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
        "storage_dir": STORAGE_DIR,
        "storage_books": STORAGE_BOOKS,
        "storage_dir_exists": os.path.isdir(STORAGE_DIR),
        "storage_books_exists": os.path.isdir(STORAGE_BOOKS),
        "files_in_frontend_dist": [],
        "files_in_storage_books": [],
        "db_tables": [],
        "db_error": None,
    }
    if os.path.isdir(FRONTEND_DIR):
        for root, dirs, files in os.walk(FRONTEND_DIR):
            for f in files:
                result["files_in_frontend_dist"].append(os.path.join(root, f))
    if os.path.isdir(STORAGE_BOOKS):
        result["files_in_storage_books"] = sorted(os.listdir(STORAGE_BOOKS))
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


REF_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def _resolve_active_qr_id(cursor, ref):
    """Resuelve el id interno de qr_codes para un ref de registro (FASE 4).

    Devuelve el id solo si ref tiene formato válido y el QR existe y está
    activo. En cualquier otro caso (None, vacío, formato inválido, QR
    inexistente o inactivo) devuelve None y el registro continúa sin
    asociación. El ref jamás influye en role ni en Rayos. Queries siempre
    parametrizadas; no se crea ningún QR nuevo aquí."""
    if not ref or not isinstance(ref, str):
        return None
    if not REF_CODE_PATTERN.fullmatch(ref):
        return None
    cursor.execute(
        "SELECT id FROM qr_codes WHERE code = %s AND is_active = TRUE",
        (ref,),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


@api_router.post("/register")
async def register(user_data: UserRegister, response: Response, request: Request):
    db = get_db()
    cursor = db.cursor()

    user_ip = (request.client.host if request.client else "unknown")

    # Protección contra abuso: máx. 3 cuentas por IP cada 24 horas
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM users WHERE registration_ip = %s AND created_at >= %s",
        (user_ip, cutoff),
    )
    ip_count_row = cursor.fetchone()
    ip_count = ip_count_row["cnt"] if ip_count_row else 0
    if ip_count >= MAX_REGISTRATIONS_PER_IP_PER_DAY:
        db.close()
        raise HTTPException(status_code=429, detail="Demasiados registros desde esta IP. Intenta más tarde.")

    cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    hashed = hash_password(user_data.password)
    now = datetime.now(timezone.utc).isoformat()

    base_username = "".join(c for c in user_data.name.lower() if c.isalnum())
    random_suffix = "".join(random.choices(string.digits, k=4))
    username = f"{base_username}{random_suffix}"

    # FASE 4: asociación al QR de referencia. Se resuelve DENTRO de la misma
    # transacción de creación del usuario: si el ref es válido y el QR está
    # activo se guarda su id en users.referred_by_qr_id; si no, queda NULL.
    # El role y la recompensa los fija siempre el servidor.
    try:
        qr_id = _resolve_active_qr_id(cursor, user_data.ref)
        cursor.execute(
            "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at, username, registration_ip, referred_by_qr_id) VALUES (%s, %s, %s, 'user', 0, %s, %s, %s, %s) RETURNING id",
            (user_data.name, user_data.email, hashed, now, username, user_ip, qr_id),
        )
        user_id = cursor.fetchone()["id"]

        # Recompensa de registro decidida por el backend y registrada en el libro mayor
        new_balance = _credit_rayos(
            cursor,
            user_id,
            REGISTRATION_REWARD_AMOUNT,
            "registration_reward",
            "Recompensa por crear tu cuenta en AETERNUM",
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")
    finally:
        db.close()

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
        "rayos_balance": new_balance,
    }


@api_router.post("/qr/{code}/visit")
async def qr_visit(code: str, request: Request):
    """Tracking de visita de QR (FASE 5).

    Contabiliza una visita solo si el QR existe y está activo; si no, NO crea
    ninguna visita (respuesta 404 genérica). Exclusivamente tracking: no crea
    ni activa QRs, no toca users, no entrega privilegios ni Rayos. Deduplicación
    garantizada por UNIQUE(qr_id, ip, visit_date) + ON CONFLICT DO NOTHING:
    1 IP + 1 QR + 1 día = 1 visita. Queries parametrizadas."""
    if not REF_CODE_PATTERN.fullmatch(code):
        raise HTTPException(status_code=404, detail="Código QR no encontrado o inactivo")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id FROM qr_codes WHERE code = %s AND is_active = TRUE",
            (code,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Código QR no encontrado o inactivo")
        ip = (request.client.host if request.client else "unknown")
        visit_date = datetime.now(timezone.utc).date().isoformat()
        created_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO qr_visits (qr_id, ip, visit_date, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (qr_id, ip, visit_date) DO NOTHING
            """,
            (row["id"], ip, visit_date, created_at),
        )
        db.commit()
        return {"status": "ok", "counted": bool(cursor.rowcount > 0)}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al registrar la visita")
    finally:
        db.close()


# ── Panel administrativo de códigos QR (FASE 6) ───────────────────────────────
# Mismo patrón de autorización que el resto del panel: get_current_user + check
# de role admin. Un usuario normal (o no autenticado) jamás llega a la BD.

@api_router.get("/admin/qr-codes")
async def admin_list_qr_codes(request: Request):
    """Listado administrativo de códigos QR (FASE 6).

    Solo administradores. Devuelve cada QR con sus estadísticas agregadas
    (visitas únicas registradas y usuarios asociados por el QR) calculadas en
    una sola consulta agrupada (sin N+1). No expone IPs de visitantes.
    SQL parametrizado."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT q.id, q.code, q.name, q.is_active, q.created_at,
                   COUNT(DISTINCT v.id) AS visits_count,
                   COUNT(DISTINCT u.id) AS registrations_count
            FROM qr_codes q
            LEFT JOIN qr_visits v ON v.qr_id = q.id
            LEFT JOIN users u ON u.referred_by_qr_id = q.id
            GROUP BY q.id, q.code, q.name, q.is_active, q.created_at
            ORDER BY q.id
            """
        )
        rows = cursor.fetchall()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al listar los códigos QR")
    finally:
        db.close()

    return [
        {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "visits_count": row["visits_count"],
            "registrations_count": row["registrations_count"],
            "registration_url": f"/register?ref={row['code']}",
        }
        for row in rows
    ]


@api_router.post("/admin/qr-codes")
async def admin_create_qr_code(payload: QrCodeCreate, request: Request):
    """Crea un código QR (FASE 6). Solo administradores.

    Valida formato del código (^[A-Za-z0-9_-]{1,32}$), nombre obligatorio con
    longitud razonable y ausencia de duplicados. El QR se crea SIEMPRE activo
    (is_active = TRUE); el campo is_active no se acepta del body. created_at
    usa el mismo formato ISO UTC del resto del proyecto. SQL parametrizado."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    code = payload.code.strip()
    name = payload.name.strip()

    if not code:
        raise HTTPException(status_code=400, detail="El código es obligatorio")
    if not REF_CODE_PATTERN.fullmatch(code):
        raise HTTPException(
            status_code=400,
            detail="El código debe tener entre 1 y 32 caracteres: letras, números, guiones (-) o guiones bajos (_)",
        )
    if not name:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if len(name) > 200:
        raise HTTPException(status_code=400, detail="El nombre es demasiado largo (máximo 200 caracteres)")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id FROM qr_codes WHERE code = %s", (code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="El código QR ya existe")

        created_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO qr_codes (code, name, is_active, created_at) VALUES (%s, %s, TRUE, %s) RETURNING id",
            (code, name, created_at),
        )
        qr_id = cursor.fetchone()["id"]
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear el código QR")
    finally:
        db.close()

    return {"id": qr_id, "code": code, "name": name, "is_active": True, "created_at": created_at}


@api_router.patch("/admin/qr-codes/{qr_id}")
async def admin_set_qr_code_active(qr_id: int, payload: QrCodePatch, request: Request):
    """Activa o desactiva un código QR (FASE 6). Solo administradores.

    Únicamente cambia is_active: no edita code/name, no elimina el QR y no
    toca visitas ni usuarios. Al desactivar, /register?ref=... deja de asociar
    nuevos usuarios y /api/qr/{code}/visit deja de registrar visitas (ambos ya
    filtran por is_active = TRUE); los datos históricos permanecen intactos.
    SQL parametrizado."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id FROM qr_codes WHERE id = %s", (qr_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Código QR no encontrado")

        cursor.execute(
            "UPDATE qr_codes SET is_active = %s WHERE id = %s",
            (payload.is_active, qr_id),
        )
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar el código QR")
    finally:
        db.close()

    return {"id": qr_id, "is_active": payload.is_active}


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

    # Debug logging para diagnosticar problema de reset-password
    if row:
        stored_hash = row["hashed_password"]
        try:
            pwd_check = verify_password(login_data.password, stored_hash)
        except Exception as verify_err:
            print(f"[LOGIN-DEBUG] Error en verify_password: {verify_err}")
            pwd_check = False
        print(f"[LOGIN-DEBUG] Usuario ID={row['id']}, email={row['email']}")
        print(f"[LOGIN-DEBUG] Hash almacenado empieza con: {stored_hash[:25]}...")
        print(f"[LOGIN-DEBUG] Verificacion resultado: {pwd_check}")
    else:
        pwd_check = False
        print(f"[LOGIN-DEBUG] No se encontro usuario con email: {login_data.email}")

    if not row or not pwd_check:
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
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Este correo NO está registrado en la base de datos. Asegúrate de haberlo escrito correctamente.")

        token = str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        cursor.execute(
            "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
            (token, expires_at, row["id"])
        )
        db.commit()
        print(f"[FORGOT-PASSWORD] Token asignado a Usuario ID={row['id']}, email={req.email}, token={token[:8]}...")

        reset_link = f"https://aeternumlibrary.com/reset-password?token={token}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; text-align: center;">
            <h2 style="color: #D92B2B;">AETERNUM - Recuperación de Contraseña</h2>
            <p>Hemos recibido una solicitud para cambiar tu contraseña.</p>
            <p>Haz clic en el siguiente botón para restablecerla. El enlace expirará en 1 hora.</p>
            <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; margin: 20px 0; background-color: #D92B2B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Restablecer Contraseña</a>
            <p style="color: #666; font-size: 12px;">Si no solicitaste esto, puedes ignorar este correo.</p>
        </div>
        """
        try:
            send_email_async(req.email, "Recupera tu contraseña en AETERNUM", html_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return {"message": "Si el correo existe, se enviará un enlace de recuperación."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        db.close()


@api_router.get("/test-email")
async def test_email_smtp():
    import traceback
    to_email = "yamildiazzz01@gmail.com"
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AeternumBackend/1.0"
        }
        data = {
            "from": "AETERNUM <soporte@aeternumlibrary.com>",
            "to": [to_email],
            "subject": "Prueba AETERNUM desde Render (Resend)",
            "html": "Si ves esto, el servidor de correos (Resend) funciona desde Render."
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            return {"status": "SUCCESS", "message": "Correo enviado con éxito por Resend"}
    except Exception as e:
        error_details = str(e)
        if hasattr(e, 'read'):
            try:
                error_details = e.read().decode()
            except:
                pass
        return {"status": "ERROR", "error": error_details, "traceback": traceback.format_exc()}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@api_router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token = %s", (req.token,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Enlace inválido o ya utilizado.")

        user_id = row["id"]

        # PostgreSQL TIMESTAMP devuelve un objeto datetime directamente
        expires_at = row["reset_token_expiry"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        # Asegurar que ambos datetimes sean comparables (naive o aware)
        if expires_at.tzinfo is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            now = datetime.now(timezone.utc)

        if now > expires_at:
            raise HTTPException(status_code=400, detail="El enlace ha expirado.")

        hashed_pw = hash_password(req.new_password)
        cursor.execute(
            "UPDATE users SET hashed_password = %s, reset_token = NULL, reset_token_expiry = NULL WHERE id = %s",
            (hashed_pw, user_id)
        )
        rows_affected = cursor.rowcount
        db.commit()
        print(f"[RESET-PASSWORD] Usuario ID={user_id} actualizado. Filas afectadas: {rows_affected}. Hash nuevo empieza con: {hashed_pw[:20]}...")

        if rows_affected == 0:
            raise HTTPException(status_code=500, detail="No se pudo actualizar la contraseña.")

        return {"message": "Contraseña actualizada exitosamente. Redirigiendo al login..."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"[RESET-PASSWORD] Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud: {str(e)}")
    finally:
        db.close()

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

class RoleUpdateRequest(BaseModel):
    role: str

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: int, req: RoleUpdateRequest, request: Request):
    current_user = await get_current_user(request)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    valid_roles = ["user", "autor", "admin"]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Rol inválido")

    db = get_db()
    cursor = db.cursor()

    # Obtener rol actual del objetivo
    cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    target = cursor.fetchone()
    if not target:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if target["role"] == "admin":
        db.close()
        raise HTTPException(status_code=400, detail="No puedes modificar el rol de otro Administrador")

    cursor.execute("UPDATE users SET role = %s WHERE id = %s", (req.role, user_id))
    db.commit()
    db.close()
    return {"message": "Rol actualizado exitosamente"}

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
        if row["uploader_id"] is not None:
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
        if row["uploader_id"] is not None:
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
async def get_book(book_id: str, request: Request):
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM books WHERE id = %s", (int(book_id),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found")

        book = dict(row)
        # Un tercero (o un no autenticado) no puede ver un libro pendiente
        # solo conociendo su ID: solo publicado, admin o el propio uploader.
        user = await get_current_user_optional(request)
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")

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

class InteractRequest(BaseModel):
    action: str

@api_router.post("/books/{book_id}/interact")
async def interact_book(book_id: int, req: InteractRequest, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")

    if req.action not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="Acción inválida")

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT interaction_type FROM book_interactions WHERE book_id = %s AND user_id = %s", (book_id, user["id"]))
        existing = cursor.fetchone()

        if existing:
            if existing["interaction_type"] == req.action:
                # Same action -> toggle off (remove)
                cursor.execute("DELETE FROM book_interactions WHERE book_id = %s AND user_id = %s", (book_id, user["id"]))
                cursor.execute(f"UPDATE books SET {req.action}s = GREATEST({req.action}s - 1, 0) WHERE id = %s", (book_id,))
                action_result = None
            else:
                # Switch action
                cursor.execute("UPDATE book_interactions SET interaction_type = %s WHERE book_id = %s AND user_id = %s", (req.action, book_id, user["id"]))
                old_action = existing["interaction_type"]
                cursor.execute(f"UPDATE books SET {req.action}s = {req.action}s + 1, {old_action}s = GREATEST({old_action}s - 1, 0) WHERE id = %s", (book_id,))
                action_result = req.action
        else:
            # New action
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("INSERT INTO book_interactions (book_id, user_id, interaction_type, created_at) VALUES (%s, %s, %s, %s)", (book_id, user["id"], req.action, now))
            cursor.execute(f"UPDATE books SET {req.action}s = {req.action}s + 1 WHERE id = %s", (book_id,))
            action_result = req.action

        db.commit()

        # Get updated counts
        cursor.execute("SELECT likes, dislikes FROM books WHERE id = %s", (book_id,))
        counts = cursor.fetchone()
        return {"interaction": action_result, "likes": counts["likes"], "dislikes": counts["dislikes"]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@api_router.get("/books/{book_id}/interaction")
async def get_book_interaction(book_id: int, request: Request):
    user = await get_current_user(request)
    if not user:
        return {"interaction": None}

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT interaction_type FROM book_interactions WHERE book_id = %s AND user_id = %s", (book_id, user["id"]))
    row = cursor.fetchone()
    db.close()

    if row:
        return {"interaction": row["interaction_type"]}
    return {"interaction": None}


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

        pdf_resuelto = _resolver_pdf_path(row["pdf_path"])
        if pdf_resuelto:
            try:
                os.remove(pdf_resuelto)
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
        cover_path = os.path.join(STORAGE_COVERS, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
        updates.append("cover_image_url = %s")
        params.append(f"/static/covers/{cover_filename}")

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
    pdf_resuelto = _resolver_pdf_path(book["pdf_path"])
    if pdf_resuelto:
        return FileResponse(
            pdf_resuelto,
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


MAX_PDF_SIZE_MB = 50
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024


def _validar_archivo_pdf(pdf_file: Optional[UploadFile]) -> None:
    """Valida el PDF por contenido (magic bytes %PDF) y por tamaño, NUNCA por
    extensión. HTTP 413 si excede el límite; HTTP 422 si no es un PDF real."""
    if not pdf_file or not pdf_file.filename:
        raise HTTPException(status_code=422, detail="Debes adjuntar un archivo PDF del libro.")

    total = 0
    cabecera = b""
    while True:
        chunk = pdf_file.file.read(64 * 1024)
        if not chunk:
            break
        if total < 1024:
            cabecera += chunk[: 1024 - total]
        total += len(chunk)
        if total > MAX_PDF_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el límite de {MAX_PDF_SIZE_MB} MB.",
            )

    if b"%PDF" not in cabecera[:1024]:
        raise HTTPException(status_code=422, detail="El archivo no es un PDF válido.")

    pdf_file.file.seek(0)


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

    # Validación de PDF por contenido (magic bytes) y tamaño, antes de escribir nada.
    _validar_archivo_pdf(pdf_file)

    db = get_db()
    cursor = db.cursor()

    pdf_path = None
    cover_path = None
    content = lectura.CONTENIDO_NO_DISPONIBLE
    cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"

    # FASE 2: extracción por páginas (sin límite) + detección de capítulos.
    # El contenido completo se mantiene en books.content para compatibilidad.
    paginas_libro = []
    capitulos_libro = []

    try:
        unique_pdf_name = f"{uuid.uuid4()}_{pdf_file.filename}"
        pdf_path = os.path.join(STORAGE_BOOKS, unique_pdf_name)
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        # PASO 3: pipeline central (extracción + validación). Un PDF cuya
        # extracción falla, produce placeholder, basura, contenido patológico
        # o insuficiente se RECHAZA: no se publica ni queda nada a medias.
        procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf_path, fuente="pdf")
        validacion = procesado["validacion"]
        if not validacion["valid"]:
            raise HTTPException(
                status_code=422,
                detail="Libro rechazado: el archivo no pudo procesarse correctamente. "
                + "; ".join(validacion["errors"]),
            )
        content = procesado["content"]
        paginas_libro = procesado["paginas"]
        capitulos_libro = procesado["capitulos"]

        # Verificar duplicado ANTES de insertar (título+autor normalizado o hash de PDF)
        pdf_hash = _calcular_hash_pdf(pdf_path) if pdf_path and os.path.isfile(pdf_path) else None
        dup_id = _verificar_duplicado(cursor, title, author_name, content, pdf_path, pdf_hash)
        if dup_id:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un libro con el mismo contenido (ID: {dup_id}). No se permiten duplicados.",
            )

        if cover_file:
            unique_cover_name = f"{uuid.uuid4()}_{cover_file.filename}"
            cover_path = os.path.join(STORAGE_COVERS, unique_cover_name)
            with open(cover_path, "wb") as buffer:
                shutil.copyfileobj(cover_file.file, buffer)
            cover_url = f"/static/covers/{unique_cover_name}"

        now = datetime.now(timezone.utc).isoformat()

        # Admin y autor publican directamente; el resto queda pendiente de aprobación.
        published_status = 1 if user["role"] in ("admin", "autor") else 0

        # Transacción única: INSERT + páginas + capítulos + page_count/paginated_at
        # se confirman juntos; si cualquier paso falla, rollback completo (sin
        # libros fantasma ni libros sin páginas).
        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at, uploader_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, %s, %s, %s)
            RETURNING id
            """,
            (title, author_name, content, category, price, cover_url, pdf_path, published_status, now, user["id"]),
        )
        book_id = cursor.fetchone()["id"]

        if paginas_libro:
            _guardar_paginas_libro(cursor, book_id, paginas_libro, capitulos_libro)
            cursor.execute(
                "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
                (len(paginas_libro), now, book_id),
            )

        db.commit()
    except HTTPException:
        db.rollback()
        # Sin filas huérfanas en BD (rollback) y sin archivos huérfanos en disco
        # (el PDF rechazado por validación se elimina de STORAGE_BOOKS).
        for ruta in (pdf_path, cover_path):
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass
        raise
    except Exception as e:
        db.rollback()
        # Sin filas huérfanas en BD (rollback) y sin archivos huérfanos en disco.
        for ruta in (pdf_path, cover_path):
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass
        raise HTTPException(status_code=500, detail=f"Error al guardar el libro: {str(e)}")
    finally:
        db.close()

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
        "published": published_status,
        "status": "published" if published_status == 1 else "pending",
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
                # 1. Validación REAL del archivo (magic bytes %PDF), nunca por extensión.
                with open(pdf, "rb") as f:
                    cabecera = f.read(1024)
                if b"%PDF" not in cabecera[:1024]:
                    task_status["errors"].append(
                        f"Archivo no es un PDF válido (sin magic bytes %PDF): {filename}"
                    )
                    continue

                # 2. Pipeline central: extracción + validación. Extracción
                #    fallida, placeholder, basura o contenido patológico ->
                #    el libro NO se publica (nada de autopublicar fallos).
                procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf, fuente="pdf")
                validacion = procesado["validacion"]
                if not validacion["valid"]:
                    task_status["errors"].append(
                        f"Contenido rechazado en {filename}: "
                        + "; ".join(validacion["errors"])
                    )
                    continue
                content = procesado["content"]
                paginas_libro = procesado["paginas"]
                capitulos_libro = procesado["capitulos"]

                # 3. Metadatos (título/autor) desde el PDF; fallan sin romper.
                title = None
                author = None
                try:
                    reader = pypdf.PdfReader(pdf)
                    meta = reader.metadata
                    if meta:
                        title = meta.title
                        author = meta.author
                except Exception:
                    pass

                if not title:
                    title = name_without_ext.replace("_", " ").replace("-", " ").title()
                if not author:
                    author = "Autor Desconocido"

                # Verificar duplicado ANTES de insertar
                pdf_hash = _calcular_hash_pdf(pdf) if pdf and os.path.isfile(pdf) else None
                dup_id = _verificar_duplicado(cursor, title, author, content, pdf, pdf_hash)
                if dup_id:
                    task_status["errors"].append(
                        f"Duplicado detectado en {filename}: ya existe libro ID {dup_id} con mismo contenido"
                    )
                    continue

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
                    RETURNING id
                    """,
                    (title, author, content, default_category, default_price, cover_url, final_pdf_path, now),
                )
                new_book_id = cursor.fetchone()["id"]
                if paginas_libro:
                    _guardar_paginas_libro(cursor, new_book_id, paginas_libro, capitulos_libro)
                    cursor.execute(
                        "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
                        (len(paginas_libro), now, new_book_id),
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
            (int(book_id), int(user["id"])),
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
            (int(book_id), int(user["id"]), user["name"], review_data.rating, review_data.comment, now),
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
            "user_id": user["id"],
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


@api_router.post("/books/{book_id}/reading-reward")
async def reading_reward(book_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id, title, published, uploader_id FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()
    if not book:
        db.close()
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    if not _puede_acceder_libro(book, user):
        db.close()
        raise HTTPException(status_code=403, detail="Este libro no está publicado")

    # Anti-farm: una sola recompensa de lectura por libro y por día
    today_prefix = datetime.now(timezone.utc).date().isoformat()
    cursor.execute(
        "SELECT id FROM rayos_transactions WHERE user_id = %s AND type = 'reading_reward' AND book_id = %s AND created_at LIKE %s",
        (user["id"], book_id, f"{today_prefix}%"),
    )
    if cursor.fetchone():
        db.close()
        return {"rewarded": False, "amount": 0, "balance": user["rayos_balance"], "message": "Ya reclamaste la recompensa de lectura para este libro hoy"}

    try:
        new_balance = _credit_rayos(
            cursor,
            user["id"],
            READING_REWARD_AMOUNT,
            "reading_reward",
            f"Recompensa por leer '{book['title']}'",
            book_id=book_id,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return {
        "rewarded": True,
        "amount": READING_REWARD_AMOUNT,
        "balance": new_balance,
        "message": f"¡Has ganado {READING_REWARD_AMOUNT} Rayos por leer!",
    }


# ── FASE 2: Lectura por páginas y meta diaria ────────────────────────────────
# El backend decide TODO sobre Rayos: página válida, progreso, páginas únicas,
# 15/15 y la recompensa. El frontend solo reporta qué página está leyendo.

def _puede_acceder_libro(book, user):
    """Un libro se puede leer si está publicado, si el usuario es admin o si
    el usuario es el propio uploader (previsualización de libros pendientes).
    El resto (terceros y no autenticados) no puede leer un libro pendiente."""
    if book["published"]:
        return True
    if not user:
        return False
    if user["role"] == "admin":
        return True
    return book.get("uploader_id") is not None and book["uploader_id"] == user["id"]


def _guardar_paginas_libro(cursor, book_id, paginas, capitulos):
    capitulo_ids = {}
    for cap in capitulos:
        cursor.execute(
            "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
            (book_id, cap["title"], cap["page"]),
        )
        capitulo_ids[cap["page"]] = cursor.fetchone()["id"]
    filas = [
        (book_id, i, texto, capitulo_ids.get(i))
        for i, texto in enumerate(paginas, start=1)
    ]
    if filas:
        cursor.executemany(
            "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
            filas,
        )


@api_router.put("/books/{book_id}/repaginate")
async def repaginate_book(book_id: int, request: Request):
    """Repaginación admin segura de UN solo libro (FASE 2).

    Secuencia obligatoria: fuente → extracción/paginación → capítulos →
    validación central (patológico, placeholder, basura, insuficiente) →
    transacción → borrar anteriores → insertar nuevos → actualizar books →
    commit. NUNCA borra páginas antes de generar y validar el nuevo contenido.
    PDF corrupto/ilegible → 422 sin modificar nada; contenido inválido
    (placeholder, duplicado, basura, insuficiente) → 422 sin modificar nada."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden repaginar libros.")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT id, title, content, pdf_path, page_count FROM books WHERE id = %s",
            (book_id,),
        )
        book = cursor.fetchone()
        if not book:
            db.rollback()
            raise HTTPException(status_code=404, detail="Libro no encontrado")

        pdf_path = _resolver_pdf_path(book["pdf_path"])

        if pdf_path:
            try:
                paginas, capitulos = lectura.extraer_paginas_pdf(pdf_path)
            except lectura.PDFSinTextoExtraible as e:
                db.rollback()
                raise HTTPException(
                    status_code=422,
                    detail=f"PDF sin texto extraíble, no se repagina: {str(e)}",
                )
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=422,
                    detail=f"PDF corrupto o ilegible, no se repagina: {str(e)}",
                )
            fuente = "pdf"
            fuente_texto = "\n".join(paginas)
        else:
            fuente_texto = book["content"] or ""
            paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(fuente_texto)
            fuente = "content"

        validacion = lectura.validar_contenido_libro(fuente_texto, paginas, fuente=fuente)
        if not validacion["valid"]:
            db.rollback()
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Contenido rechazado: "
                    + "; ".join(validacion["errors"])
                    + ". No se modificó el libro.",
                    "pathological": validacion["detalle"].get("pathological", False),
                    "errors": validacion["errors"],
                    **validacion["detalle"],
                },
            )

        cursor.execute("DELETE FROM book_pages WHERE book_id = %s", (book_id,))
        cursor.execute("DELETE FROM chapters WHERE book_id = %s", (book_id,))
        _guardar_paginas_libro(cursor, book_id, paginas, capitulos)
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
            (len(paginas), now, book_id),
        )
        db.commit()

        return {
            "message": "Libro repaginado correctamente",
            "book_id": book_id,
            "source": fuente,
            "page_count": len(paginas),
            "chapters": len(capitulos),
            "paginated_at": now,
            "diagnostico": validacion["detalle"],
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error repaginando el libro: {str(e)}")
    finally:
        db.close()


def _get_daily_progress(cursor, user_id, day):
    cursor.execute(
        "SELECT COUNT(*) AS total FROM reading_daily_pages WHERE user_id = %s AND day = %s",
        (user_id, day),
    )
    pages = cursor.fetchone()["total"]
    cursor.execute(
        """
        SELECT rdp.book_id, b.title, COUNT(*) AS pages
        FROM reading_daily_pages rdp
        JOIN books b ON b.id = rdp.book_id
        WHERE rdp.user_id = %s AND rdp.day = %s
        GROUP BY rdp.book_id, b.title
        """,
        (user_id, day),
    )
    books = cursor.fetchall()
    cursor.execute(
        "SELECT id FROM rayos_transactions WHERE user_id = %s AND type = 'daily_goal_reward' AND created_at LIKE %s",
        (user_id, f"{day}%"),
    )
    reward_claimed = bool(cursor.fetchone())
    return {
        "day": day,
        "pages": pages,
        "goal": DAILY_GOAL_PAGES,
        "completed": pages >= DAILY_GOAL_PAGES,
        "reward_claimed": reward_claimed,
        "books": books,
    }


class ProgressRequest(BaseModel):
    page: int


@api_router.post("/books/{book_id}/start")
async def start_reading_session(book_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, title, published, page_count, uploader_id FROM books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO reading_sessions (user_id, book_id, started_at, last_active_at, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT (user_id, book_id)
            DO UPDATE SET last_active_at = EXCLUDED.last_active_at
            """,
            (user["id"], book_id, now, now),
        )
        cursor.execute(
            "SELECT page_number FROM reading_progress WHERE user_id = %s AND book_id = %s",
            (user["id"], book_id),
        )
        last_page_row = cursor.fetchone()
        db.commit()

        cursor.execute("SELECT COUNT(*) AS cnt FROM book_pages WHERE book_id = %s", (book_id,))
        row = cursor.fetchone()
        total_pages = row["cnt"] if row else 0

        return {
            "session_started": True,
            "last_page": last_page_row["page_number"] if last_page_row else None,
            "total_pages": total_pages,
        }
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.post("/books/{book_id}/progress")
async def report_page_progress(book_id: int, req: ProgressRequest, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, title, published, page_count, uploader_id FROM books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")

        cursor.execute("SELECT COUNT(*) AS cnt FROM book_pages WHERE book_id = %s", (book_id,))
        row = cursor.fetchone()
        total_pages = row["cnt"] if row else 0
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        day = now.date().isoformat()

        if total_pages <= 0:
            db.commit()
            return {
                "accepted": False,
                "counted": False,
                "page": req.page,
                "message": "Este libro aún no tiene paginación",
                "daily": _get_daily_progress(cursor, user["id"], day),
            }

        if req.page < 1 or req.page > total_pages:
            raise HTTPException(status_code=400, detail=f"Página fuera de rango (1-{total_pages})")

        cursor.execute(
            "SELECT page_number, reached_at FROM reading_progress WHERE user_id = %s AND book_id = %s",
            (user["id"], book_id),
        )
        last_row = cursor.fetchone()
        last_page = last_row["page_number"] if last_row else 0

        if req.page < last_page:
            db.commit()
            return {
                "accepted": False,
                "counted": False,
                "page": req.page,
                "message": "No se puede retroceder en el progreso",
                "daily": _get_daily_progress(cursor, user["id"], day),
            }

        counted = False
        if req.page > last_page:
            if last_row:
                last_active = datetime.fromisoformat(last_row["reached_at"])
                if (now - last_active).total_seconds() < MIN_SECONDS_BETWEEN_PAGE_REPORTS:
                    db.commit()
                    return {
                        "accepted": True,
                        "counted": False,
                        "page": req.page,
                        "message": "Reporte demasiado rápido",
                        "daily": _get_daily_progress(cursor, user["id"], day),
                    }
            cursor.execute(
                """
                INSERT INTO reading_daily_pages (user_id, book_id, page_number, day)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (user["id"], book_id, req.page, day),
            )
            counted = cursor.rowcount > 0
            cursor.execute(
                """
                INSERT INTO reading_progress (user_id, book_id, page_number, reached_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, book_id)
                DO UPDATE SET page_number = EXCLUDED.page_number, reached_at = EXCLUDED.reached_at
                """,
                (user["id"], book_id, req.page, now_iso),
            )
            cursor.execute(
                """
                INSERT INTO reading_sessions (user_id, book_id, started_at, last_active_at, status)
                VALUES (%s, %s, %s, %s, 'active')
                ON CONFLICT (user_id, book_id)
                DO UPDATE SET last_active_at = EXCLUDED.last_active_at
                """,
                (user["id"], book_id, now_iso, now_iso),
            )

        # Serializa recompensas concurrentes por usuario: el segundo txn espera
        # a que el primero haga commit y ya ve su transacción de recompensa.
        cursor.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user["id"],))
        daily = _get_daily_progress(cursor, user["id"], day)
        rewarded = False
        reward_amount = 0
        new_balance = user["rayos_balance"]
        if daily["completed"] and not daily["reward_claimed"]:
            new_balance = _credit_rayos(
                cursor,
                user["id"],
                DAILY_GOAL_REWARD_AMOUNT,
                "daily_goal_reward",
                f"¡Meta diaria de {DAILY_GOAL_PAGES} páginas completada!",
                book_id=book_id,
            )
            rewarded = True
            reward_amount = DAILY_GOAL_REWARD_AMOUNT
            daily["reward_claimed"] = True

        db.commit()
        return {
            "accepted": True,
            "counted": counted,
            "page": req.page,
            "last_page": req.page if req.page > last_page else last_page,
            "rewarded": rewarded,
            "reward_amount": reward_amount,
            "balance": new_balance,
            "message": "Progreso registrado",
            "daily": daily,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@api_router.get("/books/{book_id}/progress")
async def get_reading_progress(book_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, published, page_count, uploader_id FROM books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")

        cursor.execute(
            "SELECT page_number FROM reading_progress WHERE user_id = %s AND book_id = %s",
            (user["id"], book_id),
        )
        last_row = cursor.fetchone()
        day = datetime.now(timezone.utc).date().isoformat()

        cursor.execute("SELECT COUNT(*) AS cnt FROM book_pages WHERE book_id = %s", (book_id,))
        row = cursor.fetchone()
        total_pages = row["cnt"] if row else 0

        return {
            "book_id": book_id,
            "last_page": last_row["page_number"] if last_row else 1,
            "total_pages": total_pages,
            "daily": _get_daily_progress(cursor, user["id"], day),
        }
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.get("/books/{book_id}/chapters")
async def get_book_chapters(book_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, title, published, uploader_id FROM books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")
        cursor.execute(
            "SELECT id, title, start_page FROM chapters WHERE book_id = %s ORDER BY start_page",
            (book_id,),
        )
        return cursor.fetchall()
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.get("/books/{book_id}/pages/{page}")
async def get_book_page(book_id: int, page: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, published, page_count, uploader_id FROM books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        if not _puede_acceder_libro(book, user):
            raise HTTPException(status_code=403, detail="Este libro no está publicado")

        cursor.execute("SELECT COUNT(*) AS cnt FROM book_pages WHERE book_id = %s", (book_id,))
        row = cursor.fetchone()
        total_pages = row["cnt"] if row else 0

        if total_pages <= 0:
            raise HTTPException(status_code=404, detail="Libro sin paginación")
        if page < 1 or page > total_pages:
            raise HTTPException(status_code=400, detail=f"Página fuera de rango (1-{total_pages})")

        cursor.execute(
            """
            SELECT p.page_number, p.content, c.title AS chapter_title
            FROM book_pages p
            LEFT JOIN chapters c ON c.id = p.chapter_id
            WHERE p.book_id = %s AND p.page_number = %s
            """,
            (book_id, page),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Página no encontrada")
        return {
            "book_id": book_id,
            "page_number": row["page_number"],
            "content": row["content"],
            "chapter_title": row["chapter_title"],
            "total_pages": total_pages,
            "has_next": page < total_pages,
        }
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.get("/reading/today")
async def get_reading_today(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()
    try:
        day = datetime.now(timezone.utc).date().isoformat()
        return _get_daily_progress(cursor, user["id"], day)
    finally:
        db.close()


@api_router.get("/rayos/transactions")
async def get_rayos_transactions(request: Request):
    user = await get_current_user(request)
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM rayos_transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
        (user["id"],),
    )
    rows = cursor.fetchall()

    transactions = []
    for row in rows:
        transaction = dict(row)
        transaction["id"] = str(transaction["id"])
        transactions.append(transaction)

    db.close()
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

@api_router.post("/courses/{course_id}/start")
async def start_course(course_id: int, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión para iniciar un curso")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM courses WHERE id = %s", (course_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute(
            """
            INSERT INTO course_progress (user_id, course_id, started_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, course_id) DO UPDATE SET started_at = course_progress.started_at
            """,
            (user["id"], course_id, now),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al iniciar el curso")
    finally:
        db.close()

    return {"message": "Curso iniciado. Buen estudio!"}


@api_router.post("/courses/{course_id}/complete")
async def complete_course(course_id: int, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión para obtener recompensas")

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, title, reward_amount FROM courses WHERE id = %s FOR UPDATE", (course_id,))
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Curso no encontrado")

        cursor.execute(
            "SELECT id, started_at, completed_at FROM course_progress WHERE user_id = %s AND course_id = %s FOR UPDATE",
            (user["id"], course_id),
        )
        progress = cursor.fetchone()
        if not progress:
            raise HTTPException(status_code=400, detail="Debes iniciar el curso antes de completarlo")

        # Sin doble reclamo (también cubre registros previos a la FASE 1)
        if progress["completed_at"] is not None:
            raise HTTPException(status_code=400, detail="Ya reclamaste la recompensa de este curso")
        if not progress["started_at"]:
            raise HTTPException(status_code=400, detail="Debes iniciar el curso antes de completarlo")

        # Tiempo mínimo de visualización anti-farm (el backend lo decide)
        started = datetime.fromisoformat(progress["started_at"])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed_seconds = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed_seconds < MIN_COURSE_REWARD_SECONDS:
            raise HTTPException(
                status_code=400,
                detail=f"Debes ver al menos {MIN_COURSE_REWARD_SECONDS} segundos del curso antes de reclamar la recompensa",
            )

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE course_progress SET completed_at = %s WHERE id = %s",
            (now, progress["id"]),
        )
        new_balance = _credit_rayos(
            cursor,
            user["id"],
            course["reward_amount"],
            "course_reward",
            f"Recompensa por completar el curso '{course['title']}'",
            course_id=course_id,
        )
        db.commit()
    except HTTPException as e:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar la recompensa")
    finally:
        db.close()

    return {"message": f"¡Felicidades! Has ganado {course['reward_amount']} Rayos.", "balance": new_balance}

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
        cover_path = os.path.join(STORAGE_COVERS, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
        updates.append("cover_url = %s")
        params.append(f"/static/covers/{cover_filename}")

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


# ── Libros destacados del mes (FASE: Featured Books) ─────────────────────────

class FeaturedBooksPayload(BaseModel):
    book_ids: List[int]


@api_router.get("/featured-books")
async def get_featured_books():
    """Endpoint público: retorna los libros destacados del mes actual."""
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT b.id, b.title, b.author_name, b.category, b.price,
                   b.cover_image_url, b.views, b.likes, b.average_rating,
                   b.total_reviews, fb.display_order
            FROM featured_books fb
            JOIN books b ON b.id = fb.book_id
            WHERE fb.month = %s AND fb.year = %s AND b.published = 1
            ORDER BY fb.display_order ASC
            LIMIT 20
            """,
            (current_month, current_year),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


@api_router.get("/admin/featured-books")
async def admin_get_featured_books(request: Request):
    """Panel admin: retorna la configuración de destacados del mes actual."""
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT fb.id, fb.book_id, fb.display_order, fb.month, fb.year,
                   fb.added_by, fb.created_at,
                   b.title, b.author_name, b.category, b.price,
                   b.cover_image_url, b.published
            FROM featured_books fb
            JOIN books b ON b.id = fb.book_id
            WHERE fb.month = %s AND fb.year = %s
            ORDER BY fb.display_order ASC
            """,
            (current_month, current_year),
        )
        rows = cursor.fetchall()
        return {"month": current_month, "year": current_year, "featured": [dict(row) for row in rows]}
    finally:
        db.close()


@api_router.put("/admin/featured-books")
async def admin_set_featured_books(req: FeaturedBooksPayload, request: Request):
    """Panel admin: reemplaza la selección completa de destacados del mes actual."""
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    book_ids = req.book_ids
    if not isinstance(book_ids, list):
        raise HTTPException(status_code=400, detail="book_ids debe ser una lista")

    # Eliminar duplicados manteniendo orden
    seen = set()
    unique_ids = []
    for bid in book_ids:
        if bid not in seen:
            seen.add(bid)
            unique_ids.append(bid)

    if len(unique_ids) > 20:
        raise HTTPException(status_code=400, detail="Máximo 20 libros destacados")

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year
    now_iso = now.isoformat()

    db = get_db()
    cursor = db.cursor()
    try:
        # Verificar que todos los libros existen y están publicados
        if unique_ids:
            cursor.execute(
                "SELECT id, published FROM books WHERE id = ANY(%s)",
                (unique_ids,),
            )
            found = {row["id"]: row for row in cursor.fetchall()}
            for bid in unique_ids:
                if bid not in found:
                    raise HTTPException(status_code=400, detail=f"Libro {bid} no encontrado")
                if found[bid]["published"] != 1:
                    raise HTTPException(status_code=400, detail=f"El libro {bid} no está publicado")

        # Eliminar los destacados actuales del mes y reinsertar
        cursor.execute(
            "DELETE FROM featured_books WHERE month = %s AND year = %s",
            (current_month, current_year),
        )
        for order, bid in enumerate(unique_ids):
            cursor.execute(
                """
                INSERT INTO featured_books (book_id, display_order, month, year, added_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (bid, order, current_month, current_year, user["id"], now_iso),
            )
        db.commit()
        return {"message": "Libros destacados actualizados", "count": len(unique_ids)}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@api_router.delete("/admin/featured-books/{book_id}")
async def admin_remove_featured_book(book_id: int, request: Request):
    """Panel admin: quita un libro de los destacados del mes actual."""
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "DELETE FROM featured_books WHERE book_id = %s AND month = %s AND year = %s",
            (book_id, current_month, current_year),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="El libro no está en los destacados del mes actual")
        db.commit()
        return {"message": "Libro removido de destacados"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


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

        # PASO 3: validación central. Un texto de Gutenberg vacío, degradado,
        # con repetición patológica o insuficiente NO se publica.
        contenido_recortado = content[:100000]
        validacion = lectura.validar_contenido_libro(contenido_recortado, None, fuente="gutenberg")
        if not validacion["valid"]:
            raise HTTPException(
                status_code=422,
                detail="Contenido rechazado: el texto no pudo procesarse correctamente. "
                + "; ".join(validacion["errors"]),
            )

        now = datetime.now(timezone.utc).isoformat()
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO books (title, author_name, content, category, price, cover_image_url, pdf_path, views, likes, average_rating, total_reviews, published, created_at, uploader_id)
            VALUES (%s, %s, %s, %s, 0, %s, NULL, 0, 0, 0.0, 0, 1, %s, %s)
            RETURNING id
            """,
            (title, author_name, contenido_recortado, "Clásicos", cover_url, now, user["id"])
        )
        new_book_id = cursor.fetchone()["id"]
        paginas_libro, capitulos_libro = lectura.paginar_desde_contenido_con_capitulos(contenido_recortado)
        if paginas_libro:
            _guardar_paginas_libro(cursor, new_book_id, paginas_libro, capitulos_libro)
            cursor.execute("UPDATE books SET page_count = %s WHERE id = %s", (len(paginas_libro), new_book_id))
        db.commit()
        return {"message": f"Libro '{title}' importado exitosamente."}

    except HTTPException:
        raise
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
        cursor.execute("SELECT id, email FROM users")
        all_users = cursor.fetchall()

        notif_msg = f"¡Nuevo torneo disponible: {comp.title} sobre {comp.book_title}!"
        emails_list = []
        for u in all_users:
            cursor.execute(
                "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'system', %s, %s)",
                (u["id"], notif_msg, now)
            )
            if u["email"]:
                emails_list.append(u["email"])

        db.commit()

        # Enviar correo masivo
        if emails_list:
            email_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; text-align: center;">
                <h2 style="color: #D4AF37;">¡Nuevo Torneo de Lectura!</h2>
                <p>Se ha anunciado un nuevo torneo en AETERNUM:</p>
                <h3 style="color: white; background-color: #121212; padding: 15px; border-radius: 10px;">{comp.title} <br> <span style="color: #A0A0A0; font-size: 14px;">Libro Base: {comp.book_title}</span></h3>
                <p>Fecha programada: {comp.scheduled_at}</p>
                <a href="https://aeternum-world.onrender.com/competitions" style="display: inline-block; padding: 12px 24px; margin: 20px 0; background-color: #D4AF37; color: black; text-decoration: none; border-radius: 8px; font-weight: bold;">Ir a la Arena</a>
            </div>
            """
            send_mass_email_async(emails_list, f"Nuevo Torneo: {comp.title}", email_html)

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

    cursor.execute("SELECT id, status FROM competition_participants WHERE competition_id = %s AND user_id = %s", (comp_id, user["id"]))
    participant = cursor.fetchone()

    if not participant or participant["status"] == "submitted":
        db.close()
        raise HTTPException(status_code=400, detail="No puedes enviar respuestas")

    # El puntaje SIEMPRE lo calcula el servidor comparando contra la respuesta
    # correcta real (el cliente jamás envía su propio score)
    cursor.execute("SELECT id, correct_option FROM competition_questions WHERE competition_id = %s", (comp_id,))
    correct_map = {
        q["id"]: (q["correct_option"] or "").strip().upper()
        for q in cursor.fetchall()
    }
    score = 0
    for answer in submission.answers:
        if answer.question_id in correct_map and answer.selected.strip().upper() == correct_map[answer.question_id]:
            score += 10

    # Tiempo acotado por el servidor (anti-abuso)
    try:
        time_taken_ms = int(submission.time_taken_ms)
    except (TypeError, ValueError):
        time_taken_ms = 0
    time_taken_ms = max(0, min(time_taken_ms, MAX_COMPETITION_TIME_MS))

    # Reclamo atómico: solo se acepta la primera entrega
    cursor.execute(
        "UPDATE competition_participants SET score = %s, time_taken_ms = %s, status = 'submitted' WHERE id = %s AND status = 'registered'",
        (score, time_taken_ms, participant["id"])
    )
    if cursor.rowcount != 1:
        db.rollback()
        db.close()
        raise HTTPException(status_code=400, detail="No puedes enviar respuestas")
    db.commit()
    db.close()
    return {"message": "Respuestas enviadas correctamente", "score": score}

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
        cursor.execute(
            "INSERT INTO rayos_transactions (user_id, amount, type, description, created_at, competition_id) VALUES (%s, %s, 'competition_reward', %s, %s, %s)",
            (user_id, prize, f"Premio {i+1}er lugar en competencia", now, comp_id)
        )

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

class DonationRequest(BaseModel):
    amount: int = Field(gt=0, description="Cantidad de Rayos a donar")

@api_router.post("/users/{username}/donate-rayos")
async def donate_rayos(username: str, req: DonationRequest, request: Request):
    donor = await get_current_user(request)

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, username FROM users WHERE username = %s", (username,))
        target = cursor.fetchone()

        if not target:
            raise HTTPException(status_code=404, detail="Usuario receptor no encontrado")

        if target["id"] == donor["id"]:
            raise HTTPException(status_code=400, detail="No puedes donarte Rayos a ti mismo")

        received, burned = compute_donation_split(req.amount)

        # Débito atómico condicional: nunca deja el saldo en negativo
        new_donor_balance = _debit_rayos_atomic(
            cursor,
            donor["id"],
            req.amount,
            "donation_sent",
            f"Donación enviada a @{target['username']}",
        )
        if new_donor_balance is None:
            raise HTTPException(status_code=400, detail="No tienes suficientes Rayos")

        # El receptor recibe el monto menos la quema (nunca crea Rayos nuevos)
        _credit_rayos(
            cursor,
            target["id"],
            received,
            "donation_received",
            f"Donación recibida de @{donor['username']}",
        )

        # La quema del 10% se registra a nivel de sistema (user_id NULL):
        # esos Rayos desaparecen del ecosistema, nunca son progreso de nadie
        if burned > 0:
            _record_rayos_transaction(
                cursor,
                None,
                -burned,
                "donation_burn",
                f"Quema del 10% por donación de @{donor['username']} a @{target['username']}",
            )

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'system', %s, %s)",
            (target["id"], f"¡Felicidades! @{donor['username']} te ha donado {received} Rayos.", now))

        db.commit()
    except HTTPException as e:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return {"message": f"Has donado {req.amount} Rayos exitosamente", "received": received, "burned": burned}


# ── Auditoría de Rayos (FASE 1) ───────────────────────────────────────────────

@api_router.get("/admin/rayos/audit")
async def admin_rayos_audit(request: Request):
    user = await get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")

    db = get_db()
    cursor = db.cursor()
    try:
        # Ledger real vs saldo declarado por usuario
        cursor.execute("""
            SELECT u.id, u.username, u.rayos_balance, u.historical_rayos,
                   COALESCE(SUM(t.amount), 0) AS ledger_sum
            FROM users u
            LEFT JOIN rayos_transactions t ON t.user_id = u.id
            GROUP BY u.id, u.username, u.rayos_balance, u.historical_rayos
            ORDER BY u.id
        """)
        rows = cursor.fetchall()

        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM rayos_transactions")
        total_ledger = cursor.fetchone()["s"]
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM rayos_transactions WHERE type = 'donation_burn'")
        total_burned = cursor.fetchone()["s"]
        cursor.execute("SELECT COALESCE(SUM(rayos_balance), 0) AS s FROM users")
        total_balance = cursor.fetchone()["s"]
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    users_audit = []
    mismatches = []
    for row in rows:
        entry = {
            "user_id": row["id"],
            "username": row["username"],
            "balance": row["rayos_balance"],
            "historical_rayos": row["historical_rayos"],
            "ledger_sum": row["ledger_sum"],
            "delta": row["rayos_balance"] - row["ledger_sum"],
        }
        users_audit.append(entry)
        if row["rayos_balance"] != row["ledger_sum"]:
            mismatches.append({
                **entry,
                "note": "Crédito previo a la FASE 1 (semilla o recompensa antigua) sin transacción registrada en el libro mayor",
            })

    return {
        "audit_time": datetime.now(timezone.utc).isoformat(),
        "total_users_balance": total_balance,
        "total_ledger": total_ledger,
        "total_burned": total_burned,
        "net_supply": total_ledger + total_burned,
        "users": users_audit,
        "mismatches": mismatches,
        "note": "Los deltas legacy (semillas 500/100 y acreditaciones pre-FASE 1) se reportan pero no se corrigen automáticamente.",
    }

# ── IA de Aeternum (FASE 8.3) ────────────────────────────────────────────────
# Endpoint fino: toda la lógica vive en ai_service.py. El proveedor real,
# la economía de Rayos y la persistencia se implementan en fases posteriores.

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    book_id: Optional[int] = None
    page_number: Optional[int] = None
    chapter_id: Optional[int] = None
    # operation_id (FASE 8.5): clave de idempotencia económica opcional enviada
    # por el cliente para evitar doble cobro por reintentos HTTP. Si no llega,
    # el servidor genera uno interno. Nunca permite acceder a operaciones de
    # otro usuario: se valida contra el user_id del JWT.
    operation_id: Optional[str] = Field(None, max_length=64)
    # conversation_id (FASE 8.7): conversación del usuario. Si no llega, el
    # servidor crea una nueva. Si llega, se valida que pertenezca al JWT
    # (404 genérico si no existe o es ajena). Nunca permite acceder a
    # conversaciones de otro usuario.
    conversation_id: Optional[int] = Field(None, ge=1)
    # OJO: user_id recibido aquí se IGNORA siempre. La identidad se obtiene
    # exclusivamente del JWT (get_current_user). No permite suplantación.
    user_id: Optional[int] = None


@api_router.post("/ai/chat")
async def ai_chat(payload: AIChatRequest, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        result = await process_chat(
            user=user,
            message=payload.message,
            book_id=payload.book_id,
            page_number=payload.page_number,
            chapter_id=payload.chapter_id,
            can_access_book=_puede_acceder_libro,
            db=db,
            operation_id=payload.operation_id,
            conversation_id=payload.conversation_id,
        )
        db.commit()
        return result
    except AIServiceError as e:
        # FASE 8.7: si la solicitud falla (proveedor, contexto, economía), el
        # cierre de la conexión SIN commit revierte la transacción: no quedan
        # mensajes ni conversaciones huérfanas y nunca se cobra una respuesta
        # fallida. (En PostgreSQL el cierre sin commit implica rollback.)
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception:
        logger_server.exception(
            "Error inesperado en /api/ai/chat (usuario_id=%s)", user["id"]
        )
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    finally:
        db.close()


# ── FASE 8.7: conversaciones de IA (endpoints finos, lógica en
#    ai_conversations.py) ─────────────────────────────────────────────────────

@api_router.get("/ai/conversations")
async def ai_conversations_list(request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        conversations = ai_conversations.list_conversations(db, user["id"])
        return {"success": True, "conversations": conversations}
    except ai_conversations.AIConversationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception:
        logger_server.exception(
            "Error inesperado en GET /api/ai/conversations (usuario_id=%s)",
            user["id"],
        )
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    finally:
        db.close()


@api_router.get("/ai/conversations/{conversation_id}/messages")
async def ai_conversation_messages(conversation_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        messages = ai_conversations.get_messages(db, conversation_id, user["id"])
        return {"success": True, "conversation_id": conversation_id, "messages": messages}
    except ai_conversations.AIConversationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception:
        logger_server.exception(
            "Error inesperado en GET /api/ai/conversations/{id}/messages "
            "(usuario_id=%s)", user["id"],
        )
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    finally:
        db.close()


@api_router.delete("/ai/conversations/{conversation_id}")
async def ai_conversation_delete(conversation_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        ai_conversations.delete_conversation(db, conversation_id, user["id"])
        db.commit()
        return {"success": True, "deleted": conversation_id}
    except ai_conversations.AIConversationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception:
        logger_server.exception(
            "Error inesperado en DELETE /api/ai/conversations/{id} "
            "(usuario_id=%s)", user["id"],
        )
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════════════
# FORO ESTUDIANTIL — Endpoints
# ══════════════════════════════════════════════════════════════════════════════

import math

FORUM_PAGE_DEFAULT = 20
FORUM_PAGE_MAX = 50
FORUM_POSTS_PER_HOUR = 5
FORUM_REPLIES_PER_HOUR = 20
FORUM_LIKES_PER_HOUR = 30
FORUM_REPORTS_PER_HOUR = 10


def _generate_slug(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:80]


def _check_forum_rate_limit(db, user_id: int, action: str, max_count: int):
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=1)).isoformat()
    cursor = db.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM forum_rate_limits WHERE user_id = %s AND action = %s AND window_start >= %s",
        (user_id, action, window_start),
    )
    row = cursor.fetchone()
    cnt = row["cnt"] if row else 0
    if cnt >= max_count:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Intenta más tarde.")
    cursor.execute(
        "INSERT INTO forum_rate_limits (user_id, action, window_start) VALUES (%s, %s, %s)",
        (user_id, action, now.isoformat()),
    )
    db.commit()


def _audit_log(db, admin_id: int, action: str, target_type: str, target_id: int, details: str = None):
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO forum_audit_log (admin_id, action, target_type, target_id, details, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (admin_id, action, target_type, target_id, details, now),
    )
    db.commit()


# ── Categorías ──────────────────────────────────────────────────────────────

@api_router.get("/forum/categories")
async def forum_get_categories():
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, name, description, icon, color, sort_order, is_active, post_count FROM forum_categories WHERE is_active = TRUE ORDER BY sort_order ASC"
        )
        return cursor.fetchall()
    finally:
        db.close()


@api_router.post("/admin/forum/categories")
async def forum_admin_create_category(request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nombre de categoría requerido")
    description = (body.get("description") or "").strip()
    icon = (body.get("icon") or "").strip()
    color = (body.get("color") or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO forum_categories (name, description, icon, color, sort_order, created_at) VALUES (%s,%s,%s,%s,0,%s) RETURNING id",
            (name, description, icon, color, now),
        )
        row = cursor.fetchone()
        db.commit()
        _audit_log(db, user["id"], "create_category", "category", row["id"], name)
        return {"id": row["id"], "created_at": now}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear categoría")
    finally:
        db.close()


@api_router.put("/admin/forum/categories/{category_id}")
async def forum_admin_update_category(category_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    body = await request.json()
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM forum_categories WHERE id = %s", (category_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        updates = []
        params = []
        for field in ("name", "description", "icon", "color"):
            if field in body and body[field] is not None:
                updates.append(f"{field} = %s")
                params.append(str(body[field]).strip())
        if "sort_order" in body:
            updates.append("sort_order = %s")
            params.append(int(body["sort_order"]))
        if "is_active" in body:
            updates.append("is_active = %s")
            params.append(bool(body["is_active"]))
        if not updates:
            raise HTTPException(status_code=400, detail="Sin cambios")
        params.append(category_id)
        cursor.execute(f"UPDATE forum_categories SET {', '.join(updates)} WHERE id = %s", tuple(params))
        db.commit()
        _audit_log(db, user["id"], "edit_category", "category", category_id)
        return {"updated": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar")
    finally:
        db.close()


@api_router.get("/admin/forum/categories")
async def forum_admin_list_categories(request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT id, name, description, icon, color, sort_order, is_active, post_count, created_at
               FROM forum_categories
               ORDER BY sort_order ASC"""
        )
        return cursor.fetchall()
    finally:
        db.close()


@api_router.delete("/admin/forum/categories/{category_id}")
async def forum_admin_delete_category(category_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, post_count FROM forum_categories WHERE id = %s", (category_id,))
        cat = cursor.fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        if cat.get("post_count", 0) > 0:
            raise HTTPException(status_code=400, detail="No se puede eliminar una categoría con publicaciones. Desactívala en su lugar.")
        cursor.execute("DELETE FROM forum_categories WHERE id = %s", (category_id,))
        db.commit()
        _audit_log(db, user["id"], "delete_category", "category", category_id)
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar")
    finally:
        db.close()


# ── Publicaciones ───────────────────────────────────────────────────────────

@api_router.get("/forum/posts")
async def forum_list_posts(
    request: Request,
    category: Optional[int] = None,
    book_id: Optional[int] = None,
    user_id: Optional[int] = None,
    sort: str = "newest",
    page: int = 1,
    limit: int = FORUM_PAGE_DEFAULT,
):
    limit = min(max(limit, 1), FORUM_PAGE_MAX)
    page = max(page, 1)
    offset = (page - 1) * limit
    db = get_db()
    try:
        cursor = db.cursor()
        where = ["fp.status = 'active'"]
        params = []
        if category:
            where.append("fp.category_id = %s")
            params.append(category)
        if book_id:
            where.append("fp.book_id = %s")
            params.append(book_id)
        if user_id:
            where.append("fp.user_id = %s")
            params.append(user_id)
        where_sql = " AND ".join(where)

        order_map = {
            "newest": "fp.is_pinned DESC, fp.created_at DESC",
            "popular": "fp.is_pinned DESC, fp.like_count DESC, fp.views DESC",
            "most_replies": "fp.is_pinned DESC, fp.reply_count DESC",
            "unanswered": "fp.reply_count = 0, fp.is_pinned DESC, fp.created_at DESC",
            "resolved": "fp.is_resolved = TRUE, fp.created_at DESC",
        }
        order = order_map.get(sort, order_map["newest"])

        cursor.execute(f"SELECT COUNT(*) AS total FROM forum_posts fp WHERE {where_sql}", tuple(params))
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""SELECT fp.id, fp.user_id, u.username AS author_username, u.name AS author_name,
                       fp.category_id, fc.name AS category_name, fc.icon AS category_icon, fc.color AS category_color,
                       fp.title, fp.slug, fp.status, fp.views, fp.reply_count, fp.like_count,
                       fp.is_pinned, fp.is_resolved, fp.book_id, fp.created_at, fp.updated_at
                FROM forum_posts fp
                LEFT JOIN users u ON fp.user_id = u.id
                LEFT JOIN forum_categories fc ON fp.category_id = fc.id
                WHERE {where_sql}
                ORDER BY {order}
                LIMIT %s OFFSET %s""",
            tuple(params) + (limit, offset),
        )
        posts = cursor.fetchall()
        return {
            "posts": posts,
            "total": total,
            "page": page,
            "pages": math.ceil(total / limit) if total else 0,
        }
    finally:
        db.close()


@api_router.get("/forum/posts/{post_id}")
async def forum_get_post(post_id: int, request: Request):
    user = await get_current_user_optional(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT fp.*, u.username AS author_username, u.name AS author_name,
                      fc.name AS category_name, fc.icon AS category_icon, fc.color AS category_color,
                      b.title AS book_title
               FROM forum_posts fp
               LEFT JOIN users u ON fp.user_id = u.id
               LEFT JOIN forum_categories fc ON fp.category_id = fc.id
               LEFT JOIN books b ON fp.book_id = b.id
               WHERE fp.id = %s""",
            (post_id,),
        )
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        if post["status"] != "active" and (not user or user["role"] != "admin"):
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        # Incrementar vistas (una vez)
        cursor.execute("UPDATE forum_posts SET views = views + 1 WHERE id = %s", (post_id,))
        db.commit()
        post["views"] = post.get("views", 0) + 1

        user_liked = False
        user_bookmarked = False
        user_following = False
        if user:
            cursor.execute("SELECT 1 FROM forum_likes WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
            user_liked = cursor.fetchone() is not None
            cursor.execute("SELECT 1 FROM forum_bookmarks WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
            user_bookmarked = cursor.fetchone() is not None
            cursor.execute("SELECT 1 FROM forum_follows WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
            user_following = cursor.fetchone() is not None

        return {
            "post": post,
            "user_liked": user_liked,
            "user_bookmarked": user_bookmarked,
            "user_following": user_following,
        }
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.post("/forum/posts")
async def forum_create_post(request: Request):
    user = await get_current_user(request)
    _check_forum_rate_limit(db := get_db(), user["id"], "post", FORUM_POSTS_PER_HOUR)
    body = await request.json()
    title = (body.get("title") or "").strip()
    content = (body.get("content") or "").strip()
    category_id = body.get("category_id")
    book_id = body.get("book_id")

    if not title or len(title) < 3 or len(title) > 200:
        raise HTTPException(status_code=400, detail="El título debe tener entre 3 y 200 caracteres")
    if not content or len(content) < 10 or len(content) > 10000:
        raise HTTPException(status_code=400, detail="El contenido debe tener entre 10 y 10000 caracteres")
    if not category_id:
        raise HTTPException(status_code=400, detail="Categoría requerida")

    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, is_active FROM forum_categories WHERE id = %s", (category_id,))
        cat = cursor.fetchone()
        if not cat or not cat["is_active"]:
            raise HTTPException(status_code=400, detail="Categoría no válida")

        if book_id:
            cursor.execute("SELECT id FROM books WHERE id = %s", (book_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Libro no encontrado")

        now = datetime.now(timezone.utc).isoformat()
        slug = _generate_slug(title)
        cursor.execute(
            """INSERT INTO forum_posts (user_id, category_id, title, content, book_id, slug, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (user["id"], category_id, title, content, book_id, slug, now, now),
        )
        row = cursor.fetchone()
        cursor.execute("UPDATE forum_categories SET post_count = post_count + 1 WHERE id = %s", (category_id,))
        db.commit()
        return {"id": row["id"], "slug": slug, "created_at": now}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear publicación")
    finally:
        db.close()


@api_router.put("/forum/posts/{post_id}")
async def forum_update_post(post_id: int, request: Request):
    user = await get_current_user(request)
    body = await request.json()
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, user_id, status, category_id FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        if post["status"] != "active":
            raise HTTPException(status_code=400, detail="No se puede editar esta publicación")
        if post["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="No autorizado")

        updates = []
        params = []
        old_category_id = post["category_id"]
        new_category_id = None

        if "title" in body:
            t = str(body["title"]).strip()
            if len(t) < 3 or len(t) > 200:
                raise HTTPException(status_code=400, detail="Título inválido")
            updates.append("title = %s")
            params.append(t)
            updates.append("slug = %s")
            params.append(_generate_slug(t))
        if "content" in body:
            c = str(body["content"]).strip()
            if len(c) < 10 or len(c) > 10000:
                raise HTTPException(status_code=400, detail="Contenido inválido")
            updates.append("content = %s")
            params.append(c)
        if "category_id" in body and body["category_id"] is not None:
            new_category_id = body["category_id"]
            cursor.execute("SELECT id, is_active FROM forum_categories WHERE id = %s", (new_category_id,))
            cat = cursor.fetchone()
            if not cat or not cat["is_active"]:
                raise HTTPException(status_code=400, detail="Categoría no válida")
            if new_category_id != old_category_id:
                updates.append("category_id = %s")
                params.append(new_category_id)
        if not updates:
            raise HTTPException(status_code=400, detail="Sin cambios")
        updates.append("updated_at = %s")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(post_id)
        cursor.execute(f"UPDATE forum_posts SET {', '.join(updates)} WHERE id = %s", tuple(params))

        # Actualizar post_count si cambió la categoría
        if new_category_id is not None and new_category_id != old_category_id:
            cursor.execute("UPDATE forum_categories SET post_count = GREATEST(post_count - 1, 0) WHERE id = %s", (old_category_id,))
            cursor.execute("UPDATE forum_categories SET post_count = post_count + 1 WHERE id = %s", (new_category_id,))

        db.commit()
        return {"updated": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar")
    finally:
        db.close()


@api_router.delete("/forum/posts/{post_id}")
async def forum_delete_post(post_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, user_id, status, category_id FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        if post["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="No autorizado")

        # Solo decrementar post_count si el post no estaba ya deleted
        if post["status"] != "deleted":
            cursor.execute("UPDATE forum_categories SET post_count = GREATEST(post_count - 1, 0) WHERE id = %s", (post["category_id"],))

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("UPDATE forum_posts SET status = 'deleted', updated_at = %s WHERE id = %s", (now, post_id))
        db.commit()
        if user["role"] == "admin":
            _audit_log(db, user["id"], "delete_post", "post", post_id)
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar")
    finally:
        db.close()


# ── Respuestas ──────────────────────────────────────────────────────────────

@api_router.get("/forum/posts/{post_id}/replies")
async def forum_list_replies(post_id: int, page: int = 1, limit: int = FORUM_PAGE_DEFAULT):
    limit = min(max(limit, 1), FORUM_PAGE_MAX)
    page = max(page, 1)
    offset = (page - 1) * limit
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        cursor.execute("SELECT COUNT(*) AS total FROM forum_replies WHERE post_id = %s AND status = 'active'", (post_id,))
        total = cursor.fetchone()["total"]

        cursor.execute(
            """SELECT fr.id, fr.user_id, u.username AS author_username, u.name AS author_name,
                      fr.content, fr.status, fr.is_accepted, fr.like_count, fr.created_at, fr.updated_at
               FROM forum_replies fr
               LEFT JOIN users u ON fr.user_id = u.id
               WHERE fr.post_id = %s AND fr.status = 'active'
               ORDER BY fr.is_accepted DESC, fr.created_at ASC
               LIMIT %s OFFSET %s""",
            (post_id, limit, offset),
        )
        replies = cursor.fetchall()
        return {
            "replies": replies,
            "total": total,
            "page": page,
            "pages": math.ceil(total / limit) if total else 0,
        }
    except HTTPException:
        raise
    finally:
        db.close()


@api_router.post("/forum/posts/{post_id}/replies")
async def forum_create_reply(post_id: int, request: Request):
    user = await get_current_user(request)
    _check_forum_rate_limit(db := get_db(), user["id"], "reply", FORUM_REPLIES_PER_HOUR)
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content or len(content) < 2 or len(content) > 5000:
        raise HTTPException(status_code=400, detail="El contenido debe tener entre 2 y 5000 caracteres")

    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status, user_id, title FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO forum_replies (post_id, user_id, content, created_at, updated_at) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (post_id, user["id"], content, now, now),
        )
        row = cursor.fetchone()
        cursor.execute("UPDATE forum_posts SET reply_count = reply_count + 1 WHERE id = %s", (post_id,))
        db.commit()

        # Notificar al autor del post y a seguidores
        try:
            if post["user_id"] and post["user_id"] != user["id"]:
                notif_content = f"@{user.get('username', 'usuario')} respondió a tu publicación '{post.get('title', '')}'"
                cursor.execute(
                    "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'forum_reply', %s, %s)",
                    (post["user_id"], notif_content, now),
                )
            cursor.execute(
                "SELECT user_id FROM forum_follows WHERE post_id = %s AND user_id != %s",
                (post_id, user["id"]),
            )
            for follower in cursor.fetchall():
                if follower["user_id"] and follower["user_id"] != post.get("user_id"):
                    notif_content = f"Nueva respuesta en '{post.get('title', '')}' que sigues"
                    cursor.execute(
                        "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'forum_follow', %s, %s)",
                        (follower["user_id"], notif_content, now),
                    )
            db.commit()
        except Exception:
            pass

        return {"id": row["id"], "created_at": now}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear respuesta")
    finally:
        db.close()


@api_router.put("/forum/replies/{reply_id}")
async def forum_update_reply(reply_id: int, request: Request):
    user = await get_current_user(request)
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content or len(content) < 2 or len(content) > 5000:
        raise HTTPException(status_code=400, detail="Contenido inválido")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, user_id, status FROM forum_replies WHERE id = %s", (reply_id,))
        reply = cursor.fetchone()
        if not reply:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        if reply["status"] != "active":
            raise HTTPException(status_code=400, detail="No se puede editar esta respuesta")
        if reply["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="No autorizado")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("UPDATE forum_replies SET content = %s, updated_at = %s WHERE id = %s", (content, now, reply_id))
        db.commit()
        return {"updated": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar")
    finally:
        db.close()


@api_router.delete("/forum/replies/{reply_id}")
async def forum_delete_reply(reply_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, user_id, post_id, is_accepted, status FROM forum_replies WHERE id = %s", (reply_id,))
        reply = cursor.fetchone()
        if not reply:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        if reply["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="No autorizado")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("UPDATE forum_replies SET status = 'deleted', updated_at = %s WHERE id = %s", (now, reply_id))
        cursor.execute("UPDATE forum_posts SET reply_count = GREATEST(reply_count - 1, 0) WHERE id = %s", (reply["post_id"],))
        if reply["is_accepted"]:
            cursor.execute("UPDATE forum_posts SET is_resolved = FALSE WHERE id = %s", (reply["post_id"],))
        db.commit()
        if user["role"] == "admin":
            _audit_log(db, user["id"], "delete_reply", "reply", reply_id)
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar")
    finally:
        db.close()


@api_router.post("/forum/replies/{reply_id}/accept")
async def forum_accept_reply(reply_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT fr.id, fr.post_id, fr.user_id, fr.status FROM forum_replies fr WHERE fr.id = %s",
            (reply_id,),
        )
        reply = cursor.fetchone()
        if not reply:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        if reply["status"] != "active":
            raise HTTPException(status_code=400, detail="Respuesta no válida")

        cursor.execute("SELECT id, user_id, status FROM forum_posts WHERE id = %s", (reply["post_id"],))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=400, detail="Publicación no válida")
        if post["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Solo el autor del post puede marcar la solución")

        # Desmarcar aceptación anterior si existe
        cursor.execute(
            "UPDATE forum_replies SET is_accepted = FALSE WHERE post_id = %s AND is_accepted = TRUE",
            (reply["post_id"],),
        )
        cursor.execute("UPDATE forum_replies SET is_accepted = TRUE WHERE id = %s", (reply_id,))
        cursor.execute("UPDATE forum_posts SET is_resolved = TRUE WHERE id = %s", (reply["post_id"],))
        db.commit()

        # Notificar al autor de la respuesta
        try:
            if reply["user_id"] and reply["user_id"] != user["id"]:
                notif_content = "Tu respuesta fue marcada como solución"
                cursor.execute(
                    "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'forum_accepted', %s, %s)",
                    (reply["user_id"], notif_content, datetime.now(timezone.utc).isoformat()),
                )
                db.commit()
        except Exception:
            pass

        return {"accepted": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al aceptar respuesta")
    finally:
        db.close()


# ── Interacciones ───────────────────────────────────────────────────────────

@api_router.post("/forum/posts/{post_id}/like")
async def forum_toggle_like(post_id: int, request: Request):
    user = await get_current_user(request)
    _check_forum_rate_limit(db := get_db(), user["id"], "like", FORUM_LIKES_PER_HOUR)
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, user_id, status FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        if post["user_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="No puedes dar like a tu propia publicación")

        cursor.execute("SELECT id FROM forum_likes WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
        existing = cursor.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            cursor.execute("DELETE FROM forum_likes WHERE id = %s", (existing["id"],))
            cursor.execute("UPDATE forum_posts SET like_count = GREATEST(like_count - 1, 0) WHERE id = %s", (post_id,))
            liked = False
        else:
            cursor.execute(
                "INSERT INTO forum_likes (post_id, user_id, created_at) VALUES (%s, %s, %s)",
                (post_id, user["id"], now),
            )
            cursor.execute("UPDATE forum_posts SET like_count = like_count + 1 WHERE id = %s", (post_id,))
            liked = True
        db.commit()
        cursor.execute("SELECT like_count FROM forum_posts WHERE id = %s", (post_id,))
        count_row = cursor.fetchone()
        return {"liked": liked, "like_count": count_row["like_count"] if count_row else 0}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar like")
    finally:
        db.close()


@api_router.post("/forum/posts/{post_id}/bookmark")
async def forum_toggle_bookmark(post_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        cursor.execute("SELECT id FROM forum_bookmarks WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
        existing = cursor.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            cursor.execute("DELETE FROM forum_bookmarks WHERE id = %s", (existing["id"],))
            bookmarked = False
        else:
            cursor.execute(
                "INSERT INTO forum_bookmarks (post_id, user_id, created_at) VALUES (%s, %s, %s)",
                (post_id, user["id"], now),
            )
            bookmarked = True
        db.commit()
        return {"bookmarked": bookmarked}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar bookmark")
    finally:
        db.close()


@api_router.post("/forum/posts/{post_id}/follow")
async def forum_toggle_follow(post_id: int, request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] != "active":
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        cursor.execute("SELECT id FROM forum_follows WHERE post_id = %s AND user_id = %s", (post_id, user["id"]))
        existing = cursor.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            cursor.execute("DELETE FROM forum_follows WHERE id = %s", (existing["id"],))
            following = False
        else:
            cursor.execute(
                "INSERT INTO forum_follows (post_id, user_id, created_at) VALUES (%s, %s, %s)",
                (post_id, user["id"], now),
            )
            following = True
        db.commit()
        return {"following": following}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar follow")
    finally:
        db.close()


# ── Reportes ────────────────────────────────────────────────────────────────

@api_router.post("/forum/reports")
async def forum_create_report(request: Request):
    user = await get_current_user(request)
    _check_forum_rate_limit(db := get_db(), user["id"], "report", FORUM_REPORTS_PER_HOUR)
    body = await request.json()
    post_id = body.get("post_id")
    reply_id = body.get("reply_id")
    reason = (body.get("reason") or "").strip()
    explanation = (body.get("explanation") or "").strip()

    valid_reasons = {"spam", "offensive", "harassment", "inappropriate", "off_topic", "other"}
    if reason not in valid_reasons:
        raise HTTPException(status_code=400, detail="Motivo de reporte no válido")
    if not post_id and not reply_id:
        raise HTTPException(status_code=400, detail="Debe especificar un post o reply para reportar")

    try:
        cursor = db.cursor()
        if post_id:
            cursor.execute("SELECT id, user_id, status FROM forum_posts WHERE id = %s", (post_id,))
            target = cursor.fetchone()
            if not target or target["status"] != "active":
                raise HTTPException(status_code=404, detail="Publicación no encontrada")
            if target["user_id"] == user["id"]:
                raise HTTPException(status_code=400, detail="No puedes reportar tu propio contenido")
            cursor.execute(
                "SELECT id FROM forum_reports WHERE reporter_id = %s AND post_id = %s AND status IN ('pending','reviewed')",
                (user["id"], post_id),
            )
        else:
            cursor.execute("SELECT id, post_id, user_id, status FROM forum_replies WHERE id = %s", (reply_id,))
            target = cursor.fetchone()
            if not target or target["status"] != "active":
                raise HTTPException(status_code=404, detail="Respuesta no encontrada")
            if target["user_id"] == user["id"]:
                raise HTTPException(status_code=400, detail="No puedes reportar tu propio contenido")
            cursor.execute(
                "SELECT id FROM forum_reports WHERE reporter_id = %s AND reply_id = %s AND status IN ('pending','reviewed')",
                (user["id"], reply_id),
            )

        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Ya has reportado este contenido")

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """INSERT INTO forum_reports (reporter_id, post_id, reply_id, reason, explanation, created_at)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
            (user["id"], post_id, reply_id, reason, explanation if explanation else None, now),
        )
        row = cursor.fetchone()
        db.commit()
        return {"reported": True, "id": row["id"]}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear reporte")
    finally:
        db.close()


# ── Búsqueda ────────────────────────────────────────────────────────────────

@api_router.get("/forum/search")
async def forum_search(
    q: str = "",
    category: Optional[int] = None,
    sort: str = "relevance",
    page: int = 1,
    limit: int = FORUM_PAGE_DEFAULT,
):
    limit = min(max(limit, 1), FORUM_PAGE_MAX)
    page = max(page, 1)
    offset = (page - 1) * limit
    db = get_db()
    try:
        cursor = db.cursor()
        where = ["fp.status = 'active'"]
        params = []
        if q.strip():
            where.append("(fp.title ILIKE %s OR fp.content ILIKE %s)")
            search_term = f"%{q.strip()}%"
            params.extend([search_term, search_term])
        if category:
            where.append("fp.category_id = %s")
            params.append(category)
        where_sql = " AND ".join(where)

        order_map = {
            "relevance": "fp.created_at DESC",
            "newest": "fp.created_at DESC",
            "popular": "fp.like_count DESC, fp.views DESC",
        }
        order = order_map.get(sort, order_map["relevance"])

        cursor.execute(f"SELECT COUNT(*) AS total FROM forum_posts fp WHERE {where_sql}", tuple(params))
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""SELECT fp.id, fp.user_id, u.username AS author_username, u.name AS author_name,
                       fp.category_id, fc.name AS category_name, fc.icon AS category_icon, fc.color AS category_color,
                       fp.title, fp.slug, fp.status, fp.views, fp.reply_count, fp.like_count,
                       fp.is_pinned, fp.is_resolved, fp.book_id, fp.created_at, fp.updated_at
                FROM forum_posts fp
                LEFT JOIN users u ON fp.user_id = u.id
                LEFT JOIN forum_categories fc ON fp.category_id = fc.id
                WHERE {where_sql}
                ORDER BY {order}
                LIMIT %s OFFSET %s""",
            tuple(params) + (limit, offset),
        )
        posts = cursor.fetchall()
        return {
            "posts": posts,
            "total": total,
            "page": page,
            "pages": math.ceil(total / limit) if total else 0,
        }
    finally:
        db.close()


# ── Actividad de usuario ────────────────────────────────────────────────────

@api_router.get("/forum/user/{target_user_id}/activity")
async def forum_user_activity(target_user_id: int):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM forum_posts WHERE user_id = %s AND status != 'deleted'",
            (target_user_id,),
        )
        posts_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM forum_replies WHERE user_id = %s AND status != 'deleted'",
            (target_user_id,),
        )
        replies_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM forum_replies fr JOIN forum_posts fp ON fr.post_id = fp.id WHERE fr.user_id = %s AND fr.is_accepted = TRUE AND fr.status = 'active'",
            (target_user_id,),
        )
        solutions_count = cursor.fetchone()["total"]

        cursor.execute(
            """SELECT fp.id, fp.title, fp.slug, fp.created_at, fc.name AS category_name, fc.icon AS category_icon
               FROM forum_posts fp
               LEFT JOIN forum_categories fc ON fp.category_id = fc.id
               WHERE fp.user_id = %s AND fp.status != 'deleted'
               ORDER BY fp.created_at DESC LIMIT 5""",
            (target_user_id,),
        )
        recent_posts = cursor.fetchall()

        return {
            "posts": posts_count,
            "replies": replies_count,
            "solutions": solutions_count,
            "recent_posts": recent_posts,
        }
    finally:
        db.close()


@api_router.get("/forum/bookmarks")
async def forum_get_bookmarks(request: Request):
    user = await get_current_user(request)
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT fp.id, fp.title, fp.slug, fp.created_at, fp.reply_count, fp.like_count,
                      fc.name AS category_name, fc.icon AS category_icon
               FROM forum_bookmarks fb
               JOIN forum_posts fp ON fb.post_id = fp.id
               LEFT JOIN forum_categories fc ON fp.category_id = fc.id
               WHERE fb.user_id = %s AND fp.status = 'active'
               ORDER BY fb.created_at DESC""",
            (user["id"],),
        )
        return {"bookmarks": cursor.fetchall()}
    finally:
        db.close()


# ── Conversaciones sobre este libro (para ReaderPage) ────────────────────────

@api_router.get("/books/{book_id}/forum-posts")
async def forum_posts_for_book(book_id: int):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            """SELECT fp.id, fp.title, fp.slug, fp.user_id, u.username AS author_username,
                      fp.reply_count, fp.like_count, fp.created_at
               FROM forum_posts fp
               LEFT JOIN users u ON fp.user_id = u.id
               WHERE fp.book_id = %s AND fp.status = 'active'
               ORDER BY fp.created_at DESC LIMIT 5""",
            (book_id,),
        )
        posts = cursor.fetchall()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM forum_posts WHERE book_id = %s AND status = 'active'",
            (book_id,),
        )
        total = cursor.fetchone()["total"]
        return {"posts": posts, "total": total}
    finally:
        db.close()


# ── Admin: Moderación ───────────────────────────────────────────────────────

@api_router.put("/admin/forum/posts/{post_id}/status")
async def forum_admin_change_post_status(post_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    body = await request.json()
    new_status = body.get("status")
    valid_statuses = {"active", "hidden", "closed", "deleted"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Estado no válido")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status, category_id FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        old_status = post["status"]
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("UPDATE forum_posts SET status = %s, updated_at = %s WHERE id = %s", (new_status, now, post_id))

        # Actualizar post_count en forum_categories
        if old_status != "deleted" and new_status == "deleted":
            # Post marcado como deleted: decrementar
            cursor.execute("UPDATE forum_categories SET post_count = GREATEST(post_count - 1, 0) WHERE id = %s", (post["category_id"],))
        elif old_status == "deleted" and new_status != "deleted":
            # Post restaurado desde deleted: incrementar
            cursor.execute("UPDATE forum_categories SET post_count = post_count + 1 WHERE id = %s", (post["category_id"],))

        db.commit()
        _audit_log(db, user["id"], f"set_post_{new_status}", "post", post_id)
        return {"updated": True, "status": new_status}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al cambiar estado")
    finally:
        db.close()


@api_router.put("/admin/forum/replies/{reply_id}/status")
async def forum_admin_change_reply_status(reply_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    body = await request.json()
    new_status = body.get("status")
    valid_statuses = {"active", "hidden", "deleted"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Estado no válido")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status, post_id FROM forum_replies WHERE id = %s", (reply_id,))
        reply = cursor.fetchone()
        if not reply:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("UPDATE forum_replies SET status = %s, updated_at = %s WHERE id = %s", (new_status, now, reply_id))
        if new_status in ("hidden", "deleted"):
            cursor.execute("UPDATE forum_posts SET reply_count = GREATEST(reply_count - 1, 0) WHERE id = %s", (reply["post_id"],))
        elif new_status == "active" and reply["status"] in ("hidden", "deleted"):
            cursor.execute("UPDATE forum_posts SET reply_count = reply_count + 1 WHERE id = %s", (reply["post_id"],))
        db.commit()
        _audit_log(db, user["id"], f"set_reply_{new_status}", "reply", reply_id)
        return {"updated": True, "status": new_status}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al cambiar estado")
    finally:
        db.close()


@api_router.put("/admin/forum/posts/{post_id}/pin")
async def forum_admin_toggle_pin(post_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, is_pinned FROM forum_posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        new_pinned = not post["is_pinned"]
        cursor.execute("UPDATE forum_posts SET is_pinned = %s WHERE id = %s", (new_pinned, post_id))
        db.commit()
        _audit_log(db, user["id"], "pin_post" if new_pinned else "unpin_post", "post", post_id)
        return {"pinned": new_pinned}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al fijar")
    finally:
        db.close()


# ── Admin: Reportes ─────────────────────────────────────────────────────────

@api_router.get("/admin/forum/reports")
async def forum_admin_list_reports(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = FORUM_PAGE_DEFAULT,
):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    limit = min(max(limit, 1), FORUM_PAGE_MAX)
    page = max(page, 1)
    offset = (page - 1) * limit
    db = get_db()
    try:
        cursor = db.cursor()
        where = []
        params = []
        if status:
            where.append("fr.status = %s")
            params.append(status)
        where_sql = " AND ".join(where) if where else "1=1"

        cursor.execute(f"SELECT COUNT(*) AS total FROM forum_reports fr WHERE {where_sql}", tuple(params))
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""SELECT fr.*, u.username AS reporter_username,
                       fp.title AS post_title,
                       fu.username AS reply_author_username
                FROM forum_reports fr
                LEFT JOIN users u ON fr.reporter_id = u.id
                LEFT JOIN forum_posts fp ON fr.post_id = fp.id
                LEFT JOIN forum_replies fr2 ON fr.reply_id = fr2.id
                LEFT JOIN users fu ON fr2.user_id = fu.id
                WHERE {where_sql}
                ORDER BY fr.created_at DESC
                LIMIT %s OFFSET %s""",
            tuple(params) + (limit, offset),
        )
        reports = cursor.fetchall()
        return {
            "reports": reports,
            "total": total,
            "page": page,
            "pages": math.ceil(total / limit) if total else 0,
        }
    finally:
        db.close()


@api_router.put("/admin/forum/reports/{report_id}")
async def forum_admin_resolve_report(report_id: int, request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    body = await request.json()
    new_status = body.get("status")
    valid_statuses = {"resolved", "dismissed"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Estado no válido")
    admin_note = (body.get("admin_note") or "").strip()
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, status FROM forum_reports WHERE id = %s", (report_id,))
        report = cursor.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE forum_reports SET status = %s, admin_note = %s, reviewed_by = %s, reviewed_at = %s WHERE id = %s",
            (new_status, admin_note if admin_note else None, user["id"], now, report_id),
        )
        db.commit()
        _audit_log(db, user["id"], f"report_{new_status}", "report", report_id, admin_note)
        return {"updated": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al resolver reporte")
    finally:
        db.close()


# ── Admin: Stats y Auditoría ────────────────────────────────────────────────

@api_router.get("/admin/forum/stats")
async def forum_admin_stats(request: Request):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM forum_posts WHERE status != 'deleted'")
        total_posts = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM forum_replies WHERE status != 'deleted'")
        total_replies = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM forum_reports WHERE status = 'pending'")
        pending_reports = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM forum_categories WHERE is_active = TRUE")
        active_categories = cursor.fetchone()["total"]
        now_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        cursor.execute("SELECT COUNT(*) AS total FROM forum_posts WHERE created_at >= %s", (now_24h,))
        posts_today = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM forum_replies WHERE created_at >= %s", (now_24h,))
        replies_today = cursor.fetchone()["total"]
        return {
            "total_posts": total_posts,
            "total_replies": total_replies,
            "pending_reports": pending_reports,
            "active_categories": active_categories,
            "posts_today": posts_today,
            "replies_today": replies_today,
        }
    finally:
        db.close()


@api_router.get("/admin/forum/audit")
async def forum_admin_audit(request: Request, page: int = 1, limit: int = FORUM_PAGE_DEFAULT):
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    limit = min(max(limit, 1), FORUM_PAGE_MAX)
    page = max(page, 1)
    offset = (page - 1) * limit
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM forum_audit_log")
        total = cursor.fetchone()["total"]
        cursor.execute(
            """SELECT fal.*, u.username AS admin_username
               FROM forum_audit_log fal
               LEFT JOIN users u ON fal.admin_id = u.id
               ORDER BY fal.created_at DESC
               LIMIT %s OFFSET %s""",
            (limit, offset),
        )
        logs = cursor.fetchall()
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "pages": math.ceil(total / limit) if total else 0,
        }
    finally:
        db.close()


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
