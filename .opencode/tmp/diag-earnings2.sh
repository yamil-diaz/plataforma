#!/bin/bash
cd /root/plataforma/docker
echo "=== last 80 app lines ==="
docker compose logs app --tail 80 2>&1 | tail -50

echo "=== python query test ==="
docker exec docker-app-1 python3 -c '
import os, traceback, psycopg2
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
try:
    cur.execute("SELECT count(*) FROM order_items")
    print("order_items", cur.fetchone())
    cur.execute("SELECT id, payment_status, total FROM orders ORDER BY id DESC LIMIT 5")
    print("orders", cur.fetchall())
    cur.execute("SELECT id, uploader_id, title FROM books WHERE uploader_id IS NOT NULL LIMIT 5")
    print("uploaded_books", cur.fetchall())
    cur.execute("""SELECT COALESCE(SUM(oi.subtotal),0), COUNT(DISTINCT o.id), COUNT(oi.id)
        FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN books b ON b.id=oi.book_id
        WHERE b.uploader_id=1 AND o.payment_status=%s""", ("approved",))
    print("earnings_admin", cur.fetchone())
    cur.execute("SELECT * FROM author_withdrawals LIMIT 3")
    print("wd", cur.fetchall())
except Exception:
    traceback.print_exc()
finally:
    conn.close()
'
echo DONE
