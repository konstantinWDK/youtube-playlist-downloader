# 🎵 YouTube MP3 Downloader

![Screenshot de la aplicación](assets/screenshot.png)

Una aplicación nativa para macOS, rápida y ligera construida con **Flask**, **yt-dlp** y **FFmpeg** para descargar y convertir videos y listas de reproducción de YouTube a audio **MP3 (192 kbps)** de alta calidad.

---

## ✨ Características

- 🎧 **Conversión de Alta Calidad**: Extracción directa a MP3 (192 kbps) con FFmpeg integrado.
- 📋 **Soporte de Listas y Lotes**: Descarga videos individuales o playlists completas.
- 📁 **Integración Nativa**: Selección de carpeta de descargas desde la interfaz y apertura directa en Finder.
- 🚀 **100% Autónoma**: No requiere Homebrew, Python ni dependencias en tu Mac. Instalar y usar.

---

## 🍎 Instalación en macOS (Recomendado)

La forma más sencilla de utilizar la aplicación en tu día a día:

1. Ve a la carpeta `releases/` de este repositorio o accede a la web de descarga.
2. Descarga el archivo **`YouTubePlaylistDownloader.dmg`**.
3. Abre el archivo y arrastra la aplicación a tu carpeta de **Aplicaciones**.
4. ¡Abre la app y empieza a descargar!

---

## 🌐 Despliegue Web (Landing Page)

La aplicación incluye un modo web (`WEB_MODE=True`) diseñado para ser desplegado en servicios como **Coolify** o servidores VPS. 
Al desplegarse en web, **las descargas directas se desactivan por seguridad**. La interfaz web se transforma en una *Landing Page* promocional que permite a los visitantes descargar el archivo `.dmg` de tu aplicación.

### Despliegue rápido con Docker
```bash
git clone https://github.com/<TU-USUARIO>/youtube-playlist-downloader.git
cd youtube-playlist-downloader
docker compose up -d --build
```
Abre `http://localhost:5006` para ver la Landing Page.

*Nota: Para habilitar el modo de descargas en la web localmente, puedes iniciar la app con `WEB_MODE=false python app.py`.*

---

## 🛠️ Desarrollo: Compilar la App de Mac

Si deseas modificar el código y recompilar la aplicación nativa para macOS:

1. Instala las dependencias del sistema:
   ```bash
   brew install create-dmg
   ```
2. Crea el entorno virtual e instala los paquetes:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Ejecuta el script de construcción:
   ```bash
   bash build_mac.sh
   ```
4. Encontrarás el nuevo `.dmg` en la carpeta `dist/`.

---

## ⚖️ Licencia y Aviso Legal

Este proyecto se distribuye bajo la licencia MIT con fines educativos y de uso personal. Asegúrate de cumplir con los términos de servicio de YouTube y las leyes de derechos de autor aplicables en tu jurisdicción.
