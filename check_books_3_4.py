import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='plataforma_dev',
    user='postgres',
    password='yamilpro002'
)
cursor = conn.cursor()

# Check IDs 3 and 4
cursor.execute('''
    SELECT id, title, author_name, page_count, published, uploader_id, LENGTH(content) as content_len
    FROM books
    WHERE id IN (3, 4)
    ORDER BY id
''')
results = cursor.fetchall()
print('Books to delete:')
for row in results:
    print(f'  ID {row[0]}: "{row[1]}" by {row[2]}, page_count={row[3]}, published={row[4]}, uploader_id={row[5]}, content_len={row[6]}')

# Check dependencies
for book_id in [3, 4]:
    cursor.execute('SELECT COUNT(*) FROM book_pages WHERE book_id = %s', (book_id,))
    bp = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM chapters WHERE book_id = %s', (book_id,))
    ch = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM reading_progress WHERE book_id = %s', (book_id,))
    rp = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM reading_sessions WHERE book_id = %s', (book_id,))
    rs = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM reviews WHERE book_id = %s', (book_id,))
    rv = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM book_interactions WHERE book_id = %s', (book_id,))
    bi = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM reading_daily_pages WHERE book_id = %s', (book_id,))
    rdp = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM featured_books WHERE book_id = %s', (book_id,))
    fb = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM forum_posts WHERE book_id = %s', (book_id,))
    fp = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM competitions WHERE book_id = %s', (book_id,))
    cp = cursor.fetchone()[0]
    
    print(f'\nID {book_id} dependencies:')
    print(f'  book_pages: {bp}')
    print(f'  chapters: {ch}')
    print(f'  reading_progress: {rp}')
    print(f'  reading_sessions: {rs}')
    print(f'  reviews: {rv}')
    print(f'  book_interactions: {bi}')
    print(f'  reading_daily_pages: {rdp}')
    print(f'  featured_books: {fb}')
    print(f'  forum_posts: {fp}')
    print(f'  competitions: {cp}')

conn.close()