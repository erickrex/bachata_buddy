#!/usr/bin/env python3
"""
Test script to verify frontend-backend communication works correctly.
"""

import asyncio
import aiohttp
import json
import time
import sys
from pathlib import Path

async def test_choreography_flow():
    """Test the complete choreography generation flow."""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Frontend-Backend Communication")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health check
        print("1. Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"   ✅ Health check passed: {health['status']}")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False
        
        # Test 2: Start choreography generation
        print("2. Starting choreography generation...")
        try:
            request_data = {
                "youtube_url": "data/songs/Angel.mp3",
                "difficulty": "intermediate",
                "quality_mode": "balanced"
            }
            
            async with session.post(
                f"{base_url}/api/choreography",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result["task_id"]
                    print(f"   ✅ Generation started: {task_id}")
                else:
                    error = await response.text()
                    print(f"   ❌ Generation failed to start: {response.status} - {error}")
                    return False
        except Exception as e:
            print(f"   ❌ Generation start error: {e}")
            return False
        
        # Test 3: Poll for completion
        print("3. Polling for completion...")
        max_polls = 60  # 2 minutes max
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                async with session.get(
                    f"{base_url}/api/task/{task_id}",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        status = await response.json()
                        progress = status.get("progress", 0)
                        message = status.get("message", "Processing...")
                        
                        print(f"   📊 Progress: {progress}% - {message}")
                        
                        if status["status"] == "completed":
                            print("   ✅ Generation completed!")
                            result_data = status["result"]
                            
                            # Test 4: Check if video file exists
                            video_filename = result_data.get("video_filename")
                            if video_filename:
                                print(f"4. Testing video access: {video_filename}")
                                async with session.get(
                                    f"{base_url}/api/video/{video_filename}",
                                    timeout=aiohttp.ClientTimeout(total=10)
                                ) as video_response:
                                    if video_response.status == 200:
                                        content_length = video_response.headers.get('content-length', '0')
                                        print(f"   ✅ Video accessible: {content_length} bytes")
                                        return True
                                    else:
                                        print(f"   ❌ Video not accessible: {video_response.status}")
                                        return False
                            else:
                                print("   ⚠️  No video filename in result")
                                return True  # Generation worked, just no video filename
                        
                        elif status["status"] == "failed":
                            error_msg = status.get("error", "Unknown error")
                            print(f"   ❌ Generation failed: {error_msg}")
                            return False
                        
                        # Continue polling
                        poll_count += 1
                        await asyncio.sleep(2)
                    
                    else:
                        print(f"   ❌ Polling failed: {response.status}")
                        poll_count += 1
                        await asyncio.sleep(2)
                        
            except asyncio.TimeoutError:
                print(f"   ⚠️  Polling timeout (attempt {poll_count + 1})")
                poll_count += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f"   ❌ Polling error: {e}")
                poll_count += 1
                await asyncio.sleep(2)
        
        print("   ❌ Polling timed out after 2 minutes")
        return False

async def main():
    """Run the test."""
    print("🎵 Bachata Choreography Generator - Frontend-Backend Test")
    print("Make sure the server is running on http://localhost:8000")
    print()
    
    success = await test_choreography_flow()
    
    print()
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Frontend-backend communication is working.")
        sys.exit(0)
    else:
        print("💥 Tests failed. Check the server logs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())