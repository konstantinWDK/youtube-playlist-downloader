#!/bin/bash
set -e # Detener script si hay algún error

echo "Preparando entorno para empaquetar en Mac..."

# Activar el entorno virtual si existe, o crearlo
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Instalar dependencias necesarias
pip install -r requirements.txt

# Limpiar builds anteriores
rm -rf build dist

# Empaquetar con PyInstaller
# --windowed oculta la terminal de fondo en Mac/Windows
# --name define el nombre de la app
# --add-data incluye las carpetas estáticas y templates de Flask
pyinstaller --name "YouTubePlaylistDownloader" \
            --windowed \
            --add-data "templates:templates" \
            --add-data "static:static" \
            desktop.py

echo "============================================="
echo "✅ ¡Construcción finalizada!"
echo "Tu aplicación de Mac se encuentra en la carpeta 'dist/'"
echo "Puedes abrir dist/YouTubePlaylistDownloader.app"
echo "============================================="
