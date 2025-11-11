#!/bin/bash
# Build and push GPU-enabled Docker image for Cloud Run Jobs

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-europe-west1}"
IMAGE_NAME="video-processor-gpu"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Full image path
IMAGE_PATH="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building GPU-enabled job Docker image..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_PATH}"
echo ""

# Build the image from the bachata_buddy directory (parent of job/)
cd ..
echo "Building image with job/Dockerfile.gpu..."
docker build -f job/Dockerfile.gpu -t ${IMAGE_PATH} .

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
    echo "Deploy to Cloud Run Jobs with:"
    echo "gcloud run jobs create video-processor \\"
    echo "  --image ${IMAGE_PATH} \\"
    echo "  --region ${REGION} \\"
    echo "  --memory 16Gi \\"
    echo "  --cpu 4 \\"
    echo "  --gpu 1 \\"
    echo "  --gpu-type nvidia-l4 \\"
    echo "  --set-env-vars FFMPEG_USE_NVENC=true \\"
    echo "  --max-retries 3"
else
    echo "Skipping push. Image available locally as: ${IMAGE_PATH}"
fi
