# -*- coding: utf-8 -*-
"""
update_books_text.py — HERRAMIENTA DE DIAGNÓSTICO (SOLO LECTURA).

ANTECEDENTE: esta herramienta generó en el pasado contenido FABRICADO
(párrafos repetidos y capítulos falsos "CAPÍTULO 1..10") que corrompió
126 libros de producción. Desde esta versión NO MODIFICA NINGÚN DATO:
solo enumera los libros con contenido corto y su estado de validación.

NUNCA ejecuta INSERT/UPDATE/DELETE: la conexión se abre en modo read-only.
Requiere DATABASE_URL para ejecutarse.

Uso:
  DATABASE_URL="postgresql://..." python update_books_text.py
"""
import os
import sys
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lectura

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Establece DATABASE_URL antes de ejecutar este script.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

UMBRAL_CORTO_CHARS = 5000


def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_session(readonly=True, autocommit=False)
    cursor = conn.cursor()

    print("=" * 70)
    print("ADVERTENCIA: herramienta SOLO LECTURA. No modifica ningún libro.")
    print("=" * 70)

    cursor.execute(
        "SELECT id, title, author_name, content, published FROM books ORDER BY id"
    )
    books = cursor.fetchall()

    cortos = 0
    for book in books:
        content = book["content"] or ""
        if len(content) < UMBRAL_CORTO_CHARS:
            validacion = lectura.validar_contenido_libro(content, None, fuente="diagnostico")
            estado = "INVÁLIDO" if not validacion["valid"] else "VÁLIDO"
            errores = "; ".join(validacion["errors"]) if validacion["errors"] else "-"
            print(
                f"- [{estado}] id={book['id']} '{book['title']}' "
                f"(chars={len(content)}, publicado={book['published']}) "
                f"errores: {errores}"
            )
            cortos += 1

    conn.rollback()
    conn.close()
    print(f"Total libros con contenido < {UMBRAL_CORTO_CHARS} caracteres: {cortos}.")
    print("Ningún libro fue modificado.")


if __name__ == "__main__":
    main()