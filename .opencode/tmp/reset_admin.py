import bcrypt
import os
import psycopg2

pw = b"admin123"
h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode()
url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
print("connecting...")
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    "UPDATE users SET hashed_password=%s, email_verified=TRUE, is_banned=FALSE WHERE email=%s RETURNING id, email, role",
    (h, "admin@plataforma.com"),
)
print("updated", cur.fetchone())
cur.execute("SELECT hashed_password FROM users WHERE email=%s", ("admin@plataforma.com",))
row = cur.fetchone()
print("hash_prefix", (row[0] or "")[:20])
print("verify_admin123", bcrypt.checkpw(pw, (row[0] or "").encode()))
conn.commit()
cur.close()
conn.close()
print("DONE_RESET")
