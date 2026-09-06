# -*- coding: utf-8 -*-
"""
storage_config.py — Configuración centralizada de almacenamiento.

Única fuente de verdad para STORAGE_DIR y subdirectorios.
No duplicar estas constantes en otros archivos.
"""
import os

# Directorio base del proyecto (backend/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Variable de entorno obligatoria en producción
# En Render: STORAGE_DIR=/var/data/aeternum (Persistent Disk)
# En desarrollo: se puede omitir para usar backend/storage
STORAGE_DIR_ENV = os.getenv("STORAGE_DIR")

# Detección de entorno de producción
IS_PRODUCTION = os.getenv("RENDER") == "true" or os.getenv("ENV") == "production"

# Validación estricta en producción
if IS_PRODUCTION and not STORAGE_DIR_ENV:
    raise RuntimeError(
        "STORAGE_DIR is required in production. "
        "Set STORAGE_DIR=/var/data/aeternum in Render environment variables."
    )

# STORAGE_DIR final: variable de entorno o fallback a backend/storage (solo desarrollo)
STORAGE_DIR = os.path.abspath(STORAGE_DIR_ENV or os.path.join(BASE_DIR, "storage"))

# Subdirectorios de almacenamiento
STORAGE_BOOKS = os.path.join(STORAGE_DIR, "books")
STORAGE_COVERS = os.path.join(STORAGE_DIR, "covers")
STORAGE_VIDEOS = os.path.join(STORAGE_DIR, "videos")
STORAGE_TEMP = os.path.join(STORAGE_DIR, "temp")
TEMP_DIR = STORAGE_TEMP  # Alias para compatibilidad con tests


def ensure_storage_directories():
    """Crea/verifica los directorios de almacenamiento necesarios.
    
    No borra archivos existentes. No reemplaza directorios.
    Solo crea si no existen.
    """
    for directory in (STORAGE_BOOKS, STORAGE_COVERS, STORAGE_VIDEOS, STORAGE_TEMP):
        os.makedirs(directory, exist_ok=True)
    
    # Verificar permisos de escritura
    for directory in (STORAGE_BOOKS, STORAGE_COVERS, STORAGE_VIDEOS, STORAGE_TEMP):
        if not os.access(directory, os.W_OK):
            raise RuntimeError(f"Storage directory not writable: {directory}")


def get_storage_info():
    """Retorna información de diagnóstico del storage actual."""
    return {
        "STORAGE_DIR": STORAGE_DIR,
        "STORAGE_BOOKS": STORAGE_BOOKS,
        "STORAGE_COVERS": STORAGE_COVERS,
        "STORAGE_VIDEOS": STORAGE_VIDEOS,
        "STORAGE_TEMP": STORAGE_TEMP,
        "IS_PRODUCTION": IS_PRODUCTION,
        "STORAGE_DIR_FROM_ENV": bool(STORAGE_DIR_ENV),
    }


def validate_storage():
    """Valida que el storage esté correctamente configurado y sea accesible.
    
    Comprueba:
    1. STORAGE_DIR está definido
    2. STORAGE_DIR existe o puede crearse
    3. STORAGE_BOOKS existe o puede crearse
    4. STORAGE_COVERS existe o puede crearse
    5. STORAGE_TEMP existe o puede crearse
    6. STORAGE_VIDEOS existe o puede crearse
    7. Los directorios son escribibles
    
    En producción, falla con RuntimeError si algún check no pasa.
    """
    errors = []
    
    # 1. STORAGE_DIR definido
    if not STORAGE_DIR:
        errors.append("STORAGE_DIR is not defined")
    
    # 2-6. Verificar que cada directorio existe o puede crearse
    dirs_to_check = {
        "STORAGE_DIR": STORAGE_DIR,
        "STORAGE_BOOKS": STORAGE_BOOKS,
        "STORAGE_COVERS": STORAGE_COVERS,
        "STORAGE_TEMP": STORAGE_TEMP,
        "STORAGE_VIDEOS": STORAGE_VIDEOS,
    }
    
    for name, directory in dirs_to_check.items():
        if not directory:
            errors.append(f"{name} is not defined")
            continue
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            errors.append(f"{name} ({directory}) cannot be created: {e}")
            continue
        
        # Verificar permisos de escritura
        if not os.access(directory, os.W_OK):
            errors.append(f"{name} ({directory}) is not writable")
    
    if errors:
        raise RuntimeError(
            "Storage validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    
    return True


# Migración legacy idempotente (copia de backend/storage a STORAGE_DIR si son distintos)
DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")

def migrate_legacy_storage(storage_dir=None, default_storage_dir=None):
    """Copia idempotente de archivos del directorio legacy al persistente.
    
    Se ejecuta en cada arranque: si el destino ya tiene el archivo, no se copia.
    Si el origen no existe, no hace nada. NUNCA borra ni mueve.
    
    Args:
        storage_dir: Directorio de almacenamiento destino (default: STORAGE_DIR del módulo)
        default_storage_dir: Directorio legacy origen (default: DEFAULT_STORAGE_DIR del módulo)
    """
    storage_dir = storage_dir or STORAGE_DIR
    default_storage_dir = default_storage_dir or DEFAULT_STORAGE_DIR
    
    if os.path.abspath(storage_dir) == os.path.abspath(default_storage_dir):
        return
    
    for subdir in ("books", "covers", "videos"):
        origen = os.path.join(default_storage_dir, subdir)
        destino = os.path.join(storage_dir, subdir)
        if not os.path.isdir(origen):
            continue
        os.makedirs(destino, exist_ok=True)
        for nombre in os.listdir(origen):
            ruta_origen = os.path.join(origen, nombre)
            if os.path.isfile(ruta_origen):
                ruta_destino = os.path.join(destino, nombre)
                if not os.path.exists(ruta_destino):
                    try:
                        import shutil
                        shutil.copy2(ruta_origen, ruta_destino)
                    except OSError:
                        pass