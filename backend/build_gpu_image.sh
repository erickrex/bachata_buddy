#!/bin/bash
# Build and push GPU-enabled Docker image for Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-europe-west1}"
IMAGE_NAME="bachata-api-gpu"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Full image path
IMAGE_PATH="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building GPU-enabled Docker image..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_PATH}"
echo ""

# Build the image
echo "Building image with Dockerfile.gpu..."
docker build -f Dockerfile.gpu -t ${IMAGE_PATH} .

echo ""
echo "Image built successfully: ${IMAGE_PATH}"
echo ""

# Ask if user wants to push
read -p "Push image to Google Container Registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Pushing image to GCR..."
    docker push ${IMAGE_PATH}
    echo ""
    echo "Image pushed successfully!"
    echo ""
    echo "Deploy to Cloud Run with:"
    echo "gcloud run deploy bachata-api \\"
    echo "  --image ${IMAGE_PATH} \\"
    echo "  --region ${REGION} \\"
    echo "  --platform managed \\"
    echo "  --memory 16Gi \\"
    echo "  --cpu 4 \\"
    echo "  --gpu 1 \\"
    echo "  --gpu-type nvidia-l4 \\"
    echo "  --set-env-vars USE_GPU=true,FAISS_USE_GPU=true,AUDIO_USE_GPU=true"
else
    echo "Skipping push. Image available locally as: ${IMAGE_PATH}"
fi
