#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
delete_book_128.py — ELIMINACIÓN SEGURA Y PUNTUAL DEL LIBRO ID 128.

Este script elimina EXCLUSIVAMENTE el libro con id=128 después de validaciones exhaustivas.
NO afecta ningún otro libro.

Uso:
  python delete_book_128.py --dry-run    # Solo diagnóstico
  python delete_book_128.py --execute    # Eliminación real (requiere confirmación)

Confirmación requerida para --execute: "ELIMINAR 128"
"""
import os
import sys
import argparse
import psycopg2
import psycopg2.extras

# ── Configuración ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

TARGET_ID = 128
EXPECTED_TITLE = "El Principito"
EXPECTED_AUTHOR = "Antoine de Saint-Exupéry"
CONFIRMATION_STRING = "ELIMINAR 128"

# IDs protegidos — JAMÁS eliminar
PROTECTED_IDS = {
    5, 6, 7, 8, 10, 11, 12, 13, 18, 19,
    21, 22, 29, 34, 41, 117, 145, 158,
    172, 173, 175,
}

# ── Utilidades ─────────────────────────────────────────────────────────────────

def _conectar():
    """Conecta a PostgreSQL con autocommit=False para control de transacción."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _obtener_fks_books(cursor):
    """Descubre todas las FK que apuntan a books(id) desde information_schema."""
    cursor.execute("""
        SELECT
            tc.table_name AS dependent_table,
            kcu.column_name AS dependent_column,
            rc.delete_rule,
            rc.update_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'books'
          AND ccu.column_name = 'id'
        ORDER BY tc.table_name, kcu.column_name
    """)
    return cursor.fetchall()


def _contar_dependencias(cursor, fks):
    """Cuenta dependencias existentes para book_id = 128 en cada tabla."""
    deps = {}
    for fk in fks:
        table = fk["dependent_table"]
        column = fk["dependent_column"]
        try:
            cursor.execute(
                f"SELECT COUNT(*) AS cnt FROM {table} WHERE {column} = %s",
                (TARGET_ID,)
            )
            cnt = cursor.fetchone()["cnt"]
            if cnt > 0:
                deps[table] = {"column": column, "count": cnt, "delete_rule": fk["delete_rule"]}
        except Exception as e:
            print(f"  Advertencia: no se pudo consultar {table}.{column}: {e}")
    return deps


def _verificar_libro(cursor):
    """Verifica que el libro ID 128 existe y coincide con título/autor esperados."""
    cursor.execute("""
        SELECT id, title, author_name
        FROM books
        WHERE id = %s
    """, (TARGET_ID,))
    row = cursor.fetchone()
    if not row:
        raise SystemExit(f"ERROR: Libro ID {TARGET_ID} NO EXISTE en la base de datos.")
    
    print(f"  Libro encontrado:")
    print(f"    ID:         {row['id']}")
    print(f"    Título:     {row['title']}")
    print(f"    Autor:      {row['author_name']}")
    
    if row["title"] != EXPECTED_TITLE:
        raise SystemExit(f"ERROR: Título no coincide. Esperado: '{EXPECTED_TITLE}', Encontrado: '{row['title']}'")
    if row["author_name"] != EXPECTED_AUTHOR:
        raise SystemExit(f"ERROR: Autor no coincide. Esperado: '{EXPECTED_AUTHOR}', Encontrado: '{row['author_name']}'")
    
    print(f"  ✓ Título y autor coinciden con lo esperado.")
    return row


def _verificar_protegidos():
    """Verifica que el ID objetivo NO esté en PROTECTED_IDS."""
    if TARGET_ID in PROTECTED_IDS:
        raise SystemExit(f"ERROR CRÍTICO: ID {TARGET_ID} está en PROTECTED_IDS. NO SE PUEDE ELIMINAR.")
    
    # Verificar también que ID 18 (el duplicado) sigue protegido
    if 18 not in PROTECTED_IDS:
        print(f"  ADVERTENCIA: ID 18 NO está en PROTECTED_IDS. Debería estar protegido.")
    else:
        print(f"  ✓ ID 18 está correctamente protegido.")
    
    print(f"  ✓ ID {TARGET_ID} NO está en PROTECTED_IDS.")


