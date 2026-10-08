#!/bin/bash
set -euo pipefail
cd /root/plataforma/docker
# copiar cambios de frontend al build context del server
# el código fuente del frontend está en /root/plataforma/frontend en el server?
ls /root/plataforma/frontend/src/pages/DashboardPage.jsx 2>/dev/null || echo "frontend source missing on server"
