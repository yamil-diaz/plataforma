import os, psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL').replace("postgres://", "postgresql://", 1))
cur = conn.cursor()
cur.execute("UPDATE users SET role = 'admin' WHERE name = 'osito' RETURNING id, name, role")
print(cur.fetchone())
conn.commit()
conn.close()
