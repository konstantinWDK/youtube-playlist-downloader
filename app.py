import os
import time
import threading
import uuid
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp

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
        'service': 'youtube-downloader',
        'active_jobs': len(jobs)
    }), 200


@app.route('/download', methods=['POST'])
def start_download():
    payload = request.get_json(silent=True) or {}
    urls = payload.get('urls', [])
    if not urls or not isinstance(urls, list):
        return jsonify({'error': 'No se han proporcionado URLs válidas.'}), 400

    all_urls = []
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            url = str(url).strip()
            if not url:
                continue
            try:
                info = ydl.extract_info(url, download=False)
                if info and 'entries' in info and info['entries']:
                    # Playlist
                    for entry in info['entries']:
                        if entry:
                            v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            v_title = entry.get('title') or "Video en lista"
                            all_urls.append({'url': v_url, 'title': v_title})
                else:
                    v_title = (info.get('title') if info else None) or "Cargando audio..."
                    all_urls.append({'url': url, 'title': v_title})
            except Exception as e:
                print(f"Error extrayendo info para {url}: {e}")
                all_urls.append({'url': url, 'title': url})

    if not all_urls:
        return jsonify({'error': 'No se encontraron videos procesables.'}), 400

    job_ids = []
    urls_to_download = []
    now = time.time()

    with jobs_lock:
        for item in all_urls:
            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                'status': 'queued',
                'url': item['url'],
                'title': item['title'],
                'created_at': now,
                'filename': None,
                'error': None
            }
            job_ids.append(job_id)
            urls_to_download.append(item['url'])

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
    return send_from_directory(
        app.config['DOWNLOAD_FOLDER'],
        safe_filename,
        as_attachment=True
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5006))
    app.run(host='0.0.0.0', port=port)
