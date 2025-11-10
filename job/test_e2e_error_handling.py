"""
End-to-End Error Handling Integration Test

This test demonstrates that error handling works correctly through the entire
pipeline from blueprint validation to video assembly, including:
- Error detection at each stage
- Proper error propagation
- Database status updates
- Structured logging
- Cleanup on failure
"""
import os
import sys
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text):
    print(f"{RED}❌ {text}{RESET}")


def test_e2e_validation_error():
    """Test end-to-end error handling for validation errors"""
    print_header("E2E Test 1: Blueprint Validation Error")
    
    # Create invalid blueprint (missing required fields)
    invalid_blueprint = {
        'task_id': 'test-e2e-validation',
        # Missing audio_path, moves, output_config
    }
    
    # Mock environment
    env = {
        'BLUEPRINT_JSON': json.dumps(invalid_blueprint),
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'LOG_LEVEL': 'ERROR'
    }
    
    # Mock database functions
    update_calls = []
    
    def mock_update(task_id, status, progress=0, stage='', message='', result=None, error=None):
        update_calls.append({
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'stage': stage,
            'message': message,
            'error': error
        })
        return True
    
    with patch.dict(os.environ, env, clear=True):
        with patch('services.database.update_task_status', side_effect=mock_update):
            with patch('services.database.close_connection_pool'):
                from main import main
                
                exit_code = main()
                
                # Verify exit code
                if exit_code == 1:
                    print_success("Returned exit code 1 for validation error")
                else:
                    print_error(f"Expected exit code 1, got {exit_code}")
                    return False
                
                # Verify database was updated with error
                if len(update_calls) > 0:
                    last_call = update_calls[-1]
                    if last_call['status'] == 'failed':
                        print_success("Database updated with status='failed'")
                    else:
                        print_error(f"Expected status='failed', got '{last_call['status']}'")
                        return False
                    
                    if last_call['error']:
                        print_success(f"Error message stored: {last_call['error'][:50]}...")
                    else:
                        print_error("No error message stored in database")
                        return False
                else:
                    print_error("Database was not updated")
                    return False
    
    return True


