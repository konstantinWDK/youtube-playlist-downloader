FROM python:3.11-slim

# Install ffmpeg and curl for audio extraction and health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create downloads directory with write permissions
RUN mkdir -p downloads && chmod 777 downloads

# Environment variables default
ENV PORT=5006 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_FOLDER=/app/downloads \
    FILE_EXPIRY_SECONDS=7200

EXPOSE 5006

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5006}/health || exit 1

CMD ["sh", "-c", "gunicorn --workers 1 --threads 8 --timeout 600 --bind 0.0.0.0:${PORT:-5006} app:app"]
