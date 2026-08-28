#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpiar referencias huérfanas en rayos_transactions.

Este script cambia book_id = NULL para transacciones que referencian
libros que ya no existen (IDs 142 y 163).

NO se ejecuta automáticamente. Debe ejecutarse manualmente cuando se autorice.
"""

import os
import sys
import psycopg2
import psycopg2.extras


def get_database_url():
    """Obtiene DATABASE_URL del entorno."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL no está definida en el entorno")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def main():
    DATABASE_URL = get_database_url()
    
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    ORPHAN_BOOK_IDS = (142, 163)
    
    try:
        print("=== LIMPIEZA RAYOS_TRANSACTIONS HUÉRFANAS ===")
        print()
        
        # 1. Consultar transacciones afectadas
        cursor.execute("""
            SELECT id, user_id, amount, type, description, book_id, created_at
            FROM rayos_transactions
            WHERE book_id IN %s
        """, (ORPHAN_BOOK_IDS,))
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("No se encontraron transacciones huérfanas.")
            return True
        
        print(f"Transacciones a limpiar: {len(transactions)}")
        for t in transactions:
            print(f"  ID {t['id']}: user_id={t['user_id']}, amount={t['amount']}, type={t['type']}, book_id={t['book_id']}, desc={t['description'][:60] if t['description'] else ''}...")
        
        # 2. Verificar que book_id permite NULL
        cursor.execute("""
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = 'rayos_transactions' AND column_name = 'book_id'
        """)
        col = cursor.fetchone()
        if col['is_nullable'] != 'YES':
            print(f"ERROR: book_id NO permite NULL (is_nullable={col['is_nullable']}). No se puede proceder.")
            print("Se requeriría ALTER TABLE rayos_transactions ALTER COLUMN book_id DROP NOT NULL;")
            return False
        
        print("✓ book_id permite NULL")
        
        # 3. Verificar que no hay FK en book_id
        cursor.execute("""
            SELECT constraint_name FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'rayos_transactions' AND tc.constraint_type = 'FOREIGN KEY'
            AND kcu.column_name = 'book_id'
        """)
        fks = cursor.fetchall()
        if fks:
            print(f"ADVERTENCIA: Existen FKs en book_id: {[f['constraint_name'] for f in fks]}")
            print("Esto podría impedir el UPDATE. Proceder con precaución.")
        else:
            print("✓ No hay FK en book_id")
        
        # 4. Ejecutar UPDATE
        print("\n--- Ejecutando UPDATE ---")
        cursor.execute("""
            UPDATE rayos_transactions
            SET book_id = NULL
            WHERE book_id IN %s
        """, (ORPHAN_BOOK_IDS,))
        
        updated = cursor.rowcount
        print(f"Filas actualizadas: {updated}")
        
        # 5. Verificar
        cursor.execute("""
            SELECT id, book_id FROM rayos_transactions WHERE book_id IN %s
        """, (ORPHAN_BOOK_IDS,))
        remaining = cursor.fetchall()
        
        if remaining:
            print(f"ERROR: Quedan {len(remaining)} transacciones sin limpiar")
            for r in remaining:
                print(f"  ID {r['id']}: book_id={r['book_id']}")
            conn.rollback()
            return False
        
        print("✓ Todas las transacciones huérfanas limpiadas (book_id = NULL)")
        
        # Commit
        conn.commit()
        print("\n=== LIMPIEZA COMPLETADA CON ÉXITO ===")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n=== ERROR: {e} ===")
        print("ROLLBACK ejecutado. No se modificó nada.")
        return False
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)