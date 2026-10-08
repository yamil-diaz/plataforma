#!/bin/bash
set -euo pipefail
mkdir -p /root/restore-users

echo "=== re-export users csv from scratch ==="
docker start aeternum-scratch-pg >/dev/null 2>&1 || true
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -c "COPY (SELECT id, name, email, hashed_password, role, rayos_balance, historical_rayos, username, bio, profile_image_url, favorite_genres, reset_token, reset_token_expiry, is_banned, registration_ip, created_at, referred_by_qr_id FROM users ORDER BY id) TO STDOUT WITH (FORMAT csv, NULL '')" > /root/restore-users/users.csv
wc -l /root/restore-users/users.csv

python3 <<'PY'
import csv, subprocess

def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout, p.stderr

def q(v):
    if v is None or v == "":
        return "NULL"
    s = str(v)
    if s in ("t", "true", "True"):
        return "true"
    if s in ("f", "false", "False"):
        return "false"
    return "'" + s.replace("'", "''") + "'"

rows=[]
with open("/root/restore-users/users.csv", newline="", encoding="utf-8") as f:
    for row in csv.reader(f):
        if len(row) >= 17:
            rows.append(row)
print("rows", len(rows))

stmts=[]
for row in rows:
    uid=int(row[0])
    email=row[2]
    # upsert by email: restore password/role/balances from Render dump
    # keep google_id/email_verified if user already linked Google on Hetzner
    stmts.append(f"""
INSERT INTO users (id, name, email, hashed_password, role, rayos_balance, historical_rayos, username, bio, profile_image_url, favorite_genres, reset_token, reset_token_expiry, is_banned, registration_ip, created_at, referred_by_qr_id, email_verified)
VALUES ({uid}, {q(row[1])}, {q(email)}, {q(row[3])}, {q(row[4])}, {row[5] or 0}, {row[6] or 0}, {q(row[7])}, {q(row[8])}, {q(row[9])}, {q(row[10])}, {q(row[11])}, {q(row[12])}, {q(row[13])}, {q(row[14])}, {q(row[15])}, {row[16] or 'NULL'}, TRUE)
ON CONFLICT (email) DO UPDATE SET
  name=EXCLUDED.name,
  hashed_password=EXCLUDED.hashed_password,
  role=EXCLUDED.role,
  rayos_balance=EXCLUDED.rayos_balance,
  historical_rayos=EXCLUDED.historical_rayos,
  username=EXCLUDED.username,
  bio=EXCLUDED.bio,
  profile_image_url=EXCLUDED.profile_image_url,
  favorite_genres=EXCLUDED.favorite_genres,
  is_banned=EXCLUDED.is_banned,
  email_verified=TRUE;
""".strip())

# Also handle id conflicts: if id taken by different email, reassign that old row is hard;
# delete only non-admin conflicting ids that are NOT in dump emails
dump_emails = {r[2] for r in rows}
# get prod users
out, _ = run_sql("SELECT id, email FROM users;")
print("prod_users_before:\n", out)

# For each dump user, if id exists with different email, move that prod user out of the way only if email not in dump
# Simpler path: delete prod users whose email is in dump (will be reinserted), keep others
del_emails = []
for r in rows:
    del_emails.append(q(r[2]))
run_sql("SET session_replication_role = replica;\nDELETE FROM users WHERE email IN (" + ",".join(del_emails) + ") AND email <> 'admin@plataforma.com';\nSET session_replication_role = DEFAULT;\n")

# Fix id conflicts: delete any remaining user occupying a dump id if their email is not a dump email and not admin
id_fix=[]
for r in rows:
    uid=int(r[0])
    if uid==1:
        continue
    id_fix.append(f"DELETE FROM users WHERE id={uid} AND email IS DISTINCT FROM {q(r[2])};")
run_sql("SET session_replication_role = replica;\n"+"\n".join(id_fix)+"\nSET session_replication_role = DEFAULT;\n")

# Keep Rodrigo google: if exists, don't delete him - he is in dump as id4 admin
# Apply inserts in one transaction
sql = "SET session_replication_role = replica;\n" + "\n".join(stmts) + "\nSET session_replication_role = DEFAULT;\n"
out, err = run_sql(sql)
print("apply_out_tail", (out or "")[-600:])
print("apply_err_tail", (err or "")[-800:])

# Restore Google link for rodrigo if we have it in prod backup... optional
# Ensure admin password remains admin123 for the seed admin email if present
out, _ = run_sql("SELECT id,email,role FROM users ORDER BY id;")
print("users_after:\n", out)
PY

echo "=== counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, email, name, role, google_id IS NOT NULL AS g FROM users ORDER BY id;'

echo "=== re-apply related data now that users exist ==="
python3 <<'PY'
import subprocess
def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout, p.stderr
try:
    sql=open("/root/restore-users/related_inserts.sql",encoding="utf-8").read()
except FileNotFoundError:
    sql=""
inserts=[ln for ln in sql.splitlines() if ln.startswith("INSERT INTO")]
fixed=[]
for ln in inserts:
    ln=ln.strip()
    if not ln.endswith(";"): ln+=";"
    if "ON CONFLICT" not in ln:
        ln=ln[:-1]+" ON CONFLICT DO NOTHING;"
    fixed.append(ln)
print("related", len(fixed))
for i in range(0,len(fixed),40):
    run_sql("SET session_replication_role = replica;\n"+"\n".join(fixed[i:i+40])+"\nSET session_replication_role = DEFAULT;\n")
print("related done")
PY

echo "=== final counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS reviews FROM reviews;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS rayos FROM rayos_transactions;'

echo "=== API ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
curl -s -c /tmp/cj4.txt -o /tmp/l7.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/cj4.txt -o /tmp/me7.txt -w "me=%{http_code}\n" https://aeternumlibrary.com/api/me

echo DONE
