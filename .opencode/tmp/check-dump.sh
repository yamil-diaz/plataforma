#!/bin/bash
# Inspeccionar dump local en el VPS o traerlo
DUMP_LOCAL=/root/plataforma_ugk5_20260827_210207.dump
if [ ! -f "$DUMP_LOCAL" ]; then
  echo "dump not on vps yet"
else
  ls -lh "$DUMP_LOCAL"
  docker run --rm -v "$DUMP_LOCAL":/dump.dump -v /var/lib/docker/volumes/docker_pgdata/_data:/pgdata postgres:16-alpine \
    pg_restore --list /dump.dump 2>&1 | head -80
fi
echo "---"
# also check if dump exists only on PC
ls -lh /root/*.dump 2>/dev/null || true
echo DONE
