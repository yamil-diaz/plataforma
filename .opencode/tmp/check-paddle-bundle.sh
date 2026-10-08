#!/bin/bash
HTML=$(curl -s --max-time 15 https://aeternumlibrary.com/)
JS=$(echo "$HTML" | sed -n 's/.*src="\/assets\/\([^"]*\.js\)".*/\1/p' | head -1)
echo "js=$JS"
curl -s --max-time 20 "https://aeternumlibrary.com/assets/$JS" > /tmp/bundle.js
echo "=== paddle strings in bundle ==="
grep -oE "live_[A-Za-z0-9_]+|sandbox_[A-Za-z0-9_]+|VITE_PADDLE[^\"']*|environment:\"[a-z]+\"|@paddle/paddle-js" /tmp/bundle.js | sort -u | head -30
echo "=== size ==="
wc -c /tmp/bundle.js
echo "=== PaddleInit in App? ==="
grep -n "PaddleInit\|initializePaddle" /root/plataforma/frontend/src/App.jsx | head
echo "=== package paddle ==="
grep -n paddle /root/plataforma/frontend/package.json
echo DONE
