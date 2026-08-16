# -*- coding: utf-8 -*-
"""
Migración FASE 2 (Códigos QR de referencia).

Crea la infraestructura de base de datos para los QR físicos de registro:

1. Tabla qr_codes: catálogo de códigos QR (QR001, QR002, ...) con nombre
   descriptivo y activación/desactivación.
2. Tabla qr_visits: eventos de visita con deduplicación UNIQUE(qr_id, ip,
   visit_date) — una visita por IP por día por QR.
3. Columna users.referred_by_qr_id: FK opcional que asocia el usuario creado
   con el QR por el que llegó al registro. Se conserva NULL en todos los
   usuarios existentes (no se rellena con ningún valor).

La migración es idempotente y segura para ejecutarse más de una vez:
solo DDL con CREATE ... IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
No contiene INSERT, UPDATE, DELETE ni TRUNCATE: no toca datos existentes.

Pendiente (fuera de esta fase): integrar la llamada a migrate() en el
arranque de server.py, como se hace con las demás migraciones.
"""
import os

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

# psycopg2 requiere 'postgresql://' en vez de 'postgres://' (que usa Render por defecto)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _crear_tablas(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qr_codes (
        id SERIAL PRIMARY KEY,
        code VARCHAR(32) UNIQUE NOT NULL,
        name TEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qr_visits (
        id SERIAL PRIMARY KEY,
        qr_id INTEGER NOT NULL REFERENCES qr_codes(id) ON DELETE CASCADE,
        ip TEXT NOT NULL,
        visit_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(qr_id, ip, visit_date)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_qr_visits_qr
    ON qr_visits(qr_id)
    """)
    # La columna debe agregarse solo si no existe; los usuarios existentes
    # conservan NULL (no se rellena aquí con ningún valor).
    cursor.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_qr_id INTEGER REFERENCES qr_codes(id) ON DELETE SET NULL"
    )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_referred_by_qr
    ON users(referred_by_qr_id)
    """)


def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor = conn.cursor()
        print("Iniciando migración FASE 2 (QR de referencia)...")
        _crear_tablas(cursor)
        conn.commit()
        print("Migración FASE 2 (QR de referencia) completada.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()