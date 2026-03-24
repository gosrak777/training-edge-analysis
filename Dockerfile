# TrainingEdge — Intervals.icu Edition
# Optimized for NAS deployment (Synology/QNAP)

FROM python:3.10-slim

LABEL maintainer="Mars"
LABEL description="TrainingEdge with Intervals.icu + Oura Ring integration"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install \
    fastapi>=0.104 \
    uvicorn[standard]>=0.24 \
    jinja2>=3.1 \
    requests>=2.31 \
    python-multipart>=0.0.6 \
    fitparse>=1.2.0 \
    python-dotenv>=1.0.0 \
    apscheduler>=3.10.0

# Copy application code
COPY engine/ ./engine/
COPY api/ ./api/
COPY web/ ./web/
COPY scripts/ ./scripts/
COPY docker-entrypoint.sh ./

# Create necessary directories
RUN mkdir -p /app/state /app/reports /var/log/trainingedge

# Set up cron for scheduled sync
COPY crontab /etc/cron.d/trainingedge
RUN chmod 0644 /etc/cron.d/trainingedge && \
    crontab /etc/cron.d/trainingedge

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
