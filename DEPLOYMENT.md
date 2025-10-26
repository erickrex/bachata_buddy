# 🚀 Deployment Guide

This guide covers deploying Bachata Buddy to production using Google Cloud Platform.

---

## 📋 Table of Contents

1. [Infrastructure Overview](#infrastructure-overview)
2. [Prerequisites](#prerequisites)
3. [Google Compute Engine Deployment](#google-compute-engine-deployment)
4. [Secrets Management](#secrets-management)
5. [Database Setup](#database-setup)
6. [Elasticsearch Configuration](#elasticsearch-configuration)
7. [Docker Build Verification](#docker-build-verification)
8. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🏗️ Infrastructure Overview

Bachata Buddy runs on Google Cloud Platform with the following architecture:

- **Compute Engine**: e2-medium instance (2 vCPU, 4GB RAM) for Django application
- **Cloud SQL**: PostgreSQL database for user data and choreographies
- **Elasticsearch Serverless**: Vector similarity search for embeddings
- **Secret Manager**: Secure storage for API keys and credentials
- **Local Disk Storage**: Training videos (81MB) and songs (78MB) for fast access

**Why Compute Engine over Cloud Run?**
- Local storage for 10x faster video access (no GCS download latency)
- Better performance for FFmpeg video processing
- Lower costs for video-heavy workloads
- Full control over system resources

---

## 📦 Prerequisites

Before deploying, ensure you have:

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Required APIs enabled**:
   ```bash
   gcloud services enable compute.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```
4. **Docker** installed locally for testing

---

## 🖥️ Google Compute Engine Deployment

### Quick Deploy (Automated)

```bash
# Deploy everything with one command
chmod +x scripts/deploy_to_compute_engine.sh
./scripts/deploy_to_compute_engine.sh
```

### Manual Deployment Steps

#### 1. Create Compute Engine Instance

```bash
gcloud compute instances create bachata-buddy-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker $USER
  '
```

#### 2. Configure Firewall Rules

```bash
# Allow HTTP traffic
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --target-tags http-server \
  --description="Allow HTTP traffic"

# Allow HTTPS traffic
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --target-tags https-server \
  --description="Allow HTTPS traffic"

# Allow Django dev server (optional, for testing)
gcloud compute firewall-rules create allow-django \
  --allow tcp:8000 \
  --target-tags http-server \
  --description="Allow Django dev server"
```

#### 3. SSH into Instance and Setup

```bash
# SSH into the instance
gcloud compute ssh bachata-buddy-vm --zone=us-central1-a

# Clone repository
git clone YOUR_REPO_URL
cd bachata_buddy

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Install system dependencies
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1

# Install Python dependencies
uv sync

# Create .env file (see Secrets Management section)
nano .env
```

#### 4. Upload Training Data

```bash
# From your local machine, upload training videos and songs
gcloud compute scp --recurse data/Bachata_steps bachata-buddy-vm:~/bachata_buddy/data/ --zone=us-central1-a
gcloud compute scp --recurse data/songs bachata-buddy-vm:~/bachata_buddy/data/ --zone=us-central1-a
gcloud compute scp data/bachata_annotations.json bachata-buddy-vm:~/bachata_buddy/data/ --zone=us-central1-a
```

#### 5. Run Django Application

```bash
# On the VM
cd ~/bachata_buddy

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Start server (production)
uv run gunicorn bachata_buddy.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile -

# Or use systemd service (recommended)
sudo nano /etc/systemd/system/bachata-buddy.service
```

#### 6. Systemd Service Configuration

Create `/etc/systemd/system/bachata-buddy.service`:

```ini
[Unit]
Description=Bachata Buddy Django Application
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/bachata_buddy
Environment="PATH=/home/YOUR_USERNAME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/YOUR_USERNAME/.cargo/bin/uv run gunicorn bachata_buddy.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bachata-buddy
sudo systemctl start bachata-buddy
sudo systemctl status bachata-buddy
```

---

## 🔐 Secrets Management

### Setup Secrets in Google Secret Manager

```bash
# Run the automated setup script
chmod +x scripts/setup_secrets.sh
./scripts/setup_secrets.sh
```

### Manual Secret Creation

```bash
# Django secret key
echo -n "your-secret-key-here" | gcloud secrets create DJANGO_SECRET_KEY --data-file=-

# Database password
echo -n "your-db-password" | gcloud secrets create DB_PASSWORD --data-file=-

# Elasticsearch API key
echo -n "your-es-api-key" | gcloud secrets create ELASTICSEARCH_API_KEY --data-file=-

# Gemini API key
echo -n "your-gemini-api-key" | gcloud secrets create GOOGLE_API_KEY --data-file=-

# Grant access to Compute Engine service account
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding DJANGO_SECRET_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Environment Variables (.env)

Create `.env` file on the VM:

```bash
# Environment
ENVIRONMENT=cloud

# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name

# Database (Cloud SQL)
DB_HOST=10.x.x.x  # Private IP of Cloud SQL instance
DB_NAME=bachata_buddy
DB_USER=postgres
DB_PORT=5432

# Elasticsearch Serverless
ELASTICSEARCH_HOST=your-es-host.es.us-central1.gcp.elastic-cloud.com
ELASTICSEARCH_PORT=443
ELASTICSEARCH_INDEX=bachata_move_embeddings

# Django
ALLOWED_HOSTS=your-vm-external-ip,your-domain.com
DJANGO_DEBUG=False

# YOLOv8
YOLOV8_MODEL=yolov8n-pose.pt
YOLOV8_CONFIDENCE=0.3
```

**Sensitive values** (loaded from Secret Manager at runtime):
- `DJANGO_SECRET_KEY`
- `DB_PASSWORD`
- `ELASTICSEARCH_API_KEY`
- `GOOGLE_API_KEY`

See **[SECRETS_MANAGEMENT_GUIDE.md](SECRETS_MANAGEMENT_GUIDE.md)** for detailed instructions.

---

## 🗄️ Database Setup

### Create Cloud SQL Instance

```bash
gcloud sql instances create bachata-buddy-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_ROOT_PASSWORD \
  --storage-type=SSD \
  --storage-size=10GB
```

### Create Database and User

```bash
# Connect to Cloud SQL
gcloud sql connect bachata-buddy-db --user=postgres

# In psql:
CREATE DATABASE bachata_buddy;
CREATE USER bachata_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE bachata_buddy TO bachata_user;
\q
```

### Configure Private IP (Recommended)

```bash
# Enable private IP for Cloud SQL
gcloud sql instances patch bachata-buddy-db \
  --network=default \
  --no-assign-ip
```

### Run Migrations

```bash
# On the VM
cd ~/bachata_buddy
uv run python manage.py migrate
```

---

## 🔍 Elasticsearch Configuration

### Option 1: Elasticsearch Serverless (Recommended)

1. **Create Elasticsearch Serverless Project** at https://cloud.elastic.co/
2. **Get connection details**:
   - Host: `your-project.es.region.gcp.elastic-cloud.com`
   - API Key: Generate from Kibana
3. **Create index** (automatic on first embedding generation)
4. **Configure in .env**:
   ```bash
   ELASTICSEARCH_HOST=your-project.es.region.gcp.elastic-cloud.com
   ELASTICSEARCH_PORT=443
   ELASTICSEARCH_API_KEY=your-api-key
   ```

### Option 2: Self-Hosted Elasticsearch (Development)

```bash
# On the VM
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:9.1.0

# Configure in .env
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
```

### Generate Embeddings

```bash
# On the VM
cd ~/bachata_buddy

# Backup existing embeddings (if any)
uv run python scripts/backup_embeddings.py --environment cloud

# Generate new embeddings
uv run python scripts/generate_embeddings.py \
  --video_dir data/Bachata_steps \
  --annotations data/bachata_annotations.json \
  --environment cloud

# Processing time: ~4-6 minutes for 38 videos
```

See **[README_ELASTICSEARCH.md](core/services/README_ELASTICSEARCH.md)** for detailed Elasticsearch configuration.

---

## 🐳 Docker Build Verification

Before deploying, verify the Docker build works correctly:

```bash
# Test Docker build locally
cd bachata_buddy
chmod +x scripts/test_docker_build.sh
./scripts/test_docker_build.sh
```

This script verifies:
- ✅ Docker image builds successfully
- ✅ System dependencies installed (ffmpeg, libsndfile)
- ✅ Python libraries importable (librosa, cv2)
- ✅ Health check endpoint responds
- ✅ Container is ready for deployment

### Manual Docker Build

```bash
# Build image
docker build -t bachata-buddy:latest .

# Run container
docker run -d -p 8000:8000 \
  --env-file .env \
  --name bachata-buddy \
  bachata-buddy:latest

# Check logs
docker logs bachata-buddy

# Test health endpoint
curl http://localhost:8000/health/
```

---

## 📊 Monitoring & Maintenance

### View Application Logs

```bash
# Systemd service logs
sudo journalctl -u bachata-buddy -f

# Or if running directly
tail -f /var/log/bachata-buddy.log
```

### Monitor Resource Usage

```bash
# CPU and memory
htop

# Disk usage
df -h

# Check running processes
ps aux | grep gunicorn
```

### Backup Embeddings

```bash
# Regular backups (run weekly)
cd ~/bachata_buddy
uv run python scripts/backup_embeddings.py --environment cloud

# Download backup to local machine
gcloud compute scp bachata-buddy-vm:~/bachata_buddy/data/embeddings_backup.json ./backups/ --zone=us-central1-a
```

### Update Application

```bash
# SSH into VM
gcloud compute ssh bachata-buddy-vm --zone=us-central1-a

# Pull latest code
cd ~/bachata_buddy
git pull origin main

# Install new dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Restart service
sudo systemctl restart bachata-buddy
```

### Performance Optimization

**Current Production Performance:**
- Video generation: 40-50 seconds
- Elasticsearch retrieval: <10ms
- Recommendation engine: <50ms
- Memory usage: <500MB

**Optimization Tips:**
- Use local disk for training videos (10x faster than GCS)
- Enable connection pooling for Elasticsearch
- Use gunicorn with 2-4 workers
- Monitor memory usage and adjust instance size if needed

---

## 🔧 Troubleshooting

### Common Issues

**1. Video generation fails**
```bash
# Check FFmpeg installation
ffmpeg -version

# Check video file permissions
ls -la data/Bachata_steps/

# Check disk space
df -h
```

**2. Elasticsearch connection errors**
```bash
# Test connection
curl -X GET "https://your-es-host:443/_cluster/health" \
  -H "Authorization: ApiKey YOUR_API_KEY"

# Check environment variables
cat .env | grep ELASTICSEARCH
```

**3. Database connection errors**
```bash
# Test Cloud SQL connection
psql -h DB_HOST -U DB_USER -d DB_NAME

# Check private IP connectivity
ping DB_HOST
```

**4. Out of memory errors**
```bash
# Check memory usage
free -h

# Upgrade instance type
gcloud compute instances set-machine-type bachata-buddy-vm \
  --machine-type=e2-standard-2 \
  --zone=us-central1-a
```

### Getting Help

- Check logs: `sudo journalctl -u bachata-buddy -f`
- Review documentation in `/docs` folder
- Open an issue on GitHub

---

## 📚 Additional Resources

- [SECRETS_MANAGEMENT_GUIDE.md](SECRETS_MANAGEMENT_GUIDE.md) - Detailed secrets setup
- [README_ELASTICSEARCH.md](core/services/README_ELASTICSEARCH.md) - Elasticsearch configuration
- [COMPUTE_ENGINE_DEPLOYMENT.md](COMPUTE_ENGINE_DEPLOYMENT.md) - Detailed deployment guide
- [VIDEO_GENERATION_FIXES.md](VIDEO_GENERATION_FIXES.md) - Video generation troubleshooting

---

## 🎯 Production Checklist

Before going live, ensure:

- [ ] All secrets configured in Secret Manager
- [ ] Cloud SQL instance created and accessible
- [ ] Elasticsearch Serverless project created
- [ ] Training videos and songs uploaded to VM
- [ ] Embeddings generated and validated
- [ ] Firewall rules configured
- [ ] SSL certificate installed (for HTTPS)
- [ ] Domain name configured
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Django DEBUG=False in production
- [ ] ALLOWED_HOSTS configured correctly
- [ ] Static files collected and served
- [ ] Systemd service enabled and running

---

**Status:** ✅ Fully operational on Google Compute Engine

**Last Updated:** October 26, 2025
