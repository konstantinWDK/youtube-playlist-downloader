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
            --icon "logo.icns" \
            --osx-bundle-identifier "com.konstantink.youtube-playlist-downloader" \
            --collect-all static_ffmpeg \
            --add-data "templates:templates" \
            --add-data "static:static" \
            desktop.py

echo "============================================="
echo "✅ ¡Construcción finalizada!"
echo "Tu aplicación de Mac se encuentra en la carpeta 'dist/'"
echo "Puedes abrir dist/YouTubePlaylistDownloader.app"
echo "============================================="

# Generar archivo DMG si create-dmg está instalado
if command -v create-dmg &> /dev/null; then
    echo "Empaquetando en archivo .dmg para distribución..."
    
    # Limpiar DMG anterior si existe
    rm -f dist/YouTubePlaylistDownloader.dmg

    create-dmg \
      --volname "YouTubePlaylistDownloader" \
      --volicon "logo.icns" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 100 \
      --icon "YouTubePlaylistDownloader.app" 150 190 \
      --hide-extension "YouTubePlaylistDownloader.app" \
      --app-drop-link 450 185 \
      "dist/YouTubePlaylistDownloader.dmg" \
      "dist/YouTubePlaylistDownloader.app"
      
    echo "✅ Archivo generado exitosamente en: dist/YouTubePlaylistDownloader.dmg"
else
    echo "⚠️ 'create-dmg' no está instalado en tu Mac."
    echo "Para poder generar archivos .dmg automáticamente en tu local, instálalo con:"
    echo "brew install create-dmg"
    echo "O comprime la carpeta .app en un .zip manualmente."
fi
