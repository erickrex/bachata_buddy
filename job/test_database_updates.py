"""
Test script for database updates from the job

This script tests that the job can successfully update task status in the database.
It creates a test task via the API, then tests various database update operations.

Usage:
    python test_database_updates.py
"""
import os
import sys
import logging
import time
import uuid
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


def create_test_task_in_db():
    """
    Create a test task directly in the database for testing
    
    Returns:
        str: Task ID of created task
    """
    print("\n" + "=" * 80)
    print("Setup: Creating Test Task in Database")
    print("=" * 80)
    
    task_id = str(uuid.uuid4())
    
    try:
        from services.database import get_db_cursor
        
        with get_db_cursor() as cursor:
            # Insert a test task
            query = """
                INSERT INTO choreography_tasks (
                    task_id,
                    user_id,
                    status,
                    progress,
                    stage,
                    message,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            cursor.execute(
                query,
                (task_id, 1, 'started', 0, 'initializing', 'Task created for testing')
            )
            
            print(f"✅ Test task created with ID: {task_id}")
            return task_id
            
    except Exception as e:
        print(f"❌ Failed to create test task: {e}")
        return None


def cleanup_test_task(task_id):
    """
    Clean up test task from database
    
    Args:
        task_id: Task ID to delete
    """
    print("\n" + "=" * 80)
    print("Cleanup: Removing Test Task from Database")
    print("=" * 80)
    
    try:
        from services.database import get_db_cursor
        
        with get_db_cursor() as cursor:
            query = "DELETE FROM choreography_tasks WHERE task_id = %s"
            cursor.execute(query, (task_id,))
            
            if cursor.rowcount > 0:
                print(f"✅ Test task {task_id} deleted")
            else:
                print(f"⚠️  Test task {task_id} not found (may have been deleted already)")
                
    except Exception as e:
        print(f"❌ Failed to delete test task: {e}")


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


def test_update_to_running(task_id):
    """Test updating task to running status"""
    print("\n" + "=" * 80)
    print("Test 2: Update Task to 'running' Status")
    print("=" * 80)
    
    try:
        # Update to running
        success = update_task_status(
            task_id=task_id,
            status='running',
            progress=10,
            stage='downloading',
            message='Downloading audio file...'
        )
        
        if not success:
            print("❌ Failed to update task status")
            return False
        
        print("✅ Task status updated to 'running'")
        
        # Verify the update
        task_data = get_task_status(task_id)
        
        if not task_data:
            print("❌ Failed to retrieve task data")
            return False
        
        # Check all fields
        checks = [
            (task_data['status'] == 'running', f"Status: {task_data['status']}"),
            (task_data['progress'] == 10, f"Progress: {task_data['progress']}%"),
            (task_data['stage'] == 'downloading', f"Stage: {task_data['stage']}"),
            (task_data['message'] == 'Downloading audio file...', f"Message: {task_data['message']}"),
        ]
        
        all_passed = True
        for passed, msg in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {msg}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_update_progress(task_id):
    """Test updating task progress"""
    print("\n" + "=" * 80)
    print("Test 3: Update Task Progress")
    print("=" * 80)
    
    try:
        # Simulate progress updates
        progress_stages = [
            (25, 'analyzing', 'Analyzing music features...'),
            (50, 'generating', 'Generating choreography sequence...'),
            (75, 'processing', 'Processing video...'),
        ]
        
        for progress, stage, message in progress_stages:
            success = update_task_status(
                task_id=task_id,
                status='running',
                progress=progress,
                stage=stage,
                message=message
            )
            
            if not success:
                print(f"❌ Failed to update progress to {progress}%")
                return False
            
            # Verify the update
            task_data = get_task_status(task_id)
            
            if not task_data:
                print(f"❌ Failed to retrieve task data at {progress}%")
                return False
            
            if task_data['progress'] != progress:
                print(f"❌ Progress mismatch: expected {progress}, got {task_data['progress']}")
                return False
            
            print(f"✅ Progress updated to {progress}% - {stage}")
            
            # Small delay to simulate real processing
            time.sleep(0.1)
        
        print("\n✅ All progress updates successful")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_update_to_completed(task_id):
    """Test updating task to completed status with result"""
    print("\n" + "=" * 80)
    print("Test 4: Update Task to 'completed' Status with Result")
    print("=" * 80)
    
    try:
        # Update to completed with result
        result_data = {
            'video_url': 'gs://test-bucket/choreographies/2024/11/test-video.mp4',
            'duration': 180.5,
            'moves_count': 12,
            'difficulty': 'intermediate',
            'energy_level': 'high',
            'style': 'romantic'
        }
        
        success = update_task_status(
            task_id=task_id,
            status='completed',
            progress=100,
            stage='completed',
            message='Choreography generated successfully!',
            result=result_data
        )
        
        if not success:
            print("❌ Failed to update task to completed")
            return False
        
        print("✅ Task status updated to 'completed'")
        
        # Verify the update
        task_data = get_task_status(task_id)
        
        if not task_data:
            print("❌ Failed to retrieve task data")
            return False
        
        # Check all fields
        checks = [
            (task_data['status'] == 'completed', f"Status: {task_data['status']}"),
            (task_data['progress'] == 100, f"Progress: {task_data['progress']}%"),
            (task_data['stage'] == 'completed', f"Stage: {task_data['stage']}"),
            (task_data['result'] is not None, "Result: Present"),
            (task_data['result'].get('video_url') == result_data['video_url'], 
             f"Video URL: {task_data['result'].get('video_url') if task_data['result'] else 'None'}"),
            (task_data['result'].get('moves_count') == result_data['moves_count'],
             f"Moves count: {task_data['result'].get('moves_count') if task_data['result'] else 'None'}"),
        ]
        
        all_passed = True
        for passed, msg in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {msg}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_update_to_failed(task_id):
    """Test updating task to failed status with error"""
    print("\n" + "=" * 80)
    print("Test 5: Update Task to 'failed' Status with Error")
    print("=" * 80)
    
    try:
        # First reset to running
        update_task_status(
            task_id=task_id,
            status='running',
            progress=50,
            stage='processing',
            message='Processing...'
        )
        
        # Update to failed with error
        error_message = "Failed to process video: FFmpeg encoding error"
        
        success = update_task_status(
            task_id=task_id,
            status='failed',
            progress=50,
            stage='processing',
            message='Video processing failed',
            error=error_message
        )
        
        if not success:
            print("❌ Failed to update task to failed")
            return False
        
        print("✅ Task status updated to 'failed'")
        
        # Verify the update
        task_data = get_task_status(task_id)
        
        if not task_data:
            print("❌ Failed to retrieve task data")
            return False
        
        # Check all fields
        checks = [
            (task_data['status'] == 'failed', f"Status: {task_data['status']}"),
            (task_data['error'] is not None, "Error: Present"),
            (task_data['error'] == error_message, f"Error message: {task_data['error']}"),
        ]
        
        all_passed = True
        for passed, msg in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {msg}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_concurrent_updates(task_id):
    """Test multiple rapid updates (simulating real job behavior)"""
    print("\n" + "=" * 80)
    print("Test 6: Concurrent/Rapid Updates")
    print("=" * 80)
    
    try:
        # Simulate rapid updates like a real job would do
        updates = [
            ('running', 10, 'downloading', 'Downloading audio...'),
            ('running', 15, 'downloading', 'Audio downloaded'),
            ('running', 20, 'analyzing', 'Analyzing music...'),
            ('running', 30, 'analyzing', 'Music analysis complete'),
            ('running', 35, 'querying', 'Querying move database...'),
            ('running', 45, 'generating', 'Generating choreography...'),
            ('running', 60, 'processing', 'Processing videos...'),
            ('running', 80, 'processing', 'Combining videos...'),
            ('running', 90, 'uploading', 'Uploading result...'),
            ('completed', 100, 'completed', 'Done!'),
        ]
        
        for status, progress, stage, message in updates:
            success = update_task_status(
                task_id=task_id,
                status=status,
                progress=progress,
                stage=stage,
                message=message
            )
            
            if not success:
                print(f"❌ Failed to update at {progress}%")
                return False
            
            # Very small delay to simulate rapid updates
            time.sleep(0.05)
        
        # Verify final state
        task_data = get_task_status(task_id)
        
        if not task_data:
            print("❌ Failed to retrieve final task data")
            return False
        
        if task_data['status'] != 'completed' or task_data['progress'] != 100:
            print(f"❌ Final state incorrect: {task_data['status']} at {task_data['progress']}%")
            return False
        
        print(f"✅ All {len(updates)} rapid updates successful")
        print(f"  Final state: {task_data['status']} at {task_data['progress']}%")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_error_handling():
    """Test error handling for invalid inputs"""
    print("\n" + "=" * 80)
    print("Test 7: Error Handling")
    print("=" * 80)
    
    try:
        # Test 1: Invalid status value
        print("\n  Test 7.1: Invalid status value...")
        try:
            update_task_status(
                task_id='test-task-id',
                status='invalid_status',
                progress=0,
                stage='test',
                message='Test'
            )
            print("  ❌ Should have raised ValueError for invalid status")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {str(e)[:50]}...")
        
        # Test 2: Invalid progress value (negative)
        print("\n  Test 7.2: Invalid progress value (negative)...")
        try:
            update_task_status(
                task_id='test-task-id',
                status='running',
                progress=-10,
                stage='test',
                message='Test'
            )
            print("  ❌ Should have raised ValueError for negative progress")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {str(e)[:50]}...")
        
        # Test 3: Invalid progress value (> 100)
        print("\n  Test 7.3: Invalid progress value (> 100)...")
        try:
            update_task_status(
                task_id='test-task-id',
                status='running',
                progress=150,
                stage='test',
                message='Test'
            )
            print("  ❌ Should have raised ValueError for progress > 100")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {str(e)[:50]}...")
        
        # Test 4: Non-existent task
        print("\n  Test 7.4: Non-existent task...")
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
    """Run all database update tests"""
    print("\n" + "=" * 80)
    print("Job Database Update Tests")
    print("=" * 80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"DB_HOST: {os.environ.get('DB_HOST', 'not set')}")
    print(f"DB_NAME: {os.environ.get('DB_NAME', 'not set')}")
    print(f"DB_USER: {os.environ.get('DB_USER', 'not set')}")
    print("=" * 80)
    
    results = []
    test_task_id = None
    
    try:
        # Test 1: Database connection
        results.append(("Database Connection", test_database_connection()))
        
        if not results[0][1]:
            print("\n❌ Database connection failed. Cannot proceed with tests.")
            return 1
        
        # Create test task
        test_task_id = create_test_task_in_db()
        
        if not test_task_id:
            print("\n❌ Failed to create test task. Cannot proceed with tests.")
            return 1
        
        # Run update tests
        results.append(("Update to Running", test_update_to_running(test_task_id)))
        results.append(("Update Progress", test_update_progress(test_task_id)))
        results.append(("Update to Completed", test_update_to_completed(test_task_id)))
        results.append(("Update to Failed", test_update_to_failed(test_task_id)))
        results.append(("Concurrent Updates", test_concurrent_updates(test_task_id)))
        results.append(("Error Handling", test_error_handling()))
        
    finally:
        # Cleanup
        if test_task_id:
            cleanup_test_task(test_task_id)
        
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
    
    if passed == total:
        print("\n🎉 All tests passed! Database updates from job are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
    
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
        import traceback
        traceback.print_exc()
        close_connection_pool()
        sys.exit(1)
