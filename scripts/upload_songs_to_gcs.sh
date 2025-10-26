#!/bin/bash
# Upload song files to Google Cloud Storage

set -e

echo "🎵 Uploading songs to Google Cloud Storage"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Load .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

export $(cat .env | grep -v '^#' | xargs)

# Check if bucket name is set
if [ -z "$GCS_BUCKET_NAME" ]; then
    echo "❌ Error: GCS_BUCKET_NAME not set in .env"
    exit 1
fi

SONGS_DIR="data/songs"
BUCKET_PATH="gs://${GCS_BUCKET_NAME}/songs"

# Check if songs directory exists
if [ ! -d "$SONGS_DIR" ]; then
    echo "❌ Error: Songs directory not found: $SONGS_DIR"
    exit 1
fi

# Count songs
SONG_COUNT=$(ls -1 "$SONGS_DIR"/*.mp3 2>/dev/null | wc -l | tr -d ' ')

if [ "$SONG_COUNT" -eq 0 ]; then
    echo "❌ Error: No MP3 files found in $SONGS_DIR"
    exit 1
fi

echo "📋 Configuration:"
echo "  Bucket: $GCS_BUCKET_NAME"
echo "  Source: $SONGS_DIR"
echo "  Destination: $BUCKET_PATH"
echo "  Songs to upload: $SONG_COUNT"
echo ""

# List songs
echo "🎵 Songs found:"
ls -1 "$SONGS_DIR"/*.mp3 | xargs -n1 basename
echo ""

read -p "Continue with upload? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upload cancelled"
    exit 1
fi

echo ""
echo "📤 Uploading songs..."
echo ""

# Upload all songs with proper content type
gsutil -m cp -r "$SONGS_DIR/*.mp3" "$BUCKET_PATH/" 2>&1 || \
    gsutil -m rsync -r "$SONGS_DIR" "$BUCKET_PATH"

# Set content type for all MP3 files
echo ""
echo "🔧 Setting content type for MP3 files..."
gsutil -m setmeta -h "Content-Type:audio/mpeg" "$BUCKET_PATH/*.mp3"

# Make files publicly readable (optional - remove if you want private files)
echo ""
echo "🔓 Making files publicly readable..."
gsutil -m acl ch -u AllUsers:R "$BUCKET_PATH/*.mp3"

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Upload complete!"
echo ""
echo "📊 Verify upload:"
echo "  gsutil ls -lh $BUCKET_PATH/"
echo ""
echo "🌐 Files are accessible at:"
echo "  https://storage.googleapis.com/${GCS_BUCKET_NAME}/songs/[filename].mp3"
echo ""
