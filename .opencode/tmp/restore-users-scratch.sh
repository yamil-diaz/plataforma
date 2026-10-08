#!/bin/bash
set -euo pipefail
DUMP=/root/plataforma_ugk5_20260827_210207.dump

echo "=== 1) verify API after pool fix ==="
curl -s -o /dev/null -w "books_api=%{http_code}\n" --max-time 20 https://aeternumlibrary.com/api/books
curl -s --max-time 20 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books_len", len(d) if isinstance(d,list) else d)' || echo books_parse_fail
curl -s -o /dev/null -w "https=%{http_code}\n" --max-time 15 https://aeternumlibrary.com

echo "=== 2) spin scratch PG18 and restore dump there ==="
docker rm -f aeternum-scratch-pg 2>/dev/null || true
docker volume rm -f aeternum-scratch-pgdata 2>/dev/null || true
docker run -d --name aeternum-scratch-pg \
  -e POSTGRES_PASSWORD=scratch -e POSTGRES_DB=aeternum \
  -v aeternum-scratch-pgdata:/var/lib/postgresql/data \
  postgres:18-alpine
sleep 6
docker exec aeternum-scratch-pg pg_isready -U postgres

echo "=== 3) restore full dump into scratch ==="
docker exec -i aeternum-scratch-pg pg_restore -U postgres -d aeternum --no-owner --no-acl /dev/stdin < "$DUMP" || {
  echo "pg_restore reported errors (continuing if tables exist)"
}

echo "=== 4) count users in scratch ==="
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) FROM users;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -t -c 'SELECT count(*) FROM books;'
docker exec aeternum-scratch-pg psql -U postgres -d aeternum -c 'SELECT id, email, name, role FROM users ORDER BY id LIMIT 15;'

echo "=== 5) export users (+ dependent user tables) from scratch as INSERT SQL ==="
mkdir -p /root/restore-users
docker exec aeternum-scratch-pg pg_dump -U postgres -d aeternum \
  --data-only --column-inserts \
  -t users -t login_attempts -t password_resets \
  -t rayos_transactions -t reviews -t reading_progress -t reading_sessions \
  -t reading_daily_pages -t book_interactions -t user_badges -t user_addresses \
  -t orders -t order_items -t digital_entitlements -t physical_orders \
  -t ai_conversations -t ai_messages -t notifications \
  -t forum_posts -t forum_replies -t forum_likes -t forum_bookmarks \
  -t forum_follows -t qr_codes -t qr_visits \
  > /root/restore-users/from_render.sql 2>/root/restore-users/dump_err.txt || true
wc -l /root/restore-users/from_render.sql
head -c 500 /root/restore-users/from_render.sql
echo
cat /root/restore-users/dump_err.txt | head -20

echo "=== DONE_PHASE_SCRATCH ==="
