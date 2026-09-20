import psycopg2
import hashlib

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='plataforma_dev',
    user='postgres',
    password='yamilpro002'
)
cursor = conn.cursor()

# Get all books with their details
cursor.execute('''
    SELECT b.id, b.title, b.author_name, b.page_count, LENGTH(b.content) as content_len
    FROM books b
    WHERE b.published = 1
    ORDER BY b.id
''')
books = cursor.fetchall()

print("=" * 80)
print("LIBROS PUBLICADOS")
print("=" * 80)
for book in books:
    print(f"ID: {book[0]}, Title: {book[1]}, Author: {book[2]}, page_count: {book[3]}, content_len: {book[4]}")

print("\n" + "=" * 80)
print("CONTENIDO DE book_pages POR LIBRO")
print("=" * 80)

for book in books:
    book_id = book[0]
    cursor.execute('''
        SELECT page_number, content, chapter_id
        FROM book_pages
        WHERE book_id = %s
        ORDER BY page_number
    ''', (book_id,))
    pages = cursor.fetchall()
    
    print(f"\n--- Libro ID {book_id}: {book[1]} ---")
    print(f"  page_count (books): {book[3]}, COUNT(book_pages): {len(pages)}, content_len: {book[4]}")
    
    if not pages:
        print("  (sin páginas en book_pages)")
        continue
    
    for page in pages:
        page_num = page[0]
        content = page[1]
        chapter_id = page[2]
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        preview = content[:100].replace('\n', ' ')
        print(f"  Page {page_num}: len={len(content)}, hash={content_hash}, chapter_id={chapter_id}")
        print(f"    Preview: {preview}...")

conn.close()