#!/bin/bash
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  running=0
  for d in /proc/[0-9]*; do
    cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null || true)
    case "$cmd" in *paginate_covers*) running=1;; esac
  done
  pages=$(docker exec docker-db-1 psql -U aeternum -d aeternum -tAc 'SELECT count(*) FROM book_pages;')
  withp=$(docker exec docker-db-1 psql -U aeternum -d aeternum -tAc "SELECT count(*) FROM books b WHERE EXISTS (SELECT 1 FROM book_pages p WHERE p.book_id=b.id);")
  nocov=$(docker exec docker-db-1 psql -U aeternum -d aeternum -tAc "SELECT count(*) FROM books WHERE cover_image_url IS NULL OR cover_image_url='';")
  echo "t=$i running=$running pages=$pages with_pages=$withp need_cover=$nocov"
  if [ "$running" = "0" ]; then
    echo FINISHED
    break
  fi
  sleep 30
done
echo DONE
