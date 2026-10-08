#!/bin/bash
set -euo pipefail
echo "=== users_inserts head/tail ==="
head -40 /root/restore-users/users_inserts.sql
echo "..."
grep -n "INSERT" /root/restore-users/users_inserts.sql | head -10
echo "count INSERT: $(grep -c INSERT /root/restore-users/users_inserts.sql || true)"
echo "count COPY: $(grep -c '^COPY' /root/restore-users/users_inserts.sql || true)"

echo "=== convert COPY users to INSERT via psql in scratch ==="
# If scratch still up, dump differently
if docker ps -a --format '{{.Names}}' | grep -q aeternum-scratch-pg; then
  docker start aeternum-scratch-pg >/dev/null 2>&1 || true
fi
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -tAc "SELECT count(*) FROM users;"

# Use COPY TO stdout then load as inserts via python
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -c "COPY (SELECT id, name, email, hashed_password, role, rayos_balance, historical_rayos, username, bio, profile_image_url, favorite_genres, reset_token, reset_token_expiry, is_banned, registration_ip, created_at, referred_by_qr_id FROM users ORDER BY id) TO STDOUT WITH (FORMAT csv, NULL '')" > /root/restore-users/users.csv
wc -l /root/restore-users/users.csv
head -3 /root/restore-users/users.csv

python3 <<'PY'
import csv, subprocess, json

def run_sql(sql):
    p = subprocess.run(
        ["docker","exec","-i","docker-db-1","psql","-U","aeternum","-d","aeternum","-v","ON_ERROR_STOP=0"],
        input=sql, text=True, capture_output=True
    )
    return p.stdout, p.stderr

rows=[]
with open("/root/restore-users/users.csv", newline="", encoding="utf-8") as f:
    r=csv.reader(f)
    for row in r:
        if len(row)<17: 
            continue
        rows.append(row)
print("csv_rows", len(rows))

def q(v):
    if v is None or v=="":
        return "NULL"
    return "'" + str(v).replace("'","''") + "'"

cleanup=[]
stmts=[]
for row in rows:
    uid=int(row[0])
    email=row[2]
    if uid!=1:
        cleanup.append(f"DELETE FROM users WHERE id={uid} AND email IS DISTINCT FROM {q(email)};")
        cleanup.append(f"DELETE FROM users WHERE email={q(email)} AND id<>{uid};")
    cols="id,name,email,hashed_password,role,rayos_balance,historical_rayos,username,bio,profile_image_url,favorite_genres,reset_token,reset_token_expiry,is_banned,registration_ip,created_at,referred_by_qr_id,email_verified,google_id,google_email"
    # google_id etc not in csv; leave NULL for those from dump users unless present
    vals=[q(row[0]),q(row[1]),q(row[2]),q(row[3]),q(row[4]),row[5] or "0",row[6] or "0",q(row[7]),q(row[8]),q(row[9]),q(row[10]),q(row[11]),q(row[12]),row[13] or "false",q(row[14]),q(row[15]),row[16] or "NULL","TRUE","NULL","NULL"]
    stmts.append(f"INSERT INTO users ({cols}) VALUES ({','.join(vals)}) ON CONFLICT (email) DO NOTHING;")

print("stmts", len(stmts))
out, err = run_sql("SET session_replication_role = replica;\n"+"\n".join(cleanup)+"\n"+"\n".join(stmts)+"\nSET session_replication_role = DEFAULT;\n")
print("stdout_tail", (out or "")[-400:])
print("stderr_tail", (err or "")[-400:])
PY

echo "=== counts after users merge ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -c 'SELECT id, email, name, role FROM users ORDER BY id LIMIT 20;'

echo "=== verify login admin + a restored user email exists ==="
curl -s -c /tmp/cj3.txt -o /tmp/l6.txt -w "admin=%{http_code}\n" -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'

echo DONE
