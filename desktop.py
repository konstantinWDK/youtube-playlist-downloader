import os
import sys
import webview
import threading
import time

# Asegurar que el servidor Flask corra en modo Desktop (sin restricciones)
os.environ['WEB_MODE'] = 'false'
# Por defecto las descargas irán a la carpeta de usuario
if getattr(sys, 'frozen', False):
    # Si está empaquetado (Mac/Windows), descargar en la carpeta Downloads del usuario
    home = os.path.expanduser("~")
    os.environ['DOWNLOAD_FOLDER'] = os.path.join(home, 'Downloads', 'YT_Downloads')
else:
    os.environ['DOWNLOAD_FOLDER'] = 'downloads'

from app import app

def start_server():
    # Desactivamos el reloader para evitar que abra dos ventanas
    app.run(host='127.0.0.1', port=5007, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Arrancar el servidor de Flask en un hilo de fondo
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    
    # Esperar un momento para que Flask esté listo
    time.sleep(1)

    # Arrancar la ventana nativa apuntando al servidor Flask
    webview.create_window(
        title='YouTube Playlist Downloader',
        url='http://127.0.0.1:5007',
        width=1000,
        height=800,
        resizable=True
    )
    
    # Iniciar la interfaz nativa
    webview.start()
