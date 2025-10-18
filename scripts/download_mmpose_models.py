#!/usr/bin/env python3
"""
Script to download MMPose model checkpoints using mim.

This script downloads the required models for:
1. Person detection (Faster R-CNN)
2. Body pose estimation (HRNet-W48)
3. Hand detection (HRNet-W48 for hands)

All models are configured for CPU-only inference.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {description} failed")
        print(f"Error output: {e.stderr}")
        return False


def main():
    """Download all required MMPose models."""
    
    # Create checkpoints directory
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    
    print("\n" + "="*60)
    print("MMPose Model Download Script")
    print("="*60)
    print(f"Models will be downloaded to: {checkpoint_dir.absolute()}")
    print("\nThis script will download:")
    print("  1. Faster R-CNN (person detection) - ~160MB")
    print("  2. HRNet-W48 (body pose) - ~250MB")
    print("  3. HRNet-W48 (hand pose) - ~250MB")
    print(f"  Total: ~660MB")
    print("\nNote: All models are CPU-only (no CUDA required)")
    
    # Check if mim is installed
    try:
        subprocess.run(["mim", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n✗ Error: 'mim' (OpenMMLab Installer) is not installed")
        print("\nPlease install it first:")
        print("  pip install openmim")
        sys.exit(1)
    
    success = True
    
    # 1. Download MMDetection (for person detection)
    print("\n" + "="*60)
    print("Step 1/3: Installing MMDetection")
    print("="*60)
    if not run_command(
        ["mim", "install", "mmdet"],
        "Installing MMDetection package"
    ):
        success = False
    
    # Download Faster R-CNN model
    if not run_command(
        ["mim", "download", "mmdet", 
         "--config", "faster_rcnn_r50_fpn_1x_coco",
         "--dest", str(checkpoint_dir)],
        "Downloading Faster R-CNN model for person detection"
    ):
        success = False
    
    # 2. Download MMPose (for pose estimation)
    print("\n" + "="*60)
    print("Step 2/3: Installing MMPose")
    print("="*60)
    if not run_command(
        ["mim", "install", "mmpose"],
        "Installing MMPose package"
    ):
        success = False
    
    # Download HRNet-W48 body pose model
    if not run_command(
        ["mim", "download", "mmpose",
         "--config", "td-hm_hrnet-w48_8xb32-210e_coco-384x288",
         "--dest", str(checkpoint_dir)],
        "Downloading HRNet-W48 model for body pose estimation"
    ):
        success = False
    
    # 3. Download hand detection model
    print("\n" + "="*60)
    print("Step 3/3: Downloading Hand Detection Model")
    print("="*60)
    if not run_command(
        ["mim", "download", "mmpose",
         "--config", "td-hm_hrnetv2-w18_8xb64-210e_onehand10k-256x256",
         "--dest", str(checkpoint_dir)],
        "Downloading HRNet model for hand detection"
    ):
        success = False
    
    # Summary
    print("\n" + "="*60)
    print("Download Summary")
    print("="*60)
    
    if success:
        print("✓ All models downloaded successfully!")
        print(f"\nModel checkpoints are located in: {checkpoint_dir.absolute()}")
        print("\nExpected files:")
        print("  - faster_rcnn_r50_fpn_1x_coco.py")
        print("  - faster_rcnn_r50_fpn_1x_coco_*.pth")
        print("  - td-hm_hrnet-w48_8xb32-210e_coco-384x288.py")
        print("  - hrnet_w48_coco_384x288-*.pth")
        print("  - td-hm_hrnetv2-w18_8xb64-210e_onehand10k-256x256.py")
        print("  - hrnetv2_w18_onehand10k_256x256-*.pth")
        print("\nYou can now run the embedding generation pipeline!")
    else:
        print("✗ Some downloads failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  1. Ensure you have internet connectivity")
        print("  2. Try running: pip install --upgrade openmim mmcv mmdet mmpose")
        print("  3. Check MMPose documentation: https://mmpose.readthedocs.io/")
        sys.exit(1)


if __name__ == "__main__":
    main()
