#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crea tabla author_withdrawals si no existe."""
import os
import psycopg2

url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS author_withdrawals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    method TEXT NOT NULL DEFAULT 'bank_transfer',
    account_details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','paid')),
    admin_note TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT
);
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_author_withdrawals_user
    ON author_withdrawals(user_id, created_at DESC);
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_author_withdrawals_status
    ON author_withdrawals(status, created_at DESC);
""")
conn.commit()
cur.close()
conn.close()
print("author_withdrawals OK")
