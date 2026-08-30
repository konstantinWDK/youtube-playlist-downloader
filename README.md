# 🎵 YouTube MP3 Downloader

Una aplicación web moderna, rápida y ligera construida con **Flask**, **yt-dlp** y **FFmpeg** para descargar y convertir videos y listas de reproducción de YouTube a audio **MP3 (192 kbps)** de alta calidad.

Diseñada y preparada para desplegarse fácilmente en **Coolify** o cualquier servidor con Docker.

---

## ✨ Características

- 🎧 **Conversión de Alta Calidad**: Extracción directa de audio a formato MP3 a 192 kbps utilizando FFmpeg.
- 📋 **Soporte para Listas de Reproducción y Lotes**: Descarga múltiples videos individuales o listas completas con solo pegar las URLs.
- ⚡ **Procesamiento Asíncrono**: Cola de descargas en segundo plano sin bloquear la interfaz de usuario.
- 🧹 **Limpieza Automática**: Rutina periódica en segundo plano que elimina archivos descargados antiguos (por defecto tras 2 horas) para no saturar el almacenamiento del servidor.
- 🛡️ **Preparado para Producción**: Servido con **Gunicorn**, soporte para proxy inverso (`ProxyFix`) y endpoint `/health` para monitorización.
- 📱 **Interfaz Moderna y Responsiva**: Diseño pulido con soporte móvil, animaciones sutiles y seguimiento en tiempo real.

---

## 🚀 Despliegue en Coolify

Esta aplicación está 100% optimizada para desplegarse en **Coolify** conectado a tu repositorio de GitHub:

### Paso 1: Subir a GitHub
1. Inicializa tu repositorio Git y súbelo a tu cuenta de GitHub (ver sección [Subir a GitHub](#-subir-a-github)).

### Paso 2: Crear la Aplicación en Coolify
1. En tu panel de Coolify, ve a tu **Project / Environment**.
2. Haz clic en **+ New Resource** -> **Application** -> **Public/Private GitHub Repository**.
3. Selecciona tu repositorio `youtube-playlist-downloader` y la rama (`main` o `master`).
4. Selecciona **Dockerfile** como tipo de construcción (Build Pack).

### Paso 3: Configurar Dominio y Puerto
1. En la configuración de la aplicación:
   - **Domains**: Asigna tu subdominio (ej: `https://yt.tudominio.com`).
   - **Port**: `5006` (o déjalo en el puerto por defecto expuesto).
   - **Health Check Path**: `/health`

### Paso 4: Desplegar
1. Haz clic en **Deploy**. Coolify construirá la imagen Docker, configurará el certificado SSL automático mediante Let's Encrypt y enrutará el tráfico a través de su proxy inverso.

---

## 🐳 Despliegue con Docker Compose (Servidor Propio)

Si prefieres ejecutarlo directamente con Docker Compose en tu servidor:

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/youtube-playlist-downloader.git
cd youtube-playlist-downloader

# 2. Levantar el contenedor
docker compose up -d --build
```

La aplicación estará disponible en `http://localhost:5006` o en la IP de tu servidor.

---

## 💻 Ejecución Local (Desarrollo)

### Requisitos previos
- Python 3.10+
- FFmpeg instalado en el sistema (`sudo apt install ffmpeg` en Ubuntu/Debian o `brew install ffmpeg` en macOS)

### Pasos
```bash
# 1. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor
python app.py
```

Accede a `http://localhost:5006` en tu navegador.

---

## ⚙️ Variables de Entorno

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `PORT` | Puerto en el que escucha el servidor web | `5006` |
| `DOWNLOAD_FOLDER` | Directorio donde se almacenan temporalmente los archivos | `downloads` |
| `FILE_EXPIRY_SECONDS` | Tiempo en segundos antes de eliminar archivos antiguos | `7200` (2 horas) |

---

## 📦 Subir a GitHub

Para subir este proyecto a un nuevo repositorio en GitHub:

```bash
# Inicializar repositorio git
git init -b main

# Añadir todos los archivos
git add .

# Crear el primer commit
git commit -m "feat: initial commit - ready for coolify deployment"

# Vincular con tu repositorio remoto de GitHub
git remote add origin https://github.com/<TU_USUARIO>/<TU_REPOSITORIO>.git

# Subir cambios
git push -u origin main
```

---

## 📡 API Endpoints

- `GET /` : Interfaz web principal.
- `GET /health` : Verificación de estado del servicio para Docker/Coolify.
- `POST /download` : Inicia la descarga de una lista de URLs en formato JSON (`{"urls": ["https://..."]}`).
- `GET /status/<job_id>` : Consulta el estado actual de una tarea (`queued`, `processing`, `completed`, `failed`).
- `GET /files/<filename>` : Descarga directa del archivo MP3 generado.

---

## ⚖️ Licencia y Aviso Legal

Este proyecto se proporciona únicamente con fines educativos y de uso personal. Asegúrate de cumplir con los términos de servicio de YouTube y las leyes de derechos de autor aplicables en tu jurisdicción.