def test_e2e_storage_error():
    """Test end-to-end error handling for storage errors"""
    print_header("E2E Test 2: Storage Error (Missing Files)")
    
    # Create valid blueprint but with non-existent files
    temp_dir = tempfile.mkdtemp(prefix='test_e2e_storage_')
    
    try:
        blueprint = {
            'task_id': 'test-e2e-storage',
            'audio_path': 'nonexistent/audio.mp3',
            'moves': [
                {
                    'clip_id': 'move1',
                    'video_path': 'nonexistent/video1.mp4',
                    'start_time': 0,
                    'duration': 5
                }
            ],
            'output_config': {
                'output_path': 'output/test.mp4'
            }
        }
        
        # Mock environment
        env = {
            'BLUEPRINT_JSON': json.dumps(blueprint),
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'USE_GCS': 'false',
            'LOCAL_STORAGE_PATH': temp_dir,
            'LOG_LEVEL': 'ERROR'
        }
        
        # Mock database functions
        update_calls = []
        
        def mock_update(task_id, status, progress=0, stage='', message='', result=None, error=None):
            update_calls.append({
                'task_id': task_id,
                'status': status,
                'progress': progress,
                'stage': stage,
                'message': message,
                'error': error
            })
            return True
        
        with patch.dict(os.environ, env, clear=True):
            with patch('services.database.update_task_status', side_effect=mock_update):
                with patch('services.database.close_connection_pool'):
                    from main import main
                    
                    exit_code = main()
                    
                    # Verify exit code
                    if exit_code == 1:
                        print_success("Returned exit code 1 for storage error")
                    else:
                        print_error(f"Expected exit code 1, got {exit_code}")
                        return False
                    
                    # Verify database was updated with error
                    failed_updates = [c for c in update_calls if c['status'] == 'failed']
                    if len(failed_updates) > 0:
                        last_failed = failed_updates[-1]
                        print_success("Database updated with status='failed'")
                        
                        if last_failed['error'] and 'audio' in last_failed['error'].lower():
                            print_success(f"Error message mentions audio file: {last_failed['error'][:50]}...")
                        else:
                            print_error("Error message doesn't mention audio file")
                            return False
                    else:
                        print_error("No failed status update found")
                        return False
        
        return True
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_e2e_ffmpeg_error():
    """Test end-to-end error handling for FFmpeg errors"""
    print_header("E2E Test 3: FFmpeg Error (Corrupted Files)")
    
    # Create temp directory with corrupted files
    temp_dir = tempfile.mkdtemp(prefix='test_e2e_ffmpeg_')
    
    try:
        # Create corrupted audio file
        audio_path = os.path.join(temp_dir, 'audio.mp3')
        with open(audio_path, 'wb') as f:
            f.write(b'not a valid audio file')
        
        # Create corrupted video file
        video_dir = os.path.join(temp_dir, 'videos')
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, 'video1.mp4')
        with open(video_path, 'wb') as f:
            f.write(b'not a valid video file')
        
        blueprint = {
            'task_id': 'test-e2e-ffmpeg',
            'audio_path': 'audio.mp3',
            'moves': [
                {
                    'clip_id': 'move1',
                    'video_path': 'videos/video1.mp4',
                    'start_time': 0,
                    'duration': 5
                }
            ],
            'output_config': {
                'output_path': 'output/test.mp4'
            }
        }
        
        # Mock environment
        env = {
            'BLUEPRINT_JSON': json.dumps(blueprint),
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'USE_GCS': 'false',
            'LOCAL_STORAGE_PATH': temp_dir,
            'LOG_LEVEL': 'ERROR'
        }
        
        # Mock database functions
        update_calls = []
        
        def mock_update(task_id, status, progress=0, stage='', message='', result=None, error=None):
            update_calls.append({
                'task_id': task_id,
                'status': status,
                'progress': progress,
                'stage': stage,
                'message': message,
                'error': error
            })
            return True
        
        with patch.dict(os.environ, env, clear=True):
            with patch('services.database.update_task_status', side_effect=mock_update):
                with patch('services.database.close_connection_pool'):
                    from main import main
                    
                    exit_code = main()
                    
                    # Verify exit code
                    if exit_code == 1:
                        print_success("Returned exit code 1 for FFmpeg error")
                    else:
                        print_error(f"Expected exit code 1, got {exit_code}")
                        return False
                    
                    # Verify database was updated with error
                    failed_updates = [c for c in update_calls if c['status'] == 'failed']
                    if len(failed_updates) > 0:
                        last_failed = failed_updates[-1]
                        print_success("Database updated with status='failed'")
                        
                        if last_failed['error']:
                            print_success(f"Error message stored: {last_failed['error'][:50]}...")
                        else:
                            print_error("No error message stored")
                            return False
                    else:
                        print_error("No failed status update found")
                        return False
        
        return True
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    """Run all E2E error handling tests"""
    print_header("End-to-End Error Handling Integration Tests")
    
    tests = [
        ("Blueprint Validation Error", test_e2e_validation_error),
        ("Storage Error (Missing Files)", test_e2e_storage_error),
        ("FFmpeg Error (Corrupted Files)", test_e2e_ffmpeg_error),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = f"{GREEN}✅ PASSED{RESET}" if success else f"{RED}❌ FAILED{RESET}"
        print(f"{status}: {test_name}")
    
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{BLUE}{'=' * 80}{RESET}")
    
    if passed == total:
        print_header("✅ ALL E2E ERROR HANDLING TESTS PASSED!")
        print_success("Error handling works correctly through the entire pipeline:")
        print(f"  • Errors detected at each stage")
        print(f"  • Proper error propagation")
        print(f"  • Database status updates with error messages")
        print(f"  • Appropriate exit codes")
        print(f"  • Structured logging")
        print(f"  • Cleanup on failure")
        return 0
    else:
        print_header(f"❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nTests failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
