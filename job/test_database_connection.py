"""
Test script for database connection utility

This script tests the database connection and update functions
for the video processing job.

Usage:
    python test_database_connection.py
"""
import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import (
    test_connection,
    update_task_status,
    get_task_status,
    close_connection_pool
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test basic database connection"""
    print("\n" + "=" * 80)
    print("Test 1: Database Connection")
    print("=" * 80)
    
    try:
        if test_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def test_update_task_status():
    """Test updating task status"""
    print("\n" + "=" * 80)
    print("Test 2: Update Task Status")
    print("=" * 80)
    
    # Use a test task ID (you'll need to create this task first via the API)
    test_task_id = os.environ.get('TEST_TASK_ID')
    
    if not test_task_id:
        print("⚠️  Skipping test: TEST_TASK_ID environment variable not set")
        print("   To test updates, create a task via the API and set TEST_TASK_ID")
        return True
    
    print(f"Testing with task_id: {test_task_id}")
    
    try:
        # Test 1: Update to running status
        print("\n  Test 2.1: Update to 'running' status...")
        success = update_task_status(
            task_id=test_task_id,
            status='running',
            progress=25,
            stage='downloading',
            message='Downloading audio file...'
        )
        
        if success:
            print("  ✅ Status updated to 'running'")
        else:
            print("  ❌ Failed to update status to 'running'")
            return False
        
        # Test 2: Update with progress
        print("\n  Test 2.2: Update progress to 50%...")
        success = update_task_status(
            task_id=test_task_id,
            status='running',
            progress=50,
            stage='processing',
            message='Processing video...'
        )
        
        if success:
            print("  ✅ Progress updated to 50%")
        else:
            print("  ❌ Failed to update progress")
            return False
        
        # Test 3: Update to completed with result
        print("\n  Test 2.3: Update to 'completed' with result...")
        success = update_task_status(
            task_id=test_task_id,
            status='completed',
            progress=100,
            stage='completed',
            message='Choreography generated successfully!',
            result={
                'video_url': 'gs://bucket/choreographies/2024/11/test.mp4',
                'duration': 180.5,
                'moves_count': 12
            }
        )
        
        if success:
            print("  ✅ Status updated to 'completed' with result")
        else:
            print("  ❌ Failed to update to completed")
            return False
        
        print("\n✅ All update tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Update test error: {e}")
        return False


def test_get_task_status():
    """Test getting task status"""
    print("\n" + "=" * 80)
    print("Test 3: Get Task Status")
    print("=" * 80)
    
    test_task_id = os.environ.get('TEST_TASK_ID')
    
    if not test_task_id:
        print("⚠️  Skipping test: TEST_TASK_ID environment variable not set")
        return True
    
    print(f"Fetching task_id: {test_task_id}")
    
    try:
        task_data = get_task_status(test_task_id)
        
        if task_data:
            print("\n✅ Task data retrieved:")
            print(f"  Task ID: {task_data['task_id']}")
            print(f"  User ID: {task_data['user_id']}")
            print(f"  Status: {task_data['status']}")
            print(f"  Progress: {task_data['progress']}%")
            print(f"  Stage: {task_data['stage']}")
            print(f"  Message: {task_data['message']}")
            if task_data['result']:
                print(f"  Result: {task_data['result']}")
            if task_data['error']:
                print(f"  Error: {task_data['error']}")
            print(f"  Created: {task_data['created_at']}")
            print(f"  Updated: {task_data['updated_at']}")
            return True
        else:
            print("❌ Task not found")
            return False
            
    except Exception as e:
        print(f"❌ Get task status error: {e}")
        return False


def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 80)
    print("Test 4: Error Handling")
    print("=" * 80)
    
    try:
        # Test 1: Invalid status value
        print("\n  Test 4.1: Invalid status value...")
        try:
            update_task_status(
                task_id='test-task-id',
                status='invalid_status',  # Invalid
                progress=0,
                stage='test',
                message='Test'
            )
            print("  ❌ Should have raised ValueError for invalid status")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {e}")
        
        # Test 2: Invalid progress value
        print("\n  Test 4.2: Invalid progress value...")
        try:
            update_task_status(
                task_id='test-task-id',
                status='running',
                progress=150,  # Invalid (> 100)
                stage='test',
                message='Test'
            )
            print("  ❌ Should have raised ValueError for invalid progress")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {e}")
        
        # Test 3: Non-existent task
        print("\n  Test 4.3: Non-existent task...")
        success = update_task_status(
            task_id='non-existent-task-id-12345',
            status='running',
            progress=50,
            stage='test',
            message='Test'
        )
        if not success:
            print("  ✅ Correctly returned False for non-existent task")
        else:
            print("  ❌ Should have returned False for non-existent task")
            return False
        
        print("\n✅ All error handling tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Database Connection Utility Tests")
    print("=" * 80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"DB_HOST: {os.environ.get('DB_HOST', 'not set')}")
    print(f"DB_NAME: {os.environ.get('DB_NAME', 'not set')}")
    print(f"DB_USER: {os.environ.get('DB_USER', 'not set')}")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("Database Connection", test_database_connection()))
    results.append(("Update Task Status", test_update_task_status()))
    results.append(("Get Task Status", test_get_task_status()))
    results.append(("Error Handling", test_error_handling()))
    
    # Close connection pool
    close_connection_pool()
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    # Return exit code
    return 0 if passed == total else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        close_connection_pool()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        close_connection_pool()
        sys.exit(1)
