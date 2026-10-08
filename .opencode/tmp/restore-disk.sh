#!/bin/bash
set -euo pipefail
DUMP=/root/aeternum-disk.tar.gz
BACKUP_DIR=/root/render-backup-aeternum
VOLUME=docker_aeternum-data

echo "=== 1) Verify tarball ==="
ls -lh "$DUMP"
tar tzf "$DUMP" | wc -l
gzip -t "$DUMP" && echo "gzip OK"

echo "=== 2) Extract to backup dir ==="
mkdir -p "$BACKUP_DIR"
tar xzf "$DUMP" -C "$BACKUP_DIR"
echo "backup extract OK"
du -sh "$BACKUP_DIR"
find "$BACKUP_DIR" -type f | wc -l

echo "=== 3) Copy into docker volume ==="
docker run --rm -v "$VOLUME":/data -v "$BACKUP_DIR":/backup alpine sh -c '
  set -e
  cp -a /backup/aeternum/. /data/
  echo "=== volume after copy ==="
  du -sh /data
  find /data -type f | wc -l
  ls -la /data
  ls /data/books 2>/dev/null | head -5 || true
  ls /data/covers 2>/dev/null | head -5 || true
'

echo "=== 4) Counts compare ==="
echo -n "PC tar entries: "
tar tzf "$DUMP" | wc -l
echo -n "backup files: "
find "$BACKUP_DIR" -type f | wc -l
echo -n "volume files: "
docker run --rm -v "$VOLUME":/data alpine sh -c 'find /data -type f | wc -l'

echo "=== 5) Cleanup remote temp on Render (not the disk) ==="
# disk de Render NO se toca
echo "Render disk untouched"

echo "=== 6) App still healthy ==="
cd /root/plataforma/docker
docker compose ps
curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s -o /dev/null -w "api=%{http_code}\n" https://aeternumlibrary.com/api/books
echo "DONE"
