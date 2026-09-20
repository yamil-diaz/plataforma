import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

# Compare page_count vs COUNT(book_pages) for all published books
cursor.execute('''
    SELECT b.id, b.title, b.page_count, 
           COALESCE((SELECT COUNT(*) FROM book_pages WHERE book_id = b.id), 0) as bp_count,
           COALESCE((SELECT MAX(page_number) FROM book_pages WHERE book_id = b.id), 0) as max_page,
           LENGTH(b.content) as content_len
    FROM books b
    WHERE b.published = 1
    ORDER BY b.id
''')

results = cursor.fetchall()
print('ID | Title | page_count | COUNT(book_pages) | MAX(page_number) | content_len')
print('---|-------|------------|-------------------|------------------|------------')
for row in results:
    print(f'{row[0]} | {row[1][:30]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}')

conn.close()