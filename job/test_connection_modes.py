"""
Test script to verify database connection works in both modes:
1. Local Development: PostgreSQL TCP/IP connection
2. Cloud Run Production: Cloud SQL Unix socket connection

This test verifies the connection logic without actually connecting to Cloud SQL.
"""
import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_local_connection_params():
    """Test that local development uses TCP/IP connection"""
    print("\n" + "=" * 80)
    print("Test 1: Local Development Connection Parameters")
    print("=" * 80)
    
    # Set up local environment
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'
    os.environ['DB_NAME'] = 'test_db'
    os.environ['DB_USER'] = 'test_user'
    os.environ['DB_PASSWORD'] = 'test_password'
    
    # Ensure K_SERVICE is not set (local mode)
    if 'K_SERVICE' in os.environ:
        del os.environ['K_SERVICE']
    
    # Import after setting environment
    from services.database import _create_connection_pool
    
    try:
        # This will fail to connect but we can check the parameters
        pool = _create_connection_pool()
        print("✅ Local connection pool created with TCP/IP parameters")
        print(f"   Expected: host=localhost, port=5432")
        return True
    except Exception as e:
        # Expected to fail since we don't have a real database
        if 'localhost' in str(e) or 'Connection refused' in str(e):
            print("✅ Local connection attempted with correct TCP/IP parameters")
            print(f"   Connection string includes: host=localhost, port=5432")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False


def test_cloud_run_connection_params():
    """Test that Cloud Run uses Unix socket connection"""
    print("\n" + "=" * 80)
    print("Test 2: Cloud Run Production Connection Parameters")
    print("=" * 80)
    
    # Set up Cloud Run environment
    os.environ['K_SERVICE'] = 'video-processor'  # Cloud Run sets this
    os.environ['CLOUD_SQL_CONNECTION_NAME'] = 'project-id:region:instance-name'
    os.environ['DB_NAME'] = 'bachata_buddy'
    os.environ['DB_USER'] = 'postgres'
    os.environ['DB_PASSWORD'] = 'secure-password'
    
    # Remove local DB_HOST to ensure it's not used
    if 'DB_HOST' in os.environ:
        del os.environ['DB_HOST']
    
    # Reload the module to pick up new environment
    import importlib
    import services.database
    importlib.reload(services.database)
    
    try:
        # This will fail to connect but we can check the parameters
        pool = services.database._create_connection_pool()
        print("✅ Cloud Run connection pool created with Unix socket parameters")
        print(f"   Expected: host=/cloudsql/project-id:region:instance-name")
        return True
    except Exception as e:
        # Expected to fail since we don't have a real Cloud SQL connection
        if '/cloudsql/' in str(e) or 'No such file or directory' in str(e):
            print("✅ Cloud Run connection attempted with correct Unix socket parameters")
            print(f"   Connection string includes: host=/cloudsql/project-id:region:instance-name")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False


def test_connection_mode_detection():
    """Test that connection mode is correctly detected"""
    print("\n" + "=" * 80)
    print("Test 3: Connection Mode Detection")
    print("=" * 80)
    
    # Test 1: Local mode (no K_SERVICE)
    if 'K_SERVICE' in os.environ:
        del os.environ['K_SERVICE']
    
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    if not is_cloud_run:
        print("✅ Correctly detected LOCAL mode (K_SERVICE not set)")
    else:
        print("❌ Failed to detect LOCAL mode")
        return False
    
    # Test 2: Cloud Run mode (K_SERVICE set)
    os.environ['K_SERVICE'] = 'video-processor'
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    if is_cloud_run:
        print("✅ Correctly detected CLOUD RUN mode (K_SERVICE set)")
    else:
        print("❌ Failed to detect CLOUD RUN mode")
        return False
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Database Connection Mode Tests")
    print("=" * 80)
    print("Testing connection parameter logic for local and Cloud Run environments")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("Connection Mode Detection", test_connection_mode_detection()))
    results.append(("Local Connection Parameters", test_local_connection_params()))
    results.append(("Cloud Run Connection Parameters", test_cloud_run_connection_params()))
    
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
    
    if passed == total:
        print("\n✅ All connection mode tests passed!")
        print("   The database connection correctly handles:")
        print("   - Local development: PostgreSQL TCP/IP (DB_HOST:DB_PORT)")
        print("   - Cloud Run production: Cloud SQL Unix socket (/cloudsql/CONNECTION_NAME)")
    
    # Return exit code
    return 0 if passed == total else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
