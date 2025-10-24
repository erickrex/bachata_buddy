# Production Dockerfile for Bachata Choreography Generator
# Uses YOLOv8-Pose for couple detection and Gemini for AI features

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for YOLOv8, OpenCV, and audio/video processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (optimized for Cloud Run)
RUN uv pip install --system --no-cache -e .

# Copy application code
COPY . .

# Collect static files (Django)
RUN python manage.py collectstatic --noinput || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=cloud

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5)" || exit 1

# Run gunicorn
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 0 bachata_buddy.wsgi:application
