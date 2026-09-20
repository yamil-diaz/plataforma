import psycopg2
import psycopg2.extras

conn = psycopg2.connect(
    host='localhost',
    database='plataforma_dev',
    user='postgres',
    password='postgres',
    port=5432
)
print('Connected successfully')
cursor = conn.cursor()
cursor.execute('SELECT 1 as test')
print(cursor.fetchone())
conn.close()