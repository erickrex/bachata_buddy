#!/usr/bin/env python3
"""
Execute the REAL production pipeline for Path 1 and Path 2.
This is NOT a test - it actually generates videos.
"""

import requests
import time
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8001/api"
OUTPUT_FILE = f"pipeline_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def log(message):
    """Log to both console and file."""
    print(message)
    with open(OUTPUT_FILE, 'a') as f:
        f.write(message + '\n')

def main():
    log("="*80)
    log("BACHATA BUDDY - PRODUCTION PIPELINE EXECUTION")
    log("="*80)
    log(f"Started: {datetime.now()}")
    log("")
    
    # Step 1: Authenticate
    log("[1/7] Authenticating...")
    auth_response = requests.post(
        f"{API_BASE}/auth/login/",
        json={"username": "e2etest_weighted", "password": "testpass123"}
    )
    
    if auth_response.status_code != 200:
        log(f"ERROR: Authentication failed: {auth_response.status_code}")
        log(auth_response.text)
        return 1
    
    token = auth_response.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    log("✓ Authenticated")
    log("")
    
    # Step 2: Trigger Path 1
    log("[2/7] Triggering Path 1: Song Template Generation")
    log("  Song ID: 1 (Eso_es_amor by Jiory)")
    log("  Difficulty: intermediate, Energy: medium, Style: romantic")
    
    path1_response = requests.post(
        f"{API_BASE}/choreography/generate-from-song/",
        headers=headers,
        json={
            "song_id": 1,
            "difficulty": "intermediate",
            "energy_level": "medium",
            "style": "romantic"
        }
    )
    
    if path1_response.status_code != 202:
        log(f"ERROR: Path 1 failed: {path1_response.status_code}")
        log(path1_response.text)
        path1_task_id = None
    else:
        path1_data = path1_response.json()
        path1_task_id = path1_data['task_id']
        log(f"✓ Path 1 triggered: {path1_task_id}")
    log("")
    
    # Step 3: Trigger Path 2
    log("[3/7] Triggering Path 2: AI Natural Language Generation")
    log("  Query: 'Create a romantic intermediate bachata with smooth flowing moves'")
    
    path2_response = requests.post(
        f"{API_BASE}/choreography/generate-with-ai/",
        headers=headers,
        json={"query": "Create a romantic intermediate bachata with smooth flowing moves"}
    )
    
    if path2_response.status_code != 202:
        log(f"ERROR: Path 2 failed: {path2_response.status_code}")
        log(path2_response.text)
        path2_task_id = None
    else:
        path2_data = path2_response.json()
        path2_task_id = path2_data['task_id']
        log(f"✓ Path 2 triggered: {path2_task_id}")
    log("")
    
    # Step 4: Poll Path 1
    path1_video = None
    if path1_task_id:
        log(f"[4/7] Polling Path 1 status: {path1_task_id}")
        log("  (This may take several minutes...)")
        
        for attempt in range(240):  # 20 minutes max
            time.sleep(5)
            status_response = requests.get(
                f"{API_BASE}/choreography/tasks/{path1_task_id}/",
                headers=headers
            )
            
            if status_response.status_code == 200:
                data = status_response.json()
                status = data['status']
                progress = data.get('progress', 0)
                
                if attempt % 10 == 0:
                    log(f"  [{attempt*5}s] Status: {status}, Progress: {progress}%")
                
                if status == 'completed':
                    path1_video = data['result']['video_url']
                    log(f"✓ Path 1 completed: {path1_video}")
                    break
                elif status == 'failed':
                    log(f"✗ Path 1 failed: {data.get('error', 'Unknown')}")
                    break
        else:
            log("✗ Path 1 timed out")
    else:
        log("[4/7] Skipping Path 1 (not triggered)")
    log("")
    
    # Step 5: Poll Path 2
    path2_video = None
    if path2_task_id:
        log(f"[5/7] Polling Path 2 status: {path2_task_id}")
        log("  (This may take several minutes...)")
        
        for attempt in range(240):  # 20 minutes max
            time.sleep(5)
            status_response = requests.get(
                f"{API_BASE}/choreography/tasks/{path2_task_id}/",
                headers=headers
            )
            
            if status_response.status_code == 200:
                data = status_response.json()
                status = data['status']
                progress = data.get('progress', 0)
                
                if attempt % 10 == 0:
                    log(f"  [{attempt*5}s] Status: {status}, Progress: {progress}%")
                
                if status == 'completed':
                    path2_video = data['result']['video_url']
                    log(f"✓ Path 2 completed: {path2_video}")
                    break
                elif status == 'failed':
                    log(f"✗ Path 2 failed: {data.get('error', 'Unknown')}")
                    break
        else:
            log("✗ Path 2 timed out")
    else:
        log("[5/7] Skipping Path 2 (not triggered)")
    log("")
    
    # Step 6: Summary
    log("[6/7] RESULTS SUMMARY")
    log("="*80)
    
    if path1_task_id:
        log(f"\nPATH 1 (Song Template):")
        log(f"  Task ID: {path1_task_id}")
        log(f"  Status: {'✓ SUCCESS' if path1_video else '✗ FAILED'}")
        if path1_video:
            log(f"  Video: storage/{path1_video}")
            log(f"  Blueprint: Database table 'choreography_blueprint'")
            log(f"  Query: docker exec bachata_db psql -U postgres -d bachata_db -c \"SELECT * FROM choreography_blueprint WHERE task_id='{path1_task_id}';\"")
    
    if path2_task_id:
        log(f"\nPATH 2 (AI Generation):")
        log(f"  Task ID: {path2_task_id}")
        log(f"  Status: {'✓ SUCCESS' if path2_video else '✗ FAILED'}")
        if path2_video:
            log(f"  Video: storage/{path2_video}")
            log(f"  Blueprint: Database table 'choreography_blueprint'")
            log(f"  Query: docker exec bachata_db psql -U postgres -d bachata_db -c \"SELECT * FROM choreography_blueprint WHERE task_id='{path2_task_id}';\"")
    
    log("")
    log("[7/7] OUTPUT LOCATIONS")
    log("="*80)
    log("\nBLUEPRINTS:")
    log("  Location: PostgreSQL database 'bachata_db'")
    log("  Table: choreography_blueprint")
    log("  Access: docker exec bachata_db psql -U postgres -d bachata_db")
    log("")
    log("VIDEOS:")
    log("  Location: storage/choreographies/")
    log("  Format: choreography_<task_id>.mp4")
    log("  List: ls -lh storage/choreographies/")
    log("")
    log(f"Execution log saved to: {OUTPUT_FILE}")
    log(f"Completed: {datetime.now()}")
    log("="*80)
    
    return 0 if (path1_video and path2_video) else 1

if __name__ == '__main__':
    sys.exit(main())
