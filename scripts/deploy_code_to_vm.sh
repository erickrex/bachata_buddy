#!/bin/bash
# Deploy application code to Compute Engine VM

set -e

echo "📦 Deploying code to Compute Engine VM"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Configuration
INSTANCE_NAME="bachata-buddy-vm"
ZONE="us-central1-a"
APP_DIR="/opt/bachata-buddy"

# Check if instance exists
if ! gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE &>/dev/null; then
    echo "❌ Instance $INSTANCE_NAME not found"
    echo "Run ./scripts/deploy_to_compute_engine.sh first"
    exit 1
fi

# Create deployment package
echo "📦 Creating deployment package..."
TEMP_DIR=$(mktemp -d)
rsync -av \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='data/output' \
    --exclude='data/temp' \
    --exclude='media' \
    --exclude='.pytest_cache' \
    . $TEMP_DIR/

# Copy to VM
echo "📤 Uploading code to VM..."
gcloud compute scp --recurse --zone=$ZONE \
    $TEMP_DIR/* $INSTANCE_NAME:$APP_DIR/

# Copy .env file (use Compute Engine specific config)
echo "📤 Uploading .env file..."
if [ -f .env.compute_engine ]; then
    gcloud compute scp --zone=$ZONE .env.compute_engine $INSTANCE_NAME:$APP_DIR/.env
else
    echo "⚠️  .env.compute_engine not found, using .env"
    gcloud compute scp --zone=$ZONE .env $INSTANCE_NAME:$APP_DIR/.env
fi

# Run deployment commands on VM
echo "🔧 Installing dependencies and starting application..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
set -e
cd $APP_DIR

# Install uv if not present and set PATH
export PATH=\"\$HOME/.local/bin:/root/.cargo/bin:\$PATH\"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH=\"\$HOME/.local/bin:\$PATH\"
fi

# Install Python dependencies (use --break-system-packages for Debian 12)
echo '📦 Installing Python dependencies...'
\$HOME/.local/bin/uv pip install --system --break-system-packages -e .

# Load environment variables
export \$(cat .env | grep -v '^#' | xargs)

# Run migrations
echo '🔄 Running database migrations...'
\$HOME/.local/bin/uv run python manage.py migrate --noinput

# Collect static files
echo '📦 Collecting static files...'
\$HOME/.local/bin/uv run python manage.py collectstatic --noinput

# Create media directories
mkdir -p media/output media/temp media/choreographies media/thumbnails

# Restart application
echo '🔄 Restarting application...'
sudo systemctl restart bachata-buddy

# Check status
echo '✅ Checking application status...'
sudo systemctl status bachata-buddy --no-pager
"

# Clean up
rm -rf $TEMP_DIR

# Get instance IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Application URL: http://$EXTERNAL_IP"
echo ""
echo "📊 View logs:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo journalctl -u bachata-buddy -f'"
echo ""
echo "🔍 SSH into VM:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
