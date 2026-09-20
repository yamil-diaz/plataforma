# -*- coding: utf-8 -*-
"""
Limpieza controlada del usuario de prueba 46.

NO elimina archivos del disco.
NO toca ningún libro.
Solo elimina el usuario de prueba y sus datos residuales.
"""

import os
import sys
import psycopg2


USER_ID = 46
BOOK_ID = 298

EXPECTED = {
    "name": "Dedup Test User",
    "username": "deduptestuser4614",
    "email": "dedup_test_AD2054B9@mailinator.com",
    "role": "user",
}


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL no está configurada.")
        sys.exit(1)

    print("=== CLEANUP USER 46 ===")
    print(f"Usuario objetivo: {USER_ID}")
    print(f"Libro que DEBE estar eliminado: {BOOK_ID}")
    print()

    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:

            # ---------------------------------------------------------
            # 1. Verificar identidad exacta del usuario
            # ---------------------------------------------------------
            cur.execute(
                """
                SELECT id, name, username, email, role
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (USER_ID,),
            )

            user = cur.fetchone()

            if user is None:
                raise RuntimeError("El usuario 46 no existe.")

            actual = {
                "name": user[1],
                "username": user[2],
                "email": user[3],
                "role": user[4],
            }

            if actual != EXPECTED:
                raise RuntimeError(
                    f"El usuario 46 NO coincide con el usuario de prueba.\n"
                    f"Esperado: {EXPECTED}\n"
                    f"Encontrado: {actual}"
                )

            print("OK: identidad del usuario 46 confirmada.")

            # ---------------------------------------------------------
            # 2. El libro 298 debe haber desaparecido
            # ---------------------------------------------------------
            cur.execute(
                "SELECT COUNT(*) FROM books WHERE id = %s",
                (BOOK_ID,),
            )

            if cur.fetchone()[0] != 0:
                raise RuntimeError(
                    "ABORTADO: el libro 298 todavía existe."
                )

            print("OK: libro 298 no existe.")

            # ---------------------------------------------------------
            # 3. El usuario no debe tener ningún libro
            # ---------------------------------------------------------
            cur.execute(
                "SELECT id, title FROM books WHERE uploader_id = %s",
                (USER_ID,),
            )

            books = cur.fetchall()

            if books:
                raise RuntimeError(
                    f"ABORTADO: el usuario 46 todavía tiene "
                    f"{len(books)} libro(s): {books}"
                )

            print("OK: usuario 46 no tiene libros.")

            # ---------------------------------------------------------
            # 4. Verificar dependencias conocidas
            # ---------------------------------------------------------
            checks = {
                "rayos_transactions": (
                    "SELECT COUNT(*) FROM rayos_transactions "
                    "WHERE user_id = %s"
                ),
                "reading_progress": (
                    "SELECT COUNT(*) FROM reading_progress "
                    "WHERE user_id = %s"
                ),
                "reading_sessions": (
                    "SELECT COUNT(*) FROM reading_sessions "
                    "WHERE user_id = %s"
                ),
                "reading_daily_pages": (
                    "SELECT COUNT(*) FROM reading_daily_pages "
                    "WHERE user_id = %s"
                ),
            }

            counts = {}

            for table, sql in checks.items():
                cur.execute(sql, (USER_ID,))
                counts[table] = cur.fetchone()[0]

            print("\n=== DEPENDENCIAS ENCONTRADAS ===")

            for table, count in counts.items():
                print(f"{table}: {count}")

            # ---------------------------------------------------------
            # 5. Eliminar SOLO las dependencias conocidas
            # ---------------------------------------------------------
            print("\n=== DELETE ===")

            for table, sql in {
                "rayos_transactions": (
                    "DELETE FROM rayos_transactions WHERE user_id = %s"
                ),
                "reading_progress": (
                    "DELETE FROM reading_progress WHERE user_id = %s"
                ),
                "reading_sessions": (
                    "DELETE FROM reading_sessions WHERE user_id = %s"
                ),
                "reading_daily_pages": (
                    "DELETE FROM reading_daily_pages WHERE user_id = %s"
                ),
            }.items():

                cur.execute(sql, (USER_ID,))
                print(f"{table}: {cur.rowcount} eliminado(s)")

            # ---------------------------------------------------------
            # 6. Confirmar nuevamente que no tiene libros
            # ---------------------------------------------------------
            cur.execute(
                "SELECT COUNT(*) FROM books WHERE uploader_id = %s",
                (USER_ID,),
            )

            if cur.fetchone()[0] != 0:
                raise RuntimeError(
                    "ABORTADO: apareció un libro asociado al usuario 46."
                )

            # ---------------------------------------------------------
            # 7. Eliminar usuario
            # ---------------------------------------------------------
            cur.execute(
                "DELETE FROM users WHERE id = %s",
                (USER_ID,),
            )

            if cur.rowcount != 1:
                raise RuntimeError(
                    f"DELETE de users devolvió {cur.rowcount}; "
                    "se esperaba exactamente 1."
                )

            print("users: 1 eliminado")

            # ---------------------------------------------------------
            # 8. Commit
            # ---------------------------------------------------------
            conn.commit()

        print("\n=== POST-CHECK ===")

        with conn.cursor() as cur:

            cur.execute(
                "SELECT COUNT(*) FROM users WHERE id = %s",
                (USER_ID,),
            )
            user_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM books WHERE id = %s",
                (BOOK_ID,),
            )
            book_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM books WHERE uploader_id = %s",
                (USER_ID,),
            )
            uploaded_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM rayos_transactions WHERE user_id = %s",
                (USER_ID,),
            )
            rayos_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM reading_progress WHERE user_id = %s",
                (USER_ID,),
            )
            progress_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM reading_sessions WHERE user_id = %s",
                (USER_ID,),
            )
            sessions_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM reading_daily_pages WHERE user_id = %s",
                (USER_ID,),
            )
            daily_count = cur.fetchone()[0]

            results = {
                "users.id=46": user_count,
                "books.id=298": book_count,
                "books.uploader_id=46": uploaded_count,
                "rayos_transactions.user_id=46": rayos_count,
                "reading_progress.user_id=46": progress_count,
                "reading_sessions.user_id=46": sessions_count,
                "reading_daily_pages.user_id=46": daily_count,
            }

            for name, count in results.items():
                print(f"{name}: {count}")

            if any(count != 0 for count in results.values()):
                raise RuntimeError(
                    "POST-CHECK FALLÓ: todavía quedan registros."
                )

        print("\nCLEANUP PASS")
        print("Usuario 46 eliminado correctamente.")
        print("No se eliminó ningún archivo del disco.")

    except Exception as exc:
        conn.rollback()
        print("\nROLLBACK")
        print(f"CLEANUP FAILED / ABORTED: {exc}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
