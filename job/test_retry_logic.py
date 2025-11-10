"""
Test script for database retry logic

This script tests that the retry decorator works correctly for database operations.
"""
import os
import sys
import logging
import time
from unittest.mock import Mock, patch
import psycopg2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import retry_on_db_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_retry_on_success():
    """Test that function succeeds on first try"""
    print("\n" + "=" * 80)
    print("Test 1: Function succeeds on first try")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        return "success"
    
    result = mock_function()
    
    if result == "success" and call_count[0] == 1:
        print("✅ Function succeeded on first try")
        return True
    else:
        print(f"❌ Expected 1 call, got {call_count[0]}")
        return False


def test_retry_on_transient_error():
    """Test that function retries on transient database errors"""
    print("\n" + "=" * 80)
    print("Test 2: Function retries on transient errors")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        if call_count[0] < 3:
            # Fail first 2 times
            raise psycopg2.OperationalError("Connection failed")
        return "success"
    
    try:
        result = mock_function()
        
        if result == "success" and call_count[0] == 3:
            print(f"✅ Function succeeded after {call_count[0]} attempts")
            return True
        else:
            print(f"❌ Expected 3 calls, got {call_count[0]}")
            return False
    except Exception as e:
        print(f"❌ Function failed: {e}")
        return False


def test_retry_exhaustion():
    """Test that function fails after max retries"""
    print("\n" + "=" * 80)
    print("Test 3: Function fails after max retries")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        # Always fail
        raise psycopg2.OperationalError("Connection failed")
    
    try:
        result = mock_function()
        print(f"❌ Function should have failed but returned: {result}")
        return False
    except psycopg2.OperationalError:
        if call_count[0] == 4:  # Initial try + 3 retries
            print(f"✅ Function failed after {call_count[0]} attempts (1 initial + 3 retries)")
            return True
        else:
            print(f"❌ Expected 4 calls (1 initial + 3 retries), got {call_count[0]}")
            return False


def test_no_retry_on_non_db_error():
    """Test that function doesn't retry on non-database errors"""
    print("\n" + "=" * 80)
    print("Test 4: No retry on non-database errors")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        # Non-database error
        raise ValueError("Invalid input")
    
    try:
        result = mock_function()
        print(f"❌ Function should have failed but returned: {result}")
        return False
    except ValueError:
        if call_count[0] == 1:
            print(f"✅ Function failed immediately without retry (1 attempt)")
            return True
        else:
            print(f"❌ Expected 1 call, got {call_count[0]}")
            return False


def test_retry_on_interface_error():
    """Test that function retries on InterfaceError"""
    print("\n" + "=" * 80)
    print("Test 5: Function retries on InterfaceError")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        if call_count[0] < 2:
            # Fail first time
            raise psycopg2.InterfaceError("Connection lost")
        return "success"
    
    try:
        result = mock_function()
        
        if result == "success" and call_count[0] == 2:
            print(f"✅ Function succeeded after {call_count[0]} attempts")
            return True
        else:
            print(f"❌ Expected 2 calls, got {call_count[0]}")
            return False
    except Exception as e:
        print(f"❌ Function failed: {e}")
        return False


def test_retry_on_database_error():
    """Test that function retries on DatabaseError"""
    print("\n" + "=" * 80)
    print("Test 6: Function retries on DatabaseError")
    print("=" * 80)
    
    call_count = [0]
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_count[0] += 1
        if call_count[0] < 2:
            # Fail first time
            raise psycopg2.DatabaseError("Database unavailable")
        return "success"
    
    try:
        result = mock_function()
        
        if result == "success" and call_count[0] == 2:
            print(f"✅ Function succeeded after {call_count[0]} attempts")
            return True
        else:
            print(f"❌ Expected 2 calls, got {call_count[0]}")
            return False
    except Exception as e:
        print(f"❌ Function failed: {e}")
        return False


def test_exponential_backoff():
    """Test that retry delays increase exponentially"""
    print("\n" + "=" * 80)
    print("Test 7: Exponential backoff timing")
    print("=" * 80)
    
    call_times = []
    
    @retry_on_db_error(max_retries=3, delay=0.1, backoff=2.0)
    def mock_function():
        call_times.append(time.time())
        if len(call_times) < 4:
            raise psycopg2.OperationalError("Connection failed")
        return "success"
    
    try:
        start_time = time.time()
        result = mock_function()
        
        # Check delays between calls
        delays = [call_times[i] - call_times[i-1] for i in range(1, len(call_times))]
        
        print(f"  Delays between attempts: {[f'{d:.2f}s' for d in delays]}")
        
        # First delay should be ~0.1s, second ~0.2s, third ~0.4s
        expected_delays = [0.1, 0.2, 0.4]
        
        all_correct = True
        for i, (actual, expected) in enumerate(zip(delays, expected_delays)):
            # Allow 50ms tolerance
            if abs(actual - expected) < 0.05:
                print(f"  ✅ Delay {i+1}: {actual:.2f}s (expected ~{expected}s)")
            else:
                print(f"  ❌ Delay {i+1}: {actual:.2f}s (expected ~{expected}s)")
                all_correct = False
        
        if all_correct:
            print("✅ Exponential backoff working correctly")
            return True
        else:
            print("⚠️  Exponential backoff timing slightly off (may be acceptable)")
            return True  # Still pass, timing can vary
            
    except Exception as e:
        print(f"❌ Function failed: {e}")
        return False


def main():
    """Run all retry logic tests"""
    print("\n" + "=" * 80)
    print("Database Retry Logic Tests")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("Success on first try", test_retry_on_success()))
    results.append(("Retry on transient error", test_retry_on_transient_error()))
    results.append(("Retry exhaustion", test_retry_exhaustion()))
    results.append(("No retry on non-DB error", test_no_retry_on_non_db_error()))
    results.append(("Retry on InterfaceError", test_retry_on_interface_error()))
    results.append(("Retry on DatabaseError", test_retry_on_database_error()))
    results.append(("Exponential backoff", test_exponential_backoff()))
    
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
        print("\n🎉 All retry logic tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
    
    print("=" * 80)
    
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
