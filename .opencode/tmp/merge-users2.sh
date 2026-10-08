#!/bin/bash
set -euo pipefail
mkdir -p /root/restore-users

echo "=== 0) backup production db ==="
docker exec docker-db-1 pg_dump -U aeternum -d aeternum -Fc -f /tmp/prod_before_users.dump
docker cp docker-db-1:/tmp/prod_before_users.dump /root/prod_before_users.dump
ls -lh /root/prod_before_users.dump

echo "=== export users from scratch ==="
docker exec aeternum-scratch-pg pg_dump -U postgres -d aeternum --data-only --column-inserts -t users > /root/restore-users/users_inserts.sql
wc -l /root/restore-users/users_inserts.sql
head -3 /root/restore-users/users_inserts.sql

echo "=== export related ==="
rm -f /root/restore-users/related_inserts.sql
for t in login_attempts password_resets rayos_transactions reviews reading_progress reading_sessions reading_daily_pages book_interactions user_badges user_addresses orders order_items digital_entitlements physical_orders ai_conversations ai_messages notifications forum_posts forum_replies forum_likes forum_bookmarks forum_follows qr_codes qr_visits followers course_progress; do
  exists=$(docker exec aeternum-scratch-pg psql -U postgres -d aeternum -tAc "SELECT to_regclass('public.$t') IS NOT NULL")
  if [ "$exists" = "t" ]; then
    docker exec aeternum-scratch-pg pg_dump -U postgres -d aeternum --data-only --column-inserts -t "$t" >> /root/restore-users/related_inserts.sql 2>/dev/null || true
    echo "exported $t"
  fi
done
wc -l /root/restore-users/related_inserts.sql || true

echo "=== merge users ==="
python3 <<'PY'
import subprocess, re

def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout + p.stderr

sql = open("/root/restore-users/users_inserts.sql", encoding="utf-8").read()
inserts = [ln for ln in sql.splitlines() if ln.startswith("INSERT INTO users")]
print("insert_lines", len(inserts))

ids_emails=[]
for ln in inserts:
    em=re.search(r"'([^']+@[^']+)'", ln)
    idm=re.search(r"\((\d+),", ln)
    if em and idm:
        ids_emails.append((int(idm.group(1)), em.group(1)))
print("parsed", len(ids_emails))

cleanup=[]
for uid, em in ids_emails:
    if uid==1:
        continue
    em_safe=em.replace("'","''")
    cleanup.append(f"DELETE FROM users WHERE id={uid} AND email IS DISTINCT FROM '{em_safe}';")
    cleanup.append(f"DELETE FROM users WHERE email='{em_safe}' AND id<>{uid};")
run_sql("SET session_replication_role = replica;\n"+"\n".join(cleanup)+"\n")
print("cleanup done")

out=[]
for ln in inserts:
    ln=ln.strip()
    if not ln.endswith(";"):
        ln+=";"
    if "ON CONFLICT" not in ln:
        ln=ln[:-1]+" ON CONFLICT (email) DO NOTHING;"
    out.append(ln)
res=run_sql("SET session_replication_role = replica;\n"+"\n".join(out)+"\n")
print("users_apply_tail:", (res or "")[-400:])
run_sql("SET session_replication_role = DEFAULT;\n")
print("users applied")
PY

echo "=== merge related ==="
python3 <<'PY'
import subprocess
def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout + p.stderr

try:
    sql=open("/root/restore-users/related_inserts.sql",encoding="utf-8").read()
except FileNotFoundError:
    sql=""
inserts=[ln for ln in sql.splitlines() if ln.startswith("INSERT INTO")]
print("related_inserts", len(inserts))
fixed=[]
for ln in inserts:
    ln=ln.strip()
    if not ln.endswith(";"): ln+=";"
    if "ON CONFLICT" not in ln:
        ln=ln[:-1]+" ON CONFLICT DO NOTHING;"
    fixed.append(ln)
run_sql("SET session_replication_role = replica;\n")
for i in range(0,len(fixed),40):
    run_sql("SET session_replication_role = replica;\n"+"\n".join(fixed[i:i+40])+"\n")
run_sql("SET session_replication_role = DEFAULT;\n")
print("related applied")
PY

echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS reviews FROM reviews;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS rayos FROM rayos_transactions;'
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, email, name, role FROM users ORDER BY id LIMIT 12;'

echo "=== verify API + admin login ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
curl -s -c /tmp/cj2.txt -o /tmp/l5.txt -w "admin_login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/cj2.txt -o /tmp/me5.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me

echo DONE
