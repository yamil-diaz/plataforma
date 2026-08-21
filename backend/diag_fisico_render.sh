#!/usr/bin/env bash
# ============================================================================
# diag_fisico_render.sh — DIAGNÓSTICO FÍSICO DE PRODUCCIÓN (SOLO LECTURA).
# ============================================================================
# Ejecutar DENTRO del shell de Render (carpeta del backend del despliegue).
#
#   bash diag_fisico_render.sh
#
# - CONECTA a la BD de producción en READ-ONLY
#   (default_transaction_read_only=on; nunca INSERT/UPDATE/DELETE).
# - Verifica FÍSICAMENTE cada pdf_path registrado: [ -f ], tamaño y magic %PDF.
# - Cruzamiento explícito en bash: [ -f "$pdf_path" ] para cada pdf_path.
# - NO ejecuta admin_catalog_tool.py, seed_books.py, ni ninguna limpieza.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "########################################################################"
echo "# PASO 1/2: diag_catalog.py (BD READ-ONLY + verificación física)"
echo "########################################################################"
python diag_catalog.py 2>/dev/null | tee /tmp/diag_fichero.txt
STATUS_PY=${PIPESTATUS[0]}
if [ "$STATUS_PY" -ne 0 ]; then
    echo "ERROR: diag_catalog.py falló (código $STATUS_PY). Revisar DATABASE_URL y STORAGE_DIR." >&2
    exit 1
fi

echo ""
echo "########################################################################"
echo "# PASO 2/2: cruzamiento explícito [ -f \"\$pdf_path\" ] por libro"
echo "########################################################################"
python - <<'EOF' > /tmp/diag_paths.txt
import json, sys
# Re-lee la salida JSONL del informe (cada línea con pdf_path).
for line in open("/tmp/diag_fichero.txt", encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        b = json.loads(line)
    except Exception:
        continue
    p = (b.get("pdf_path") or "").strip()
    if p:
        print(f"{b.get('id')}\t{p}")
EOF

while IFS=$'\t' read -r id p; do
    if [ -f "$p" ]; then
        size=$(stat -c %s "$p" 2>/dev/null || echo "?")
        echo "OK   id=$id size=$size  $p"
    else
        echo "MISS id=$id  $p"
    fi
done < /tmp/diag_paths.txt

echo ""
echo "PRODUCCIÓN NO FUE MODIFICADA."