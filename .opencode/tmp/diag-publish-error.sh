#!/bin/bash
echo "=== recent app errors publish ==="
cd /root/plataforma/docker && docker compose logs app --tail 80 2>&1 | grep -iE 'create_book|POST /api/books|rechazado|Error al guardar|422|409|413|Traceback|Exception|vacalola|upload' | tail -40
echo "=== last POST /api/books ==="
docker compose logs app --tail 200 2>&1 | grep 'POST /api/books' | tail -10
echo "=== max pdf size ==="
grep -n 'MAX_PDF' /root/plataforma/backend/server.py | head
echo DONE
