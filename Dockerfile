# Production Dockerfile for Bachata Choreography Generator
# Handles MMPose/chumpy dependency issues correctly

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    libopencv-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install core dependencies (excluding mmpose group)
# This avoids the chumpy build issue
RUN uv pip install --system --no-cache -e .

# Install MMPose stack via mim (handles chumpy correctly)
# mim uses pip internally with proper build isolation workarounds
RUN uv pip install --system --no-cache openmim && \
    mim install --no-cache-dir mmengine && \
    mim install --no-cache-dir "mmcv>=2.0.0" && \
    mim install --no-cache-dir "mmdet>=3.0.0" && \
    mim install --no-cache-dir "mmpose>=1.0.0"

# Copy application code
COPY . .

# Download MMPose model checkpoints
RUN python scripts/download_mmpose_models.py

# Collect static files (Django)
RUN python manage.py collectstatic --noinput || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=cloud

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run gunicorn
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 0 bachata_buddy.wsgi:application
