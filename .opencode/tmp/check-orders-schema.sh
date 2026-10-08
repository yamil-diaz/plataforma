#!/bin/bash
docker exec docker-db-1 psql -U aeternum -d aeternum -c "\d order_items" | head -25
docker exec docker-db-1 psql -U aeternum -d aeternum -c "\d orders" | head -30
echo DONE
