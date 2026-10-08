#!/bin/bash
echo "=== FKs to books ==="
docker exec docker-db-1 psql -U aeternum -d aeternum -c "
SELECT tc.table_name, kcu.column_name, rc.delete_rule, rc.update_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
JOIN information_schema.referential_constraints rc ON tc.constraint_name=rc.constraint_name
JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name=ccu.constraint_name
WHERE tc.constraint_type='FOREIGN KEY' AND ccu.table_name='books'
ORDER BY tc.table_name;
"

echo "=== try delete test book 172 as admin ==="
curl -s -c /tmp/del.txt -o /dev/null -X POST https://aeternumlibrary.com/api/login \
  -H "Content-Type: application/json" -H "Origin: https://aeternumlibrary.com" \
  -d '{"email":"admin@plataforma.com","password":"admin123"}'
curl -s -b /tmp/del.txt -o /tmp/del_resp.txt -w "delete=%{http_code}\n" -X DELETE "https://aeternumlibrary.com/api/books/172" \
  -H "Origin: https://aeternumlibrary.com"
head -c 500 /tmp/del_resp.txt
echo

echo "=== try delete without auth ==="
curl -s -o /tmp/del2.txt -w "noauth=%{http_code}\n" -X DELETE "https://aeternumlibrary.com/api/books/99999" \
  -H "Origin: https://aeternumlibrary.com"
head -c 300 /tmp/del2.txt
echo

echo "=== app logs ==="
cd /root/plataforma/docker && docker compose logs app --tail 25 2>&1 | grep -iE 'delete|books|error|violat|foreign' | tail -15
echo DONE
