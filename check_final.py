import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='plataforma_dev',
    user='postgres',
    password='yamilpro002'
)
cursor = conn.cursor()

# Check for books with COUNT(book_pages) = 1 but long content
cursor.execute('''
    SELECT b.id, b.title, b.page_count, 
           COALESCE((SELECT COUNT(*) FROM book_pages WHERE book_id = b.id), 0) as bp_count,
           COALESCE((SELECT MAX(page_number) FROM book_pages WHERE book_id = b.id), 0) as max_page,
           LENGTH(b.content) as content_len
    FROM books b
    ORDER BY b.id
''')
results = cursor.fetchall()
print('Books with page_count vs COUNT(book_pages) analysis:')
for row in results:
    if row[3] == 1 and row[5] > 2000:
        print(f'  WARNING: ID {row[0]} "{row[1]}" has COUNT(book_pages)=1 but content_len={row[5]}')
    elif row[3] == 0:
        print(f'  ZERO PAGES: ID {row[0]} "{row[1]}" page_count={row[2]}, COUNT(book_pages)={row[3]}, content_len={row[5]}')
    else:
        print(f'  OK: ID {row[0]} "{row[1]}" page_count={row[2]}, COUNT(book_pages)={row[3]}, content_len={row[5]}')

conn.close()