# Production Dockerfile for Django REST API
# Optimized for Cloud Run deployment with multi-stage build

# Stage 1: Build stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml .
COPY README.md* ./

# Install dependencies using UV (system-wide for production)
RUN uv pip install --system --no-cache .

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV in runtime stage (for running commands)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder (system-wide installation)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and create staticfiles directory
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles

# Switch to non-root user
USER appuser

# Collect static files using UV
RUN uv run python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/health || exit 1

# Expose port
EXPOSE 8080

# Run with gunicorn
# - bind to PORT environment variable (Cloud Run requirement)
# - 1 worker with 8 threads (optimal for Cloud Run)
# - timeout 0 for long-running requests
# - access log to stdout for Cloud Logging
# - error log to stderr for Cloud Logging
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 0 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    api.wsgi:application
