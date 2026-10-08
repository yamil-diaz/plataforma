#!/bin/bash
echo "=== try ai chat as admin ==="
# login and capture cookie
curl -s -c /tmp/ai.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/ai.txt -o /tmp/ai_resp.txt -w "ai_chat=%{http_code}\n" -X POST https://aeternumlibrary.com/api/ai/chat \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"message":"hola, que libros tienes?"}'
head -c 800 /tmp/ai_resp.txt
echo
echo "=== app logs ai ==="
cd /root/plataforma/docker && docker compose logs app --tail 80 | grep -iE 'ai_|gemini|conversation|error|traceback|exception' | tail -40
echo DONE
