#!/bin/bash
set -euo pipefail

echo "=== 0) backup production db ==="
docker exec docker-db-1 pg_dump -U aeternum -d aeternum -Fc -f /tmp/prod_before_users.dump
docker cp docker-db-1:/tmp/prod_before_users.dump /root/prod_before_users.dump
ls -lh /root/prod_before_users.dump

echo "=== 1) schema compare users ==="
echo "--- PROD users cols ---"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position;"
echo "--- SCRATCH users cols ---"
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position;"

echo "=== 2) export users from scratch ==="
docker exec aeternum-scratch-pg pg_dump -U postgres -d aeternum --data-only --column-inserts -t users > /root/restore-users/users_inserts.sql
wc -l /root/restore-users/users_inserts.sql
head -5 /root/restore-users/users_inserts.sql

echo "=== 3) export related user data ==="
for t in login_attempts password_resets rayos_transactions reviews reading_progress reading_sessions reading_daily_pages book_interactions user_badges user_addresses orders order_items digital_entitlements physical_orders ai_conversations ai_messages notifications forum_posts forum_replies forum_likes forum_bookmarks forum_follows qr_codes qr_visits followers course_progress; do
  docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c "SELECT to_regclass('public.$t');" | grep -q null && continue
  docker exec aeternum-scratch-pg pg_dump -U postgres -d aeternum --data-only --column-inserts -t "$t" >> /root/restore-users/related_inserts.sql 2>/dev/null || true
done
wc -l /root/restore-users/related_inserts.sql || echo no_related

echo "=== 4) apply users to production (keep admin id1, insert others by email) ==="
# Disable FK checks during load
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SET session_replication_role = replica;'

# Truncate test users that are not in dump? Keep admin@ id1, insert rest
# Strategy: insert all dump users with ON CONFLICT DO NOTHING on email; also try id conflict
python3 - <<'PY'
import subprocess, re, os

def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout + p.stderr

# Load users inserts but skip header lines that are COPY/SET
sql = open("/root/restore-users/users_inserts.sql",encoding="utf-8").read()
# keep only INSERT lines
inserts = [ln for ln in sql.splitlines() if ln.startswith("INSERT INTO users")]
print("insert_lines", len(inserts))
# rewrite: ON CONFLICT (email) DO NOTHING; also handle id conflict by deleting conflicting non-admin emails first
# First, collect emails from dump inserts
emails=set()
for ln in inserts:
    emails.update(re.findall(r"'([^']*@[^']*)'", ln))
print("emails", len(emails))

# Remove prod users that conflict on id but are not admin and not same email as dump
# Simpler: for each insert, if id exists with different email and not admin, delete that id first
# Extract id and email from INSERT INTO users (id, ...) VALUES (N, ...
ids_emails=[]
for ln in inserts:
    m=re.search(r"INSERT INTO users \([^)]*\) VALUES \((.*)\);", ln)
    if not m: continue
    # rough parse first two string-ish fields is hard; use regex for email
    em=re.search(r"'([^']+@[^']+)'", ln)
    idm=re.search(r"\((\d+),", ln)
    if em and idm:
        ids_emails.append((int(idm.group(1)), em.group(1)))
print("parsed", len(ids_emails))

cleanup=[]
for uid, em in ids_emails:
    if uid==1:
        continue
    cleanup.append(f"DELETE FROM users WHERE id={uid} AND email IS DISTINCT FROM '{em}';")
    cleanup.append(f"DELETE FROM users WHERE email='{em}' AND id<>{uid};")
run_sql("\n".join(cleanup)+"\nSET session_replication_role = replica;\n")
print("cleanup done")

# Apply inserts with ON CONFLICT DO NOTHING on email; for id conflicts use DO NOTHING too
out=[]
for ln in inserts:
    if not ln.strip().endswith(";"):
        ln=ln.strip()+";"
    if "ON CONFLICT" not in ln:
        ln=ln[:-1]+" ON CONFLICT (email) DO NOTHING;"
    out.append(ln)
res=run_sql("\n".join(out)+"\n")
print(res[-500:] if res else "no out")

# re-enable
run_sql("SET session_replication_role = DEFAULT;\n")
print("users applied")
PY

echo "=== 5) apply related data ==="
python3 - <<'PY'
import subprocess
def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout + p.stderr

run_sql("SET session_replication_role = replica;\n")
try:
    sql=open("/root/restore-users/related_inserts.sql",encoding="utf-8").read()
except FileNotFoundError:
    sql=""
inserts=[ln for ln in sql.splitlines() if ln.startswith("INSERT INTO")]
print("related_inserts", len(inserts))
# add ON CONFLICT DO NOTHING if missing
fixed=[]
for ln in inserts:
    ln=ln.strip()
    if not ln.endswith(";"): ln+=";"
    if "ON CONFLICT" not in ln:
        ln=ln[:-1]+" ON CONFLICT DO NOTHING;"
    fixed.append(ln)
# apply in chunks
for i in range(0,len(fixed),50):
    chunk= "\n".join(fixed[i:i+50])
    run_sql("SET session_replication_role = replica;\n"+chunk+"\n")
run_sql("SET session_replication_role = DEFAULT;\n")
print("related applied")
PY

echo "=== 6) counts after merge ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS reviews FROM reviews;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS rayos FROM rayos_transactions;'
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, email, name, role FROM users ORDER BY id LIMIT 15;'

echo "=== 7) cleanup scratch ==="
docker rm -f aeternum-scratch-pg || true

echo "=== 8) verify API ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
curl -s -c /tmp/cj2.txt -o /tmp/l5.txt -w "admin_login=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/cj2.txt -o /tmp/me5.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me

echo DONE
