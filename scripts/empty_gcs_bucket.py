#!/usr/bin/env python3
"""
Empty GCS bucket (delete all files in training_videos folder)

Usage:
    python scripts/empty_gcs_bucket.py --bucket_name your-bucket-name
"""

import argparse
from google.cloud import storage


def empty_bucket(bucket_name: str, prefix: str = "training_videos/"):
    """Delete all files with given prefix from bucket."""
    
    print(f"🗑️  Emptying gs://{bucket_name}/{prefix}")
    print("=" * 80)
    
    # Initialize client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # List all blobs with prefix
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        print(f"✅ Bucket is already empty (no files with prefix '{prefix}')")
        return
    
    print(f"Found {len(blobs)} files to delete")
    
    # Delete all blobs
    for i, blob in enumerate(blobs, 1):
        print(f"[{i}/{len(blobs)}] Deleting: {blob.name}")
        blob.delete()
    
    print("=" * 80)
    print(f"✅ Deleted {len(blobs)} files from gs://{bucket_name}/{prefix}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Empty GCS bucket")
    parser.add_argument("--bucket_name", required=True, help="GCS bucket name")
    parser.add_argument("--prefix", default="training_videos/", help="Prefix to delete (default: training_videos/)")
    
    args = parser.parse_args()
    
    # Confirm
    response = input(f"⚠️  Delete all files in gs://{args.bucket_name}/{args.prefix}? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled")
        exit(0)
    
    empty_bucket(args.bucket_name, args.prefix)
