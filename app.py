import os
import time
import threading
import uuid
import io
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, render_template, send_from_directory, jsonify, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp

# --- LOGGING SETUP ---
LOG_DIR = os.path.abspath('logs')
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

app = Flask(__name__)

# Apply ProxyFix for reverse proxy support (Coolify, Traefik, Caddy, Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DOWNLOAD_FOLDER = os.environ.get('DOWNLOAD_FOLDER', 'downloads')
app.config['DOWNLOAD_FOLDER'] = os.path.abspath(DOWNLOAD_FOLDER)
FILE_EXPIRY_SECONDS = int(os.environ.get('FILE_EXPIRY_SECONDS', 7200))  # Default: 2 hours

# Ensure download folder exists
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

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
    }

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
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = str(e)


def process_batch(items, job_ids):
    for i, url in enumerate(items):
        download_video(url, job_ids[i])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'youtube-playlist-downloader',
        'active_jobs': len(jobs)
    }), 200


@app.route('/info', methods=['POST'])
def get_info():
    payload = request.get_json(silent=True) or {}
    url = payload.get('url')
    if not url:
        return jsonify({'error': 'No se proporcionó una URL.'}), 400

    logger.info(f"User requested info for URL: {url}")
    
    all_videos = []
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}

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
def start_download():
    payload = request.get_json(silent=True) or {}
    videos = payload.get('videos', [])
    if not videos or not isinstance(videos, list):
        return jsonify({'error': 'No se han proporcionado videos válidos.'}), 400

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
