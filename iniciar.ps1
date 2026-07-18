# Script de Inicialización y Arranque de la Plataforma Lectura y Rayos para Windows
# Ejecución: Clic derecho en el archivo -> "Ejecutar con PowerShell"

Clear-Host
$host.UI.RawUI.WindowTitle = "Instalador y Arrancador - Lectura Rayos"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  INICIALIZADOR AUTOMÁTICO: PLATAFORMA LECTURA Y RAYOS" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Directorio base del script
$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BASE_DIR

# --- 1. VERIFICACIONES PREVIAS ---
Write-Host "`n[1/4] Verificando requisitos del sistema..." -ForegroundColor Yellow

# Verificar Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✔ Python detectado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python no está instalado o no está en el PATH de Windows." -ForegroundColor Red
    Write-Host "Por favor instala Python (versión 3.9 o superior) desde python.org y marca la casilla 'Add Python to PATH' durante la instalación." -ForegroundColor DarkYellow
    Read-Host "Presiona Enter para salir..."
    exit
}

# Verificar Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✔ Node.js detectado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js no está instalado o no está en el PATH de Windows." -ForegroundColor Red
    Write-Host "Por favor instala Node.js (versión 18 o superior) desde nodejs.org para poder ejecutar el frontend." -ForegroundColor DarkYellow
    Read-Host "Presiona Enter para salir..."
    exit
}

# --- 2. CONFIGURAR BACKEND ---
Write-Host "`n[2/4] Configurando Servidor Backend (Python + SQLite)..." -ForegroundColor Yellow

if (-not (Test-Path "backend\venv")) {
    Write-Host "Creando entorno virtual de Python (venv)... esto tomará unos segundos." -ForegroundColor Gray
    python -m venv backend\venv
}

Write-Host "Instalando dependencias de Python (FastAPI, pypdf, etc.)..." -ForegroundColor Gray
& backend\venv\Scripts\pip install -r backend\requirements.txt

# Generar archivo ZIP de prueba automáticamente
if (Test-Path "generar_muestra.py") {
    Write-Host "Generando archivo ZIP de muestra para pruebas..." -ForegroundColor Gray
    & backend\venv\Scripts\python generar_muestra.py
}

# --- 3. CONFIGURAR FRONTEND ---
Write-Host "`n[3/4] Configurando Interfaz Frontend (React + Vite)..." -ForegroundColor Yellow

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Instalando dependencias de Node (npm install)... esto puede tomar un minuto." -ForegroundColor Gray
    Set-Location "$BASE_DIR\frontend"
    npm install
    Set-Location $BASE_DIR
} else {
    Write-Host "✔ Dependencias de Node ya instaladas." -ForegroundColor Green
}

# --- 4. INICIAR SERVIDORES ---
Write-Host "`n[4/4] Levantando servidores locales en ventanas separadas..." -ForegroundColor Green

# Iniciar Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BASE_DIR\backend'; .\venv\Scripts\activate; python server.py" -WindowStyle Normal

# Iniciar Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BASE_DIR\frontend'; npm run dev" -WindowStyle Normal

Write-Host "`n¡Listo! Servidores iniciados con éxito." -ForegroundColor Green
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "• Backend: http://localhost:8000" -ForegroundColor Gray
Write-Host "• Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Abriendo tu navegador en el catálogo de libros..." -ForegroundColor Cyan

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
