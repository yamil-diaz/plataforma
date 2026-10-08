#!/bin/bash
curl -s -c /tmp/ai5.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/ai5.txt -o /tmp/ai5_resp.txt -w "ai_chat=%{http_code}\n" -X POST https://aeternumlibrary.com/api/ai/chat \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"message":"hola, que libros tienes?"}'
python3 -c 'import json; d=json.load(open("/tmp/ai5_resp.txt")); print("success", d.get("success")); print("provider", d.get("provider")); print("model", d.get("model")); print("msg", (d.get("message") or "")[:120])'

HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
echo "js=$JS"
curl -s --max-time 20 "https://aeternumlibrary.com/assets/$JS" | grep -oE "Mis Libros|Explorar por categoría|Buscar por título|Mis Compras|Panel del Lector" | sort -u

curl -s -o /dev/null -w "https=%{http_code}\n" https://aeternumlibrary.com
curl -s --max-time 15 https://aeternumlibrary.com/api/books | python3 -c 'import sys,json; d=json.load(sys.stdin); print("books", len(d) if isinstance(d,list) else d)'
echo DONE
