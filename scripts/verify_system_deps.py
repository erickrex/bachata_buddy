#!/usr/bin/env python3
"""
Verify that all required system dependencies are available in the container.
Run this inside the Docker container to ensure ffmpeg, libsndfile, etc. are installed.
"""

import subprocess
import sys


def check_command(cmd: str, name: str) -> bool:
    """Check if a command is available."""
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # ffmpeg outputs to stderr, so check both stdout and stderr
            output = result.stdout or result.stderr
            version_info = output.split('\n')[0] if output else 'Unknown'
            print(f"✅ {name}: Available")
            print(f"   {version_info}")
            return True
        else:
            print(f"❌ {name}: Command failed (exit code {result.returncode})")
            return False
    except FileNotFoundError:
        print(f"❌ {name}: Not found")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False


def check_library(lib_name: str, import_name: str = None) -> bool:
    """Check if a Python library can be imported."""
    import_name = import_name or lib_name
    try:
        __import__(import_name)
        print(f"✅ {lib_name}: Importable")
        return True
    except ImportError as e:
        print(f"❌ {lib_name}: Import failed - {e}")
        return False


def main():
    print("🔍 Verifying System Dependencies for Bachata Buddy")
    print("=" * 60)
    
    all_ok = True
    
    # Check system commands
    print("\n📦 System Commands:")
    all_ok &= check_command("ffmpeg", "FFmpeg")
    all_ok &= check_command("python", "Python")
    
    # Check Python libraries that depend on system packages
    print("\n🐍 Python Libraries (system-dependent):")
    all_ok &= check_library("librosa", "librosa")
    all_ok &= check_library("cv2", "cv2")
    all_ok &= check_library("yt_dlp", "yt_dlp")
    all_ok &= check_library("ultralytics", "ultralytics")
    
    # Check critical Django/app libraries
    print("\n🌐 Application Libraries:")
    all_ok &= check_library("django", "django")
    all_ok &= check_library("elasticsearch", "elasticsearch")
    all_ok &= check_library("google.generativeai", "google.generativeai")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All dependencies verified successfully!")
        return 0
    else:
        print("❌ Some dependencies are missing or failed to load")
        return 1


if __name__ == "__main__":
    sys.exit(main())
