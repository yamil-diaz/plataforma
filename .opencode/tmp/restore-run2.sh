#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== 1) stop app (libera locks sobre books) ==="
docker compose stop app
sleep 2

echo "=== 2) kill leftover restore / idle tx ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=0 -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='aeternum' AND pid <> pg_backend_pid() AND state <> 'idle';" || true
sleep 1

echo "=== 3) schema via psql ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 -c \
  "ALTER TABLE books ADD COLUMN IF NOT EXISTS cover_image_url TEXT;"
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 -c \
  "ALTER TABLE books ADD COLUMN IF NOT EXISTS uploader_id INTEGER;"
docker exec docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 -c \
  "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_books_uploader') THEN ALTER TABLE books ADD CONSTRAINT fk_books_uploader FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE SET NULL; END IF; END \$\$;"
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='books' AND column_name IN ('cover_image_url','uploader_id');"

echo "=== 4) run restore via compose run (nueva container, mismas volumes/env) ==="
docker compose run --rm --no-deps \
  -v /root/restore_all.py:/app/restore_all.py:ro \
  app python /app/restore_all.py

echo "=== 5) counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS books FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) AS users FROM users;'

echo "=== 6) start app ==="
docker compose up -d app
sleep 5
docker compose ps
docker compose logs app --tail 20

echo "=== 7) verify ==="
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 20 https://aeternumlibrary.com/api/books -o /tmp/api_books.json -w "api=%{http_code}\n"
python3 - <<'PY'
import json
with open("/tmp/api_books.json") as f:
    d=json.load(f)
print("type", type(d).__name__)
if isinstance(d, list):
    print("len", len(d))
    if d:
        print("first_title", d[0].get("title"))
        print("first_cover", d[0].get("cover_image_url"))
        print("first_pdf", d[0].get("pdf_path"))
else:
    print(str(d)[:300])
PY
docker exec docker-app-1 printenv RENDER || true
docker exec docker-app-1 printenv STORAGE_DIR || true
echo DONE
