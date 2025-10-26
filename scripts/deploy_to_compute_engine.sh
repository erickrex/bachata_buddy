#!/bin/bash
# Deploy Bachata Buddy to Compute Engine VM
# This script creates a VM and deploys the application

set -e

echo "🚀 Deploying Bachata Buddy to Compute Engine"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Configuration
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
INSTANCE_NAME="bachata-buddy-vm"
ZONE="us-central1-a"
MACHINE_TYPE="n2-standard-4"  # 4 vCPUs, 16GB RAM
DISK_SIZE="50GB"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Instance: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  Machine: $MACHINE_TYPE (4 vCPUs, 16GB RAM)"
echo "  Disk: $DISK_SIZE"
echo ""

# Check if instance already exists
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE &>/dev/null; then
    echo "⚠️  Instance $INSTANCE_NAME already exists"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting existing instance..."
        gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --quiet
    else
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Create firewall rule for HTTP/HTTPS if it doesn't exist
echo "🔥 Setting up firewall rules..."
if ! gcloud compute firewall-rules describe allow-http-https &>/dev/null; then
    gcloud compute firewall-rules create allow-http-https \
        --allow tcp:80,tcp:443,tcp:8080 \
        --source-ranges 0.0.0.0/0 \
        --target-tags http-server,https-server \
        --description "Allow HTTP and HTTPS traffic"
fi

# Create startup script
cat > /tmp/startup-script.sh << 'STARTUP_SCRIPT'
#!/bin/bash
# Startup script for Bachata Buddy VM

set -e

echo "🚀 Starting Bachata Buddy setup..."

# Update system
apt-get update
apt-get upgrade -y

# Install dependencies
echo "📦 Installing system dependencies..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    postgresql-client \
    ffmpeg \
    libpq-dev \
    build-essential \
    curl \
    libsndfile1 \
    libsndfile1-dev \
    libavcodec-extra \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavfilter-dev \
    libavdevice-dev \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libopencv-dev \
    python3-opencv

# Install uv (fast Python package installer)
echo "📦 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.cargo/bin:$PATH"

# Create app directory
mkdir -p /opt/bachata-buddy
cd /opt/bachata-buddy

# Clone repository (or copy files)
echo "📥 Setting up application..."
# Note: In production, you'd clone from git or copy from GCS
# For now, we'll create a placeholder

# Create systemd service
cat > /etc/systemd/system/bachata-buddy.service << 'SERVICE'
[Unit]
Description=Bachata Buddy Django Application
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=/opt/bachata-buddy
Environment="PATH=/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/.cargo/bin/uv run gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 4 --timeout 300 bachata_buddy.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Configure nginx
cat > /etc/nginx/sites-available/bachata-buddy << 'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /static/ {
        alias /opt/bachata-buddy/staticfiles/;
    }

    location /media/ {
        alias /opt/bachata-buddy/media/;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/bachata-buddy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Enable and start services
systemctl daemon-reload
systemctl enable nginx
systemctl restart nginx

echo "✅ Setup complete! Application will start when code is deployed."
STARTUP_SCRIPT

# Get Cloud SQL instance IP for firewall rule
echo "🔍 Getting Cloud SQL instance IP..."
CLOUD_SQL_IP=$(gcloud sql instances describe bachata-db --format="get(ipAddresses[0].ipAddress)" 2>/dev/null || echo "")

if [ -z "$CLOUD_SQL_IP" ]; then
    echo "⚠️  Warning: Could not get Cloud SQL IP. You may need to configure database access manually."
else
    echo "  Cloud SQL IP: $CLOUD_SQL_IP"
fi

# Create the VM
echo "🖥️  Creating Compute Engine instance..."
gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --boot-disk-size=$DISK_SIZE \
    --boot-disk-type=pd-balanced \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --tags=http-server,https-server \
    --metadata-from-file startup-script=/tmp/startup-script.sh \
    --scopes=cloud-platform

# Authorize VM to access Cloud SQL
if [ ! -z "$CLOUD_SQL_IP" ]; then
    echo "🔐 Authorizing VM to access Cloud SQL..."
    VM_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    
    # Add VM IP to Cloud SQL authorized networks
    gcloud sql instances patch bachata-db \
        --authorized-networks=$VM_IP \
        --quiet || echo "⚠️  Could not add VM to Cloud SQL authorized networks. You may need to do this manually."
fi

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready..."
sleep 30

# Get instance IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ VM created successfully!"
echo ""
echo "📋 Instance Details:"
echo "  Name: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  External IP: $EXTERNAL_IP"
echo ""
echo "🌐 Access your application at:"
echo "  http://$EXTERNAL_IP"
echo ""
echo "📝 Next steps:"
echo "  1. Deploy application code:"
echo "     ./scripts/deploy_code_to_vm.sh"
echo ""
echo "  2. SSH into the VM:"
echo "     gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "  3. View logs:"
echo "     gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo journalctl -u bachata-buddy -f'"
echo ""

# Clean up
rm /tmp/startup-script.sh
