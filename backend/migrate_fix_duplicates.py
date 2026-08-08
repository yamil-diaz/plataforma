"""
Migración: Limpiar usuarios duplicados por email.
Mantiene el usuario con el ID más alto (el más reciente) y elimina los demás.
Luego agrega un índice UNIQUE si no existe.
"""
import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def migrate():
    if not DATABASE_URL:
        print("[MIGRATE-DUPLICATES] DATABASE_URL no definida, saltando.")
        return

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    try:
        # 1. Encontrar emails duplicados
        cursor.execute("""
            SELECT email, COUNT(*) as cnt, array_agg(id ORDER BY id) as ids
            FROM users
            GROUP BY email
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()

        if not duplicates:
            print("[MIGRATE-DUPLICATES] No se encontraron emails duplicados.")
        else:
            for dup in duplicates:
                email = dup["email"]
                ids = dup["ids"]
                keep_id = max(ids)  # Mantener el más reciente
                remove_ids = [i for i in ids if i != keep_id]
                print(f"[MIGRATE-DUPLICATES] Email '{email}' duplicado en IDs: {ids}. Manteniendo ID={keep_id}, eliminando {remove_ids}")

                for rid in remove_ids:
                    # Transferir libros del usuario duplicado al usuario que se mantiene
                    cursor.execute("UPDATE books SET uploader_id = %s WHERE uploader_id = %s", (keep_id, rid))
                    # Eliminar el usuario duplicado
                    cursor.execute("DELETE FROM users WHERE id = %s", (rid,))
                    print(f"[MIGRATE-DUPLICATES] Usuario ID={rid} eliminado.")

            conn.commit()
            print("[MIGRATE-DUPLICATES] Duplicados limpiados exitosamente.")

        # 2. Asegurar que el constraint UNIQUE exista en email
        try:
            cursor.execute("""
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'users_email_unique_fix' 
                AND conrelid = 'users'::regclass
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD CONSTRAINT users_email_unique_fix UNIQUE (email)")
                conn.commit()
                print("[MIGRATE-DUPLICATES] Constraint UNIQUE agregado a users.email")
            else:
                print("[MIGRATE-DUPLICATES] Constraint UNIQUE ya existe.")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print("[MIGRATE-DUPLICATES] Error: aún hay duplicados, no se pudo agregar UNIQUE constraint.")
        except psycopg2.errors.DuplicateTable:
            conn.rollback()
            print("[MIGRATE-DUPLICATES] Constraint UNIQUE ya existe (DuplicateTable).")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATE-DUPLICATES] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
