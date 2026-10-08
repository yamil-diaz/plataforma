#!/bin/bash
echo "=== python procs via /proc ==="
for d in /proc/[0-9]*; do
  pid=${d#/proc/}
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null || true)
  case "$cmd" in
    *restore_all*|*python*) echo "PID $pid: $cmd";;
  esac
done
echo "=== try short psql with timeout ==="
timeout 8 docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM books;' || echo "books count timeout/locked"
timeout 8 docker exec docker-db-1 psql -U aeternum -d aeternum -t -c 'SELECT count(*) FROM users;' || echo "users count timeout"
echo "=== locks ==="
timeout 8 docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT pid, state, wait_event_type, left(query,80) FROM pg_stat_activity WHERE datname='aeternum';" || true
echo DONE
