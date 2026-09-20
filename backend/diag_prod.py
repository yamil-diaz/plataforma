import os
import json
import sys
import socket
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print(json.dumps({"ok": False, "error": "DATABASE_URL no definida"}), file=sys.stdout)
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

RENDER_SUFFIXES = [".oregon-postgres.render.com", ".postgres.render.com"]


def resolve_url(url):
    """Devuelve una URL cuyo host resuelve por DNS (sin exponer la URL)."""
    if "@" not in url:
        return url
    head, tail = url.split("@", 1)
    hostport, _, rest = tail.partition("/")
    host = hostport
    port = ""
    if ":" in hostport:
        host, _, port = hostport.partition(":")
    try:
        socket.getaddrinfo(host, None)
        return url
    except socket.gaierror:
        for suffix in RENDER_SUFFIXES:
            candidate = head + "@" + host + suffix + (":" + port if port else "")
            if rest:
                candidate += "/" + rest
            try:
                socket.getaddrinfo(host + suffix, None)
                return candidate
            except socket.gaierror:
                continue
    return url

DIAG_QUERIES = {
    "server_version": "SELECT version() AS version",
    "tables": """
        SELECT tablename AS table_name
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """,
    "row_counts": """
        SELECT relname AS table_name, n_live_tup AS live_rows, n_dead_tup AS dead_rows
        FROM pg_stat_user_tables
        ORDER BY relname
    """,
    "db_size": "SELECT pg_size_pretty(pg_database_size(current_database())) AS size",
    "active_connections": """
        SELECT count(*) AS n
        FROM pg_stat_activity
        WHERE datname = current_database() AND state = 'active'
    """,
    "total_connections": """
        SELECT count(*) AS n
        FROM pg_stat_activity
        WHERE datname = current_database()
    """,
    "last_analyze": """
        SELECT relname AS table_name, last_analyze, last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY relname
    """,
    "orphan_reviews": """
        SELECT count(*) AS n
        FROM reviews r
        LEFT JOIN books b ON b.id = r.book_id
        WHERE b.id IS NULL
    """,
    "recent_registrations": """
        SELECT count(*) AS n
        FROM users
        WHERE created_at >= to_char(now() - interval '7 days', 'YYYY-MM-DD"T"HH24:MI:SS')
    """,
    "recent_activity": """
        SELECT count(*) AS n
        FROM rayos_transactions
        WHERE created_at >= to_char(now() - interval '7 days', 'YYYY-MM-DD"T"HH24:MI:SS')
    """,

    # ── A. ESQUEMA ──────────────────────────────────────────────────────────
    "critical_columns": """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND (table_name, column_name) IN (
            ('users','id'),('users','email'),('users','hashed_password'),('users','role'),
            ('books','id'),('books','title'),('books','author_name'),('books','content'),
            ('books','page_count'),('books','published'),('books','created_at'),
            ('book_pages','id'),('book_pages','book_id'),('book_pages','page_number'),('book_pages','content'),
            ('chapters','id'),('chapters','book_id'),('chapters','title'),('chapters','start_page'),
            ('reviews','id'),('reviews','book_id'),('reviews','user_id')
          )
        ORDER BY table_name, column_name
    """,
    "constraints_fks": """
        SELECT conrelid::regclass::text AS table_name,
               conname,
               contype,
               pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace
        ORDER BY conrelid::regclass::text, contype, conname
    """,

    # ── B. LIBROS ───────────────────────────────────────────────────────────
    "books_page_count_null_or_zero": """
        SELECT id, title, page_count, published
        FROM books
        WHERE page_count IS NULL OR page_count <= 0
        ORDER BY id
    """,
    "books_without_pages": """
        SELECT b.id, b.title, b.page_count
        FROM books b
        LEFT JOIN book_pages p ON p.book_id = b.id
        WHERE p.id IS NULL
        ORDER BY b.id
    """,
    "books_published_status": """
        SELECT published, count(*) AS n
        FROM books
        GROUP BY published
        ORDER BY published
    """,

    # ── C. PAGINACIÓN ───────────────────────────────────────────────────────
    "page_duplicates_book_page": """
        SELECT book_id, page_number, count(*) AS n
        FROM book_pages
        GROUP BY book_id, page_number
        HAVING count(*) > 1
        ORDER BY book_id, page_number
    """,
    "empty_pages": """
        SELECT id, book_id, page_number
        FROM book_pages
        WHERE content IS NULL OR length(trim(content)) = 0
        ORDER BY book_id, page_number
    """,
    "page_numbering_gaps": """
        WITH ranges AS (
            SELECT book_id,
                   min(page_number) AS min_page,
                   max(page_number) AS max_page,
                   count(DISTINCT page_number) AS distinct_pages
            FROM book_pages
            GROUP BY book_id
        )
        SELECT book_id, min_page, max_page, distinct_pages,
               (max_page - min_page + 1) - distinct_pages AS gap_count
        FROM ranges
        WHERE (max_page - min_page + 1) - distinct_pages > 0
        ORDER BY gap_count DESC
    """,
    "page_count_vs_max_page": """
        SELECT b.id, b.title, b.page_count, p.max_page
        FROM books b
        LEFT JOIN (SELECT book_id, max(page_number) AS max_page
                   FROM book_pages GROUP BY book_id) p ON p.book_id = b.id
        WHERE b.page_count IS DISTINCT FROM p.max_page
        ORDER BY b.id
    """,

    # ── D. CONTENIDO ────────────────────────────────────────────────────────
    "books_suspicious_content": """
        SELECT id, title
        FROM books
        WHERE content ~* '(lorem ipsum|placeholder|pendiente|todo:|fixme|qwerty|asdasd|test content)'
        ORDER BY id
    """,
    "repeated_paragraphs": """
        WITH pars AS (
            SELECT b.id AS book_id, b.title,
                   trim(regexp_split_to_table(b.content, '\\n')) AS par
            FROM books b
            WHERE b.content IS NOT NULL
        )
        SELECT book_id, title, par, count(*) AS n
        FROM pars
        WHERE par <> ''
        GROUP BY book_id, title, par
        HAVING count(*) > 1
        ORDER BY n DESC
    """,
    "identical_book_content": """
        SELECT content, count(*) AS n,
               array_agg(id ORDER BY id) AS ids,
               array_agg(title ORDER BY id) AS titles
        FROM books
        GROUP BY content
        HAVING count(*) > 1
        ORDER BY n DESC
    """,
    "identical_pages_across_books": """
        SELECT content, count(*) AS n,
               array_agg(id ORDER BY id) AS page_ids,
               array_agg(book_id ORDER BY id) AS book_ids
        FROM book_pages
        GROUP BY content
        HAVING count(*) > 1 AND count(DISTINCT book_id) > 1
        ORDER BY n DESC
        LIMIT 100
    """,
    "books_empty_or_placeholder": """
        SELECT id, title
        FROM books
        WHERE content IS NULL OR length(trim(content)) = 0
           OR content ~* '(placeholder|TBD|pendiente de agregar)'
        ORDER BY id
    """,

    # ── E. CAPÍTULOS ────────────────────────────────────────────────────────
    "duplicate_chapters_in_book": """
        SELECT book_id, title, count(*) AS n
        FROM chapters
        GROUP BY book_id, title
        HAVING count(*) > 1
        ORDER BY book_id
    """,
    "duplicate_chapter_start_pages": """
        SELECT book_id, start_page, count(*) AS n
        FROM chapters
        GROUP BY book_id, start_page
        HAVING count(*) > 1
        ORDER BY book_id, start_page
    """,
    "chapters_out_of_range": """
        SELECT c.id, c.book_id, c.title, c.start_page, p.max_page
        FROM chapters c
        LEFT JOIN (SELECT book_id, max(page_number) AS max_page
                   FROM book_pages GROUP BY book_id) p ON p.book_id = c.book_id
        WHERE c.start_page < 1
           OR p.max_page IS NULL
           OR c.start_page > p.max_page
        ORDER BY c.book_id, c.start_page
    """,
    "chapters_summary_per_book": """
        SELECT book_id, count(*) AS n,
               array_agg(title ORDER BY start_page) AS titles
        FROM chapters
        GROUP BY book_id
        ORDER BY book_id
    """,
    "chapter_titles_shared_across_books": """
        SELECT title, count(DISTINCT book_id) AS n_books,
               array_agg(DISTINCT book_id) AS book_ids
        FROM chapters
        GROUP BY title
        HAVING count(DISTINCT book_id) > 1
        ORDER BY n_books DESC
    """,

    # ── F. DUPLICADOS DEL CATÁLOGO ──────────────────────────────────────────
    "duplicate_title_author": """
        SELECT title, author_name, count(*) AS n,
               array_agg(id ORDER BY id) AS ids
        FROM books
        GROUP BY title, author_name
        HAVING count(*) > 1
        ORDER BY n DESC
    """,
    "el_principito_results": """
        SELECT id, title, author_name, page_count, published,
               length(content) AS content_length
        FROM books
        WHERE title ILIKE '%principito%'
        ORDER BY id
    """,
    "pg_trgm_available": """
        SELECT count(*) AS n FROM pg_extension WHERE extname = 'pg_trgm'
    """,
    "near_identical_content": """
        SELECT a.id AS id_a, a.title AS title_a,
               b.id AS id_b, b.title AS title_b
        FROM books a
        JOIN books b ON a.id < b.id
          AND regexp_replace(a.content, '\\s+', '', 'g') =
              regexp_replace(b.content, '\\s+', '', 'g')
        ORDER BY a.id
    """,
}

def main():
    try:
        conn = psycopg2.connect(
            resolve_url(DATABASE_URL),
            cursor_factory=psycopg2.extras.RealDictCursor,
            options="-c default_transaction_read_only=on",
        )
        conn.set_session(readonly=True, autocommit=False)
        cursor = conn.cursor()

        result = {}
        for name, query in DIAG_QUERIES.items():
            cursor.execute(query)
            rows = cursor.fetchall()
            result[name] = [dict(r) for r in rows]

        cursor.close()
        conn.rollback()
        conn.close()

        print(json.dumps({"ok": True, "diagnosis": result}, ensure_ascii=False, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()