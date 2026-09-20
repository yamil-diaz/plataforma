import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set environment
os.environ['DATABASE_URL'] = 'postgresql://postgres:yamilpro002@localhost:5432/plataforma_dev'
os.environ['STORAGE_DIR'] = 'backend/storage'

# Use the database module
from database import get_db

try:
    db = get_db()
    cursor = db.cursor()
    
    # Check total books
    cursor.execute("SELECT count(*) as total FROM books")
    total = cursor.fetchone()['total']
    print(f"Total books: {total}")
    
    # Check ID 128
    cursor.execute("SELECT id, title, author_name, page_count, pdf_path FROM books WHERE id = 128")
    row = cursor.fetchone()
    print(f"ID 128: {row}")
    
    # Check ID 18
    cursor.execute("SELECT id, title, author_name, page_count, pdf_path FROM books WHERE id = 18")
    row = cursor.fetchone()
    print(f"ID 18: {row}")
    
    # Check for duplicates of El Principito
    cursor.execute("""
        SELECT id, title, author_name, page_count, pdf_path 
        FROM books 
        WHERE title = 'El Principito' AND author_name = 'Antoine de Saint-Exupéry'
        ORDER BY id
    """)
    rows = cursor.fetchall()
    print("El Principito duplicates:")
    for r in rows:
        print(f"  {r}")
    
    # Check books with page_count = 0 or NULL
    cursor.execute("""
        SELECT id, title, author_name, page_count, 
               (SELECT count(*) FROM book_pages WHERE book_id = books.id) as n_pages
        FROM books 
        WHERE page_count IS NULL OR page_count = 0
        ORDER BY id
    """)
    rows = cursor.fetchall()
    print(f"\nBooks with page_count 0 or NULL ({len(rows)}):")
    for r in rows[:20]:
        print(f"  ID={r['id']} Title='{r['title']}' page_count={r['page_count']} book_pages={r['n_pages']}")
    if len(rows) > 20:
        print(f"  ... and {len(rows) - 20} more")
    
    # Check books with page_count > 0 but no book_pages
    cursor.execute("""
        SELECT b.id, b.title, b.page_count,
               (SELECT count(*) FROM book_pages WHERE book_id = b.id) as n_pages
        FROM books b
        WHERE b.page_count > 0 
        AND NOT EXISTS (SELECT 1 FROM book_pages WHERE book_id = b.id)
        ORDER BY b.id
    """)
    rows = cursor.fetchall()
    print(f"\nBooks with page_count > 0 but NO book_pages ({len(rows)}):")
    for r in rows:
        print(f"  ID={r['id']} Title='{r['title']}' page_count={r['page_count']} book_pages={r['n_pages']}")
    
    # Check books with book_pages but page_count = 0
    cursor.execute("""
        SELECT b.id, b.title, b.page_count,
               (SELECT count(*) FROM book_pages WHERE book_id = b.id) as n_pages
        FROM books b
        WHERE b.page_count = 0 
        AND EXISTS (SELECT 1 FROM book_pages WHERE book_id = b.id)
        ORDER BY b.id
    """)
    rows = cursor.fetchall()
    print(f"\nBooks with page_count = 0 but HAVE book_pages ({len(rows)}):")
    for r in rows:
        print(f"  ID={r['id']} Title='{r['title']}' page_count={r['page_count']} book_pages={r['n_pages']}")
    
    # Check all books with their page stats
    cursor.execute("""
        SELECT b.id, b.title, b.author_name, b.page_count, b.published,
               (SELECT count(*) FROM book_pages WHERE book_id = b.id) as n_pages,
               (SELECT count(*) FROM chapters WHERE book_id = b.id) as n_chapters
        FROM books b
        WHERE b.published = 1
        ORDER BY b.id
    """)
    rows = cursor.fetchall()
    print(f"\nAll published books ({len(rows)}):")
    for r in rows:
        print(f"  ID={r['id']} '{r['title']}' author={r['author_name']} page_count={r['page_count']} book_pages={r['n_pages']} chapters={r['n_chapters']} published={r['published']}")
    
    db.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()