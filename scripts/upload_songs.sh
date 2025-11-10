#!/bin/bash
# Upload songs to Google Cloud Storage

set -e

echo "🎵 Uploading songs to GCS..."

# Configuration
BUCKET_NAME=${GCS_BUCKET_NAME:-"bachata-buddy-bucket"}
SOURCE_DIR="data/songs"
DEST_PATH="gs://${BUCKET_NAME}/songs"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Count local files
LOCAL_COUNT=$(find $SOURCE_DIR -name "*.mp3" | wc -l)
echo "📊 Found $LOCAL_COUNT song files locally"

# Upload with parallel processing
echo "☁️  Uploading to $DEST_PATH..."
gsutil -m cp ${SOURCE_DIR}/*.mp3 ${DEST_PATH}/

# Verify upload
echo "✅ Verifying upload..."
REMOTE_COUNT=$(gsutil ls ${DEST_PATH}/*.mp3 | wc -l)
echo "📊 Found $REMOTE_COUNT song files in GCS"

if [ "$LOCAL_COUNT" -eq "$REMOTE_COUNT" ]; then
    echo "✅ All songs uploaded successfully!"
else
    echo "⚠️  Upload count mismatch: local=$LOCAL_COUNT, remote=$REMOTE_COUNT"
    exit 1
fi

# Show storage usage
echo "💾 Storage usage:"
gsutil du -sh ${DEST_PATH}

echo "✅ Songs uploaded!"
