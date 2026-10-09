#!/usr/bin/env python3
"""
Script de migración: cambiar roles user→buyer, author→seller
Ejecutar una sola vez después del deploy.
"""
import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def migrate_roles():
    """Migra los roles antiguos a los nuevos."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    try:
        print("Migrando roles...")
        
        # user → buyer
        cursor.execute("UPDATE users SET role = 'buyer' WHERE role = 'user'")
        print(f"  {cursor.rowcount} usuarios migrados de 'user' a 'buyer'")
        
        # author → seller (both English and Spanish variants)
        cursor.execute("UPDATE users SET role = 'seller' WHERE role IN ('author', 'autor')")
        print(f"  {cursor.rowcount} autores migrados de 'author'/'autor' a 'seller'")
        
        # Marcar sellers existentes como verificados
        cursor.execute("UPDATE users SET seller_verified = TRUE WHERE role = 'seller'")
        print(f"  {cursor.rowcount} vendedores marcados como verificados")
        
        conn.commit()
        print("✓ Migración completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error en migración: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_roles()