def _mostrar_dependencias(deps):
    """Muestra resumen de dependencias encontradas."""
    if not deps:
        print(f"  No hay dependencias en tablas referenciadas.")
        return
    
    print(f"  Dependencias encontradas para book_id = {TARGET_ID}:")
    for table, info in deps.items():
        rule = info["delete_rule"]
        cnt = info["count"]
        col = info["column"]
        print(f"    - {table}.{col}: {cnt} registro(s)  [ON DELETE {rule}]")


def _verificar_post_delete(cursor):
    """Verifica que el libro ya no existe y no quedan dependencias."""
    # Verificar que books.id = 128 ya no existe
    cursor.execute("SELECT 1 FROM books WHERE id = %s", (TARGET_ID,))
    if cursor.fetchone():
        raise SystemExit(f"ERROR POST-DELETE: Libro ID {TARGET_ID} SIGUE EXISTENTE tras DELETE.")
    
    # Verificar dependencias restantes
    fks = _obtener_fks_books(cursor)
    remaining = []
    for fk in fks:
        table = fk["dependent_table"]
        column = fk["dependent_column"]
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE {column} = %s", (TARGET_ID,))
        cnt = cursor.fetchone()["cnt"]
        if cnt > 0:
            remaining.append(f"{table}.{column} = {cnt}")
    
    if remaining:
        raise SystemExit(f"ERROR POST-DELETE: Quedan dependencias: {', '.join(remaining)}")
    
    print(f"  ✓ Verificación post-DELETE: libro eliminado y sin dependencias huérfanas.")


def _dry_run(cursor):
    """Ejecuta solo diagnóstico completo sin modificar nada."""
    print(f"{'='*70}")
    print(f"MODO: DRY-RUN — SOLO DIAGNÓSTICO")
    print(f"{'='*70}")
    
    # 1. Verificar libro
    print(f"\n1. Verificando libro ID {TARGET_ID}...")
    _verificar_libro(cursor)
    
    # 2. Verificar protegidos
    print(f"\n2. Verificando IDs protegidos...")
    _verificar_protegidos()
    
    # 3. Inspeccionar FKs
    print(f"\n3. Inspeccionando Foreign Keys hacia books(id)...")
    fks = _obtener_fks_books(cursor)
    print(f"  Total FKs encontradas: {len(fks)}")
    for fk in fks:
        print(f"    - {fk['dependent_table']}.{fk['dependent_column']} -> books.id  [ON DELETE {fk['delete_rule']}]")
    
    # 4. Contar dependencias
    print(f"\n4. Contando dependencias existentes para book_id = {TARGET_ID}...")
    deps = _contar_dependencias(cursor, fks)
    _mostrar_dependencias(deps)
    
    # 5. Resumen
    print(f"\n{'='*70}")
    print(f"RESUMEN DRY-RUN")
    print(f"{'='*70}")
    print(f"  Libro objetivo:      ID {TARGET_ID} — '{EXPECTED_TITLE}' — '{EXPECTED_AUTHOR}'")
    print(f"  En PROTECTED_IDS:    NO")
    print(f"  ID 18 protegido:     SÍ")
    print(f"  Tablas con FK:       {len(fks)}")
    print(f"  Dependencias:        {len(deps)} tabla(s) con {sum(d['count'] for d in deps.values())} registro(s)")
    print(f"  Acción propuesta:    DELETE FROM books WHERE id = {TARGET_ID}")
    print(f"  Regla FK esperada:   Las tablas con ON DELETE CASCADE borran automáticamente.")
    print(f"                       Las tablas con ON DELETE SET NULL ponen NULL.")
    print(f"                       Las tablas con ON DELETE RESTRICT/NO ACTION bloquean.")
    print(f"\n  DRY-RUN COMPLETADO — SIN MODIFICACIONES")
    print(f"{'='*70}")
    
    return deps


