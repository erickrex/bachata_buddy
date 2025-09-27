#!/usr/bin/env python3
"""
Clean server startup script that handles port conflicts automatically.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    try:
        # Find process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    pid = int(pid.strip())
                    print(f"🔄 Killing process {pid} on port {port}")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    # Force kill if still running
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated
                except (ValueError, ProcessLookupError):
                    continue
            
            print(f"✅ Cleared port {port}")
            time.sleep(2)  # Give time for port to be released
        else:
            print(f"✅ Port {port} is already free")
            
    except FileNotFoundError:
        # lsof not available, try alternative method
        print("⚠️  lsof not available, trying alternative method...")
        try:
            result = subprocess.run(
                ["netstat", "-tulpn", f"| grep :{port}"],
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(f"⚠️  Port {port} appears to be in use, but couldn't kill process automatically")
        except:
            pass

def main():
    """Start the server with automatic port cleanup."""
    port = 8000
    
    print("🧹 Cleaning up any existing server processes...")
    kill_process_on_port(port)
    
    print("🚀 Starting Bachata Choreography Generator...")
    
    # Set environment variables
    os.environ["SKIP_SYSTEM_VALIDATION"] = "true"
    os.environ["ENVIRONMENT"] = "development"
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        # Start the server using the main module
        subprocess.run([
            sys.executable, "main.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()