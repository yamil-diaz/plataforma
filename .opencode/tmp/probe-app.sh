#!/bin/bash
echo "=== Dockerfile ==="
grep -nE 'WORKDIR|COPY|CMD|ENTRYPOINT' /root/plataforma/docker/Dockerfile | head -40
echo "=== app container paths ==="
docker exec docker-app-1 sh -c 'pwd; ls -la; python -c "import storage_config,os; print(storage_config.__file__); print(storage_config.STORAGE_BOOKS); print(os.listdir(\"/app\") if os.path.isdir(\"/app\") else \"no /app\")"'
echo "=== is production_books in image? ==="
docker exec docker-app-1 sh -c 'ls -la /app/backend/production_books.json /app/production_books.json /root/plataforma/backend/production_books.json 2>&1 | head -20'
echo DONE
