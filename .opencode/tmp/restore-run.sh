#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker

echo "=== 1) compose RENDER=false ==="
sed -i 's/^\(\s*-\s*\)RENDER=true/\1RENDER=false/' docker-compose.yml
grep -n 'RENDER=' docker-compose.yml

echo "=== 2) copy restore script into running app ==="
docker cp /root/restore_all.py docker-app-1:/app/restore_all.py

echo "=== 3) run restore inside app ==="
docker exec -w /app docker-app-1 python restore_all.py

echo "=== 4) db counts ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM books;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM users;'
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='books' AND column_name IN ('cover_image_url','uploader_id');"

echo "=== 5) recreate app ==="
docker compose up -d --force-recreate app
sleep 5
docker compose ps
docker compose logs app --tail 25

echo "=== 6) verify ==="
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
        print("sample_keys", sorted(d[0].keys())[:15])
        print("first_title", d[0].get("title"))
        print("first_cover", d[0].get("cover_image_url"))
        print("first_pdf", d[0].get("pdf_path"))
else:
    print(d)
PY

echo "=== app env ==="
docker exec docker-app-1 printenv RENDER || true
docker exec docker-app-1 printenv STORAGE_DIR || true
docker exec docker-app-1 printenv ENV || true

echo DONE
