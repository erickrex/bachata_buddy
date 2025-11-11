# Dockerfile for Blueprint-Based Video Assembly Job
# This lightweight job assembles videos from pre-computed blueprints
# All intelligence (audio analysis, move selection, AI) happens in the API/backend

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies
# - ffmpeg: Required for video assembly and concatenation
# - libpq-dev: Required for PostgreSQL client (psycopg2-binary)
# - gcc: Required for compiling psycopg2-binary
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install minimal Python dependencies
# Only what's needed for: video assembly, database updates, storage access, config
RUN uv pip install --system --no-cache \
    "psycopg2-binary>=2.9" \
    "google-cloud-storage>=2.10" \
    "python-dotenv>=1.0"

# Copy job code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the blueprint-based video assembly job
CMD ["python", "src/main.py"]
