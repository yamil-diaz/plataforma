#!/bin/bash
cd /root/plataforma/docker
echo "=== app logs earnings ==="
docker compose logs app --tail 40 2>&1 | grep -iE 'earnings|withdraw|Traceback|Error|psycopg|column' | tail -25

echo "=== try earnings via python in container ==="
docker exec -w /app docker-app-1 python - <<'PY'
import os, traceback
import psycopg2
url=os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url=url.replace("postgres://","postgresql://",1)
conn=psycopg2.connect(url)
cur=conn.cursor()
try:
    cur.execute("""
        SELECT
            COALESCE(SUM(oi.subtotal), 0) AS total_sales,
            COUNT(DISTINCT o.id) AS orders_count,
            COUNT(oi.id) AS items_count
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN books b ON b.id = oi.book_id
        WHERE b.uploader_id = 1 AND o.payment_status = 'approved'
    """)
    print("summary", cur.fetchone())
    cur.execute("SELECT count(*) FROM author_withdrawals")
    print("withdrawals", cur.fetchone())
    cur.execute("SELECT id FROM order_items LIMIT 3")
    print("order_items sample", cur.fetchall())
    cur.execute("SELECT id, payment_status FROM orders LIMIT 5")
    print("orders sample", cur.fetchall())
except Exception:
    traceback.print_exc()
conn.close()
PY
echo DONE
