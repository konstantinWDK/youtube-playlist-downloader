# Script de compilación para Windows en PowerShell
$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Preparando entorno para compilar en Windows (.exe)..." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 0. Cerrar instancias previas si están abiertas para evitar bloqueos de archivos
Stop-Process -Name "YouTubePlaylistDownloader" -Force -ErrorAction SilentlyContinue

# 1. Crear / activar entorno virtual
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual venv..." -ForegroundColor Yellow
    python -m venv venv
}

$venvPython = Join-Path (Get-Location) "venv\Scripts\python.exe"
$venvPip = Join-Path (Get-Location) "venv\Scripts\pip.exe"
$venvPyinstaller = Join-Path (Get-Location) "venv\Scripts\pyinstaller.exe"

# 2. Instalar dependencias
Write-Host "Instalando dependencias desde requirements.txt..." -ForegroundColor Yellow
& $venvPip install -r requirements.txt
& $venvPython -c "import static_ffmpeg; static_ffmpeg.add_paths()"

# 3. Generar logo.ico si no existe a partir de logo.icns
if (-not (Test-Path "logo.ico")) {
    Write-Host "Generando logo.ico..." -ForegroundColor Yellow
    & $venvPython -c "from PIL import Image; img = Image.open('logo.icns'); img.save('logo.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])"
}

# 4. Limpiar builds anteriores
Write-Host "Limpiando carpetas build y dist..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# 5. Empaquetar con PyInstaller
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Empaquetando con PyInstaller..." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

& $venvPyinstaller --name "YouTubePlaylistDownloader" `
                   --windowed `
                   --onefile `
                   --icon "logo.ico" `
                   --collect-all static_ffmpeg `
                   --add-data "templates;templates" `
                   --add-data "static;static" `
                   desktop.py

# 6. Copiar a la carpeta releases
if (-not (Test-Path "releases")) {
    New-Item -ItemType Directory -Path "releases" | Out-Null
}

$exePath = "dist\YouTubePlaylistDownloader.exe"
if (Test-Path $exePath) {
    Copy-Item -Path $exePath -Destination "releases\YouTubePlaylistDownloader.exe" -Force
    Write-Host "=======================================================" -ForegroundColor Green
    Write-Host "✅ [ÉXITO] Compilación finalizada correctamente." -ForegroundColor Green
    Write-Host "El ejecutable se ha generado y copiado a:" -ForegroundColor Green
    Write-Host "  - dist\YouTubePlaylistDownloader.exe" -ForegroundColor White
    Write-Host "  - releases\YouTubePlaylistDownloader.exe" -ForegroundColor White
    Write-Host "=======================================================" -ForegroundColor Green
} else {
    Write-Error "No se encontró el archivo $exePath"
}
