# 🎵 YouTube MP3 Downloader

Una aplicación web moderna, rápida y ligera construida con **Flask**, **yt-dlp** y **FFmpeg** para descargar y convertir videos y listas de reproducción de YouTube a audio **MP3 (192 kbps)** de alta calidad.

Diseñada tanto para uso personal local como para despliegues en servidores domésticos, VPS o plataformas PaaS como **Coolify**.

---

## ✨ Características

- 🎧 **Conversión de Alta Calidad**: Extracción directa de audio a formato MP3 a 192 kbps utilizando FFmpeg.
- 📋 **Soporte para Listas de Reproducción y Lotes**: Descarga múltiples videos individuales o listas completas con solo pegar las URLs.
- ⚡ **Procesamiento Asíncrono**: Cola de descargas en segundo plano sin bloquear la interfaz ni la navegación.
- 🧹 **Limpieza Automática**: Rutina periódica en segundo plano que elimina archivos descargados antiguos (por defecto tras 2 horas) para proteger el almacenamiento del servidor.
- 🛡️ **Seguro y Preparado para Producción**: Servido con **Gunicorn**, protección contra Path Traversal, soporte para proxy inverso (`ProxyFix`) y endpoint `/health`.
- 📱 **Interfaz Moderna y Responsiva**: Diseño pulido con soporte móvil, animaciones sutiles y seguimiento de progreso en tiempo real.

---

## ⚡ Inicio Rápido (30 segundos con Docker)

La forma más rápida y recomendada de ejecutar la aplicación:

```bash
# 1. Clonar el repositorio
git clone https://github.com/<TU-USUARIO>/youtube-playlist-downloader.git
cd youtube-playlist-downloader

# 2. Levantar el contenedor
docker compose up -d --build
```

Abre tu navegador en 👉 **`http://localhost:5006`**

---

## 🚀 Opciones de Instalación

Elige el método que mejor se adapte a tus necesidades:

### Opción 1: Despliegue en Coolify (Recomendado para servidores)

Esta aplicación está 100% preparada para **Coolify**:

1. **Crear recurso en Coolify**:
   - Ve a tu proyecto en Coolify.
   - Selecciona **+ New Resource** ➔ **Application** ➔ **Public/Private GitHub Repository**.
   - Selecciona tu repositorio y la rama (`main`).
2. **Configuración de compilación**:
   - **Build Pack**: `Dockerfile`
   - **Port**: `5006`
   - **Health Check Path**: `/health`
3. **Dominio**:
   - Asigna tu dominio o subdominio (ej: `https://yt.tudominio.com`).
4. **Desplegar**:
   - Haz clic en **Deploy**. Coolify configurará SSL automático (Let's Encrypt) y enrutará el tráfico a través de su reverse proxy.

---

### Opción 2: Instalación Local con Python (Sin Docker)

#### Requisitos Previos:
- **Python 3.10 o superior**
- **FFmpeg** instalado en tu sistema:
  - **Ubuntu / Debian**: `sudo apt update && sudo apt install ffmpeg -y`
  - **macOS**: `brew install ffmpeg`
  - **Windows**: Descargar desde [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/) o con `winget install Gyan.FFmpeg` y verificar que esté en el `PATH`.

#### Pasos de Instalación:

```bash
# 1. Clonar el repositorio
git clone https://github.com/<TU-USUARIO>/youtube-playlist-downloader.git
cd youtube-playlist-downloader

# 2. Crear y activar entorno virtual
python3 -m venv venv

# En Linux / macOS:
source venv/bin/activate

# En Windows (CMD / PowerShell):
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar la aplicación
python app.py
```

Accede a **`http://localhost:5006`** en tu navegador.

---

### Opción 3: Aplicación de Escritorio Nativa (Mac)

Si deseas usar la aplicación localmente en tu Mac sin necesidad de abrir la terminal cada vez, puedes empaquetarla como una aplicación nativa (`.app` y `.dmg`) utilizando el script incluido.

#### Pasos para compilar:

```bash
# 1. Instalar la herramienta para generar DMGs
brew install create-dmg

# 2. Ejecutar el script de construcción
bash build_mac.sh
```

El script se encargará de instalar las dependencias necesarias y empaquetar la aplicación. Al finalizar, encontrarás el archivo `YouTubePlaylistDownloader.dmg` en la carpeta `dist/`, listo para ser instalado arrastrándolo a tu carpeta de Aplicaciones.

---

## ⚙️ Configuración y Variables de Entorno

Puedes personalizar la configuración creando un archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `PORT` | Puerto en el que escucha el servidor web | `5006` |
| `DOWNLOAD_FOLDER` | Directorio donde se almacenan temporalmente los archivos | `downloads` |
| `FILE_EXPIRY_SECONDS` | Tiempo en segundos antes de eliminar archivos descargados | `7200` (2 horas) |

---

## 🛠️ Solución de Problemas Frecuentes

<details>
<summary><b>1. YouTube ha cambiado su algoritmo y las descargas fallan</b></summary>

YouTube actualiza sus medidas frecuentemente. Para solucionarlo, simplemente actualiza `yt-dlp` a la última versión:

- **En Docker**: Reconstruye la imagen ejecutando `docker compose up -d --build --no-cache`
- **En Python Local**: Ejecuta `pip install --upgrade yt-dlp`
</details>

<details>
<summary><b>2. Error: "FFmpeg not found"</b></summary>

Asegúrate de haber instalado FFmpeg en tu sistema operativo y que el comando `ffmpeg -version` responda correctamente en tu terminal antes de iniciar la app sin Docker.
</details>

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Interfaz web interactiva |
| `GET` | `/health` | Chequeo de salud del servicio (retorna status HTTP 200) |
| `POST` | `/download` | Inicia la descarga en lote (`{"urls": ["https://..."]}`) |
| `GET` | `/status/<job_id>` | Consulta el estado de una tarea (`queued`, `processing`, `completed`, `failed`) |
| `GET` | `/files/<filename>` | Descarga segura del archivo MP3 generado |

---

## 🔒 Seguridad y Privacidad

- **Sin almacenamiento permanente**: Los audios descargados se eliminan automáticamente tras el período configurado (`FILE_EXPIRY_SECONDS`).
- **Seguridad en descargas**: Validación estricta con `os.path.basename` y `send_from_directory` para prevenir ataques de Path Traversal.
- **Sin credenciales requeridas**: No almacena cookies, inicios de sesión ni datos privados de usuarios.

---

## ⚖️ Licencia y Aviso Legal

Este proyecto se distribuye bajo la licencia MIT con fines educativos y de uso personal. Asegúrate de cumplir con los términos de servicio de YouTube y las leyes de derechos de autor aplicables en tu jurisdicción.

