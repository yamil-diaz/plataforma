import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='plataforma_dev',
    user='postgres',
    password='yamilpro002'
)
cursor = conn.cursor()

cursor.execute('''
    SELECT b.id, b.title, b.page_count, 
           COALESCE((SELECT COUNT(*) FROM book_pages WHERE book_id = b.id), 0) as bp_count,
           COALESCE((SELECT MAX(page_number) FROM book_pages WHERE book_id = b.id), 0) as max_page
    FROM books b
    WHERE b.published = 1
    ORDER BY b.id
''')
results = cursor.fetchall()
print('ID | Title | page_count (books) | COUNT(book_pages)')
print('---|-------|-------------------|-------------------')
for row in results:
    match = 'OK' if row[2] == row[3] else 'MISMATCH'
    print(f'{row[0]} | {row[1][:30]} | {row[2]} | {row[3]} {match}')

conn.close()