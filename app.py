import os
import time
import threading
import uuid
import io
import logging
import re
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, render_template, send_from_directory, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp

import sys
import glob

# Modo de funcionamiento de la aplicación (True = pública/landing, False = escritorio local)
WEB_MODE = os.environ.get('WEB_MODE', 'true').lower() == 'true'

# Añadir rutas de Homebrew al PATH (respaldo en macOS)
if sys.platform == 'darwin':
    os.environ["PATH"] += os.pathsep + os.pathsep.join([
        '/opt/homebrew/bin',
        '/opt/homebrew/sbin',
        '/usr/local/bin',
        '/usr/bin'
    ])

if getattr(sys, 'frozen', False):
    if sys.platform == 'darwin':
        LOG_DIR = os.path.join(os.path.expanduser("~"), 'Library', 'Logs', 'YouTubePlaylistDownloader')
        ffmpeg_bin = glob.glob(os.path.join(sys._MEIPASS, 'static_ffmpeg', 'bin', 'darwin_*'))
    elif sys.platform == 'win32':
        LOG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser("~")), 'YouTubePlaylistDownloader', 'Logs')
        ffmpeg_bin = glob.glob(os.path.join(sys._MEIPASS, 'static_ffmpeg', 'bin', 'win32*')) or glob.glob(os.path.join(sys._MEIPASS, 'static_ffmpeg', 'bin', '*'))
    else:
        LOG_DIR = os.path.join(os.path.expanduser("~"), '.local', 'share', 'YouTubePlaylistDownloader', 'logs')
        ffmpeg_bin = glob.glob(os.path.join(sys._MEIPASS, 'static_ffmpeg', 'bin', 'linux*'))

    if ffmpeg_bin:
        os.environ["PATH"] = ffmpeg_bin[0] + os.pathsep + os.environ["PATH"]
else:
    LOG_DIR = os.path.abspath('logs')
    try:
        from static_ffmpeg import add_paths
        add_paths()
    except ImportError:
        pass
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, 'downloads.log')
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger("yt-downloader")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
# ---------------------

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"]
)

# Apply ProxyFix for reverse proxy support (Coolify, Traefik, Caddy, Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DOWNLOAD_FOLDER = os.environ.get('DOWNLOAD_FOLDER', 'downloads')
app.config['DOWNLOAD_FOLDER'] = os.path.abspath(DOWNLOAD_FOLDER)
FILE_EXPIRY_SECONDS = int(os.environ.get('FILE_EXPIRY_SECONDS', 7200))  # Default: 2 hours

from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify(error=str(e.description)), e.code
    logger.exception("Unhandled exception:")
    return jsonify(error="Error interno del servidor."), 500

# Ensure download folder exists
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

COOKIE_FILE_PATH = '/tmp/yt_cookies.txt'
if os.environ.get('YOUTUBE_COOKIES'):
    try:
        with open(COOKIE_FILE_PATH, 'w') as f:
            # Reemplazar retornos literales por reales por si se introducen mal en Coolify
            f.write(os.environ.get('YOUTUBE_COOKIES').replace('\\n', '\n'))
        logger.info("YouTube cookies file created from environment variable.")
    except Exception as e:
        logger.error(f"Failed to write YouTube cookies: {e}")

# Global status dictionary to track progress
jobs = {}
jobs_lock = threading.Lock()


def cleanup_worker():
    """Background thread to remove files and jobs older than FILE_EXPIRY_SECONDS."""
    while True:
        try:
            time.sleep(600)  # Run cleanup every 10 minutes
            now = time.time()
            folder = app.config['DOWNLOAD_FOLDER']
            
            if os.path.exists(folder):
                for fname in os.listdir(folder):
                    if fname == '.gitkeep':
                        continue
                    fpath = os.path.join(folder, fname)
                    if os.path.isfile(fpath):
                        if (now - os.path.getmtime(fpath)) > FILE_EXPIRY_SECONDS:
                            try:
                                os.remove(fpath)
                            except OSError:
                                pass

            with jobs_lock:
                cutoff = now - FILE_EXPIRY_SECONDS
                expired_keys = [
                    jid for jid, jdata in jobs.items()
                    if jdata.get('created_at', 0) < cutoff
                ]
                for jid in expired_keys:
                    jobs.pop(jid, None)
        except Exception as e:
            print(f"[Cleanup Error] {e}")


# Start background cleanup thread
cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()


def download_video(url, job_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'client': ['android', 'mweb', 'ios']}},
    }
    
    if os.path.exists(COOKIE_FILE_PATH):
        ydl_opts['cookiefile'] = COOKIE_FILE_PATH

    try:
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'processing'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Calculate the converted mp3 filename
            raw_filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(os.path.basename(raw_filename))[0]
            mp3_filename = f"{base_name}.mp3"
            
            with jobs_lock:
                if job_id in jobs:
                    jobs[job_id]['status'] = 'completed'
                    jobs[job_id]['filename'] = mp3_filename
                    jobs[job_id]['title'] = info.get('title', jobs[job_id].get('title', 'Audio'))
    except Exception as e:
        logger.error(f"Error crítico en yt-dlp descargando {url}: {str(e)}")
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = str(e)


def process_batch(items, job_ids):
    for i, url in enumerate(items):
        download_video(url, job_ids[i])


@app.route('/')
def index():
    return render_template('index.html', web_mode=WEB_MODE)


@app.route('/health')
@limiter.exempt
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'youtube-playlist-downloader',
        'active_jobs': len(jobs)
    }), 200


@app.route('/info', methods=['POST'])
@limiter.limit("10 per minute")
def get_info():
    if WEB_MODE:
        return jsonify({'error': 'La API de descarga está deshabilitada en la versión pública web.'}), 403

    payload = request.get_json(silent=True) or {}
    url = payload.get('url')
    
    if not url or not isinstance(url, str):
        return jsonify({'error': 'No se proporcionó una URL.'}), 400
        
    # Anti-SSRF: Solo permitir dominios de YouTube
    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/.*', url):
        logger.warning(f"Rejected invalid URL attempt: {url}")
        return jsonify({'error': 'URL inválida o no permitida. Solo YouTube.'}), 400

    logger.info(f"User requested info for URL: {url}")
    
    all_videos = []
    ydl_opts = {
        'extract_flat': True, 
        'quiet': True, 
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'client': ['android', 'mweb', 'ios']}}
    }
    
    if os.path.exists(COOKIE_FILE_PATH):
        ydl_opts['cookiefile'] = COOKIE_FILE_PATH

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if info and 'entries' in info and info['entries']:
                # It's a playlist
                for entry in info['entries']:
                    if entry:
                        v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        v_title = entry.get('title') or "Video en lista"
                        all_videos.append({'url': v_url, 'title': v_title})
            else:
                # Single video
                v_title = (info.get('title') if info else None) or "Audio a descargar"
                v_url = info.get('webpage_url') or url
                all_videos.append({'url': v_url, 'title': v_title})
        except Exception as e:
            logger.error(f"Error extracting info for {url}: {e}")
            return jsonify({'error': 'No se pudo analizar la URL.'}), 500

    if not all_videos:
        return jsonify({'error': 'No se encontraron videos procesables.'}), 400

    return jsonify({'videos': all_videos})


@app.route('/download', methods=['POST'])
@limiter.limit("5 per minute")
def start_download():
    if WEB_MODE:
        return jsonify({'error': 'La API de descarga está deshabilitada en la versión pública web.'}), 403
        
    # Logueamos la petición cruda para depurar el 400
    logger.info(f"Incoming /download request. Headers: {request.headers}")
    
    payload = request.get_json(silent=True)
    if payload is None:
        logger.error(f"Fallo al parsear JSON. Data cruda: {request.get_data(as_text=True)}")
        payload = {}

    videos = payload.get('videos', [])
    if not videos or not isinstance(videos, list):
        logger.error(f"Payload de videos inválido o vacío. Payload parseado: {payload}")
        return jsonify({'error': 'No se han proporcionado videos válidos.'}), 400

    if len(videos) > 50:
        logger.warning(f"User tried to download {len(videos)} videos (limit 50).")
        return jsonify({'error': 'Por seguridad, el límite máximo es de 50 descargas simultáneas.'}), 400

    logger.info(f"User started download for {len(videos)} videos")

    job_ids = []
    urls_to_download = []
    now = time.time()

    with jobs_lock:
        for item in videos:
            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                'status': 'queued',
                'url': item.get('url'),
                'title': item.get('title', 'Unknown Title'),
                'created_at': now,
                'filename': None,
                'error': None
            }
            job_ids.append(job_id)
            urls_to_download.append(item.get('url'))

    thread = threading.Thread(target=process_batch, args=(urls_to_download, job_ids), daemon=True)
    thread.start()

    return jsonify({'job_ids': job_ids})


@app.route('/status/<job_id>')
def get_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Tarea no encontrada'}), 404
    return jsonify(job)




@app.route('/config/download-folder', methods=['GET'])
def get_download_folder():
    return jsonify({'folder': app.config['DOWNLOAD_FOLDER']})

@app.route('/config/change-folder', methods=['POST'])
def change_folder():
    try:
        import webview
        if len(webview.windows) > 0:
            window = webview.windows[0]
            result = window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                app.config['DOWNLOAD_FOLDER'] = result[0]
    except Exception as e:
        print(e)
    return jsonify({'folder': app.config['DOWNLOAD_FOLDER']})

@app.route('/download-app/mac', methods=['GET'])
def download_mac_app():
    return send_from_directory(os.path.join(app.root_path, 'releases'), 'YouTubePlaylistDownloader.dmg', as_attachment=True)

@app.route('/download-app/windows', methods=['GET'])
def download_windows_app():
    return send_from_directory(os.path.join(app.root_path, 'releases'), 'YouTubePlaylistDownloader.exe', as_attachment=True)

@app.route('/open-folder', methods=['POST'])
def open_folder():
    import subprocess
    folder = app.config['DOWNLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    if sys.platform == 'darwin':
        subprocess.run(['open', folder])
    elif sys.platform == 'win32':
        os.startfile(folder)
    else:
        subprocess.run(['xdg-open', folder])
    return jsonify({'status': 'ok'})

@app.route('/show-file', methods=['POST'])
def show_file():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename'}), 400
        
    filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    import subprocess
    if sys.platform == 'darwin' and os.path.exists(filepath):
        subprocess.run(['open', '-R', filepath])
    elif sys.platform == 'win32' and os.path.exists(filepath):
        subprocess.run(['explorer', f'/select,{os.path.normpath(filepath)}'])
    elif os.path.exists(filepath):
        subprocess.run(['xdg-open', os.path.dirname(filepath)])
    return jsonify({'status': 'ok'})


@app.route('/files/<path:filename>')
def download_file(filename):
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Archivo no encontrado'}), 404
        
    try:
        # Leer el archivo a la memoria (RAM)
        with open(filepath, 'rb') as f:
            file_data = f.read()
            
        # Borrar el archivo físico del disco inmediatamente
        os.remove(filepath)
        logger.info(f"File {safe_filename} downloaded and deleted from disk.")
        
        # Enviar el archivo al usuario desde la memoria
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=safe_filename,
            mimetype='audio/mpeg'
        )
    except Exception as e:
        logger.error(f"Error serving file {safe_filename}: {e}")
        return jsonify({'error': 'Error al procesar la descarga'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5006))
    app.run(host='0.0.0.0', port=port)
