@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo Preparando entorno para compilar en Windows (.exe)...
echo =======================================================

:: 0. Cerrar instancias previas si están abiertas
taskkill /F /IM YouTubePlaylistDownloader.exe >nul 2>&1

:: 1. Activar o crear entorno virtual
if not exist "venv" (
    echo Creando entorno virtual venv...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: 2. Instalar dependencias
echo Instalando dependencias desde requirements.txt...
python -m pip install -r requirements.txt
python -c "import static_ffmpeg; static_ffmpeg.add_paths()"

:: 3. Generar logo.ico si no existe a partir de logo.icns
if not exist "logo.ico" (
    echo Generando logo.ico...
    python -c "from PIL import Image; img = Image.open('logo.icns'); img.save('logo.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])"
)

:: 4. Limpiar builds anteriores
echo Limpiando carpetas build y dist...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

:: 5. Empaquetar con PyInstaller
echo =======================================================
echo Empaquetando con PyInstaller...
echo =======================================================
pyinstaller --name "YouTubePlaylistDownloader" ^
            --windowed ^
            --onefile ^
            --icon "logo.ico" ^
            --version-file "file_version_info.txt" ^
            --collect-all static_ffmpeg ^
            --add-data "templates;templates" ^
            --add-data "static;static" ^
            desktop.py

if errorlevel 1 (
    echo [ERROR] La compilacion ha fallado.
    exit /b 1
)

:: 6. Copiar a la carpeta releases
if not exist "releases" mkdir releases

if exist "dist\YouTubePlaylistDownloader.exe" (
    copy /y "dist\YouTubePlaylistDownloader.exe" "releases\YouTubePlaylistDownloader.exe"
    echo =======================================================
    echo [EXITO] Compilacion finalizada correctamente.
    echo El ejecutable se ha generado y copiado a:
    echo   - dist\YouTubePlaylistDownloader.exe
    echo   - releases\YouTubePlaylistDownloader.exe
    echo =======================================================
) else (
    echo [ERROR] No se encontro el archivo dist\YouTubePlaylistDownloader.exe
    exit /b 1
)

pause
