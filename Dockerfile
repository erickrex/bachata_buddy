# Production Dockerfile for Bachata Choreography Generator
# Simplified with YOLOv8-Pose (no complex dependencies!)

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

# Install all dependencies (including YOLOv8)
# Much simpler than MMPose - no special handling needed!
RUN uv pip install --system --no-cache -e .

# Copy application code
COPY . .

# YOLOv8 models download automatically on first use - no manual download needed!

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
