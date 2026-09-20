import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='plataforma_dev',
    user='postgres',
    password='yamilpro002'
)
cursor = conn.cursor()

affected_ids = [133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170]

# Add IDs 82 and 145 from suspicious content
all_ids = affected_ids + [82, 145]

placeholders = ','.join(['%s'] * len(all_ids))
query = f'''
    SELECT 
        b.id, b.title, b.author_name, b.page_count, b.published, 
        b.uploader_id, b.pdf_path,
        LENGTH(b.content) as content_len,
        b.content
    FROM books b
    WHERE b.id IN ({placeholders})
    ORDER BY b.id
'''

cursor.execute(query, tuple(all_ids))
books = cursor.fetchall()

print('BOOKS WITH PLACEHOLDER/SUSPICIOUS CONTENT:')
for b in books:
    content_preview = b[9][:80].replace('\n', ' ') if b[9] else 'NULL'
    is_placeholder = 'Contenido de texto no disponible' in (b[9] or '')
    print(f'ID {b[0]}: {b[1]} | Author: {b[2]} | page_count: {b[3]} | published: {b[4]} | pdf: {b[6]} | content_len: {b[7]} | placeholder: {is_placeholder} | content: {content_preview}...')

# Now get book_pages for these books
print()
print('BOOK_PAGES FOR THESE BOOKS:')
cursor.execute(f'''
    SELECT bp.book_id, bp.page_number, bp.content, bp.chapter_id
    FROM book_pages bp
    WHERE bp.book_id IN ({placeholders})
    ORDER BY bp.book_id, bp.page_number
''', tuple(all_ids))
pages = cursor.fetchall()

current_book = None
for p in pages:
    if p[0] != current_book:
        current_book = p[0]
        print(f'\n--- Book {current_book} ---')
    content_preview = p[2][:80].replace('\n', ' ') if p[2] else 'NULL'
    is_placeholder = 'Contenido de texto no disponible' in (p[2] or '')
    print(f'  Page {p[1]}: len={len(p[2]) if p[2] else 0}, placeholder={is_placeholder}, chapter_id={p[3]} | {content_preview}...')

conn.close()