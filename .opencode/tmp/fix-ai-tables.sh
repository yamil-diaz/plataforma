#!/bin/bash
set -euo pipefail
echo "=== create AI tables ==="
docker exec -i docker-db-1 psql -U aeternum -d aeternum -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS ai_consumption (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_id TEXT NOT NULL UNIQUE,
    operation TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    rayos_cost INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_consumption_user ON ai_consumption(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_consumption_created ON ai_consumption(created_at);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL
        REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_updated
    ON ai_conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation
    ON ai_messages(conversation_id, id);
SQL

echo "=== tables ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'ai_%';"

echo "=== test ai chat ==="
curl -s -c /tmp/ai2.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/ai2.txt -o /tmp/ai_resp2.txt -w "ai_chat=%{http_code}\n" -X POST https://aeternumlibrary.com/api/ai/chat \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"message":"hola, que libros tienes?"}'
head -c 600 /tmp/ai_resp2.txt
echo
echo DONE
