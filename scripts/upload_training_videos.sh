#!/bin/bash
# Upload training videos to Google Cloud Storage

set -e

echo "📹 Uploading training videos to GCS..."

# Configuration
BUCKET_NAME=${GCS_BUCKET_NAME:-"bachata-buddy-bucket"}
SOURCE_DIR="data/Bachata_steps"
DEST_PATH="gs://${BUCKET_NAME}/Bachata_steps"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Count local files
LOCAL_COUNT=$(find $SOURCE_DIR -name "*.mp4" | wc -l)
echo "📊 Found $LOCAL_COUNT video files locally"

# Upload with parallel processing
echo "☁️  Uploading to $DEST_PATH..."
gsutil -m cp -r ${SOURCE_DIR}/* ${DEST_PATH}/

# Verify upload
echo "✅ Verifying upload..."
REMOTE_COUNT=$(gsutil ls -r ${DEST_PATH}/**/*.mp4 | wc -l)
echo "📊 Found $REMOTE_COUNT video files in GCS"

if [ "$LOCAL_COUNT" -eq "$REMOTE_COUNT" ]; then
    echo "✅ All videos uploaded successfully!"
else
    echo "⚠️  Upload count mismatch: local=$LOCAL_COUNT, remote=$REMOTE_COUNT"
    exit 1
fi

# Show storage usage
echo "💾 Storage usage:"
gsutil du -sh ${DEST_PATH}

echo "✅ Training videos uploaded!"