def _execute(cursor, conn, confirm):
    """Ejecuta la eliminación real dentro de transacción."""
    if confirm != CONFIRMATION_STRING:
        raise SystemExit(f"CONFIRMACIÓN RECHAZADA. Se esperaba exactamente: '{CONFIRMATION_STRING}'")
    
    print(f"{'='*70}")
    print(f"MODO: EXECUTE — ELIMINACIÓN REAL")
    print(f"{'='*70}")
    
    # Pre-verificaciones dentro de la transacción
    print(f"\n1. Pre-verificaciones...")
    _verificar_libro(cursor)
    _verificar_protegidos()
    
    fks = _obtener_fks_books(cursor)
    deps = _contar_dependencias(cursor, fks)
    _mostrar_dependencias(deps)
    
    # Verificar reglas FK que puedan bloquear
    blocking = []
    for table, info in deps.items():
        rule = info["delete_rule"]
        if rule in ("NO ACTION", "RESTRICT"):
            blocking.append(f"{table} (ON DELETE {rule})")
    
    if blocking:
        raise SystemExit(f"BLOQUEADO: Las siguientes tablas tienen ON DELETE {blocking[0].split()[-1]} y impedirían el borrado: {', '.join(blocking)}")
    
    # Ejecutar DELETE
    print(f"\n2. Ejecutando DELETE...")
    cursor.execute("""
        DELETE FROM books
        WHERE id = %s
        RETURNING id, title, author_name
    """, (TARGET_ID,))
    
    deleted = cursor.fetchone()
    if not deleted:
        conn.rollback()
        raise SystemExit(f"ERROR: DELETE no retornó filas. Posiblemente el ID ya no existe.")
    
    print(f"  Eliminado: ID {deleted['id']} — '{deleted['title']}' — '{deleted['author_name']}'")
    
    # Post-verificación
    print(f"\n3. Verificación post-DELETE...")
    _verificar_post_delete(cursor)
    
    # Commit
    print(f"\n4. Confirmando transacción (COMMIT)...")
    conn.commit()
    
    print(f"\n{'='*70}")
    print(f"ELIMINACIÓN COMPLETADA EXITOSAMENTE")
    print(f"{'='*70}")
    print(f"  Libro ID {TARGET_ID} eliminado permanentemente.")
    print(f"  Dependencias manejadas según reglas ON DELETE de cada FK.")
    print(f"{'='*70}")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Eliminación segura del libro ID 128")
    parser.add_argument("--dry-run", action="store_true", help="Solo diagnóstico, sin modificar")
    parser.add_argument("--execute", action="store_true", help="Eliminación real (requiere confirmación)")
    parser.add_argument("--confirm", type=str, default="", help=f"Confirmación obligatoria para --execute: '{CONFIRMATION_STRING}'")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        parser.error("Especifica --dry-run o --execute")
    if args.dry_run and args.execute:
        parser.error("No uses --dry-run y --execute simultáneamente")
    
    conn = _conectar()
    cursor = conn.cursor()
    
    try:
        if args.dry_run:
            _dry_run(cursor)
            return 0
        
        if args.execute:
            _execute(cursor, conn, args.confirm)
            return 0
    
    except SystemExit as e:
        if "ERROR" in str(e) or "BLOQUEADO" in str(e) or "CONFIRMACIÓN" in str(e):
            print(f"\n{'!'*70}")
            print(f"ABORTADO: {e}")
            print(f"{'!'*70}")
        conn.rollback()
        return 1
    except Exception as e:
        print(f"\n{'!'*70}")
        print(f"EXCEPCIÓN INESPERADA: {e}")
        print(f"Ejecutando ROLLBACK automático...")
        print(f"{'!'*70}")
        conn.rollback()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())