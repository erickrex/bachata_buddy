"""
Test script for blueprint parser and validator

This script tests the blueprint parsing and validation functionality
for the video processing job.

Usage:
    python test_blueprint_parser.py
"""
import os
import sys
import json
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.blueprint_parser import (
    BlueprintParser,
    BlueprintValidationError,
    parse_blueprint
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_valid_blueprint():
    """Test parsing a valid blueprint"""
    print("\n" + "=" * 80)
    print("Test 1: Valid Blueprint")
    print("=" * 80)
    
    valid_blueprint = {
        "task_id": "test-task-123",
        "audio_path": "data/songs/test_song.mp3",
        "audio_tempo": 120.0,
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0,
                "transition_type": "cut"
            },
            {
                "clip_id": "move_2",
                "video_path": "data/Bachata_steps/body_roll/body_roll_1.mp4",
                "start_time": 8.0,
                "duration": 8.0,
                "transition_type": "crossfade"
            }
        ],
        "total_duration": 16.0,
        "difficulty_level": "intermediate",
        "output_config": {
            "output_path": "data/output/choreography_test-task-123.mp4",
            "output_format": "mp4",
            "frame_rate": 30
        }
    }
    
    try:
        blueprint_json = json.dumps(valid_blueprint)
        parser = BlueprintParser(allow_absolute_paths=False)
        result = parser.parse_and_validate(blueprint_json)
        
        print("✅ Valid blueprint parsed successfully")
        print(f"   Task ID: {result['task_id']}")
        print(f"   Number of moves: {len(result['moves'])}")
        print(f"   Total duration: {result['total_duration']}s")
        
        # Test summary
        summary = parser.get_summary(result)
        print(f"   Summary: {summary}")
        
        return True
    except BlueprintValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_missing_required_fields():
    """Test blueprint with missing required fields"""
    print("\n" + "=" * 80)
    print("Test 2: Missing Required Fields")
    print("=" * 80)
    
    # Missing task_id
    invalid_blueprint = {
        "audio_path": "data/songs/test_song.mp3",
        "moves": [],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(invalid_blueprint)
        parser = BlueprintParser()
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for missing task_id")
        return False
    except BlueprintValidationError as e:
        if "task_id" in str(e):
            print(f"✅ Correctly caught missing required field: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_empty_moves_array():
    """Test blueprint with empty moves array"""
    print("\n" + "=" * 80)
    print("Test 3: Empty Moves Array")
    print("=" * 80)
    
    invalid_blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "moves": [],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(invalid_blueprint)
        parser = BlueprintParser()
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for empty moves array")
        return False
    except BlueprintValidationError as e:
        if "empty" in str(e).lower():
            print(f"✅ Correctly caught empty moves array: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_directory_traversal_attack():
    """Test blueprint with directory traversal in paths"""
    print("\n" + "=" * 80)
    print("Test 4: Directory Traversal Attack Prevention")
    print("=" * 80)
    
    malicious_blueprint = {
        "task_id": "test-123",
        "audio_path": "../../etc/passwd",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "../../../sensitive/file.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(malicious_blueprint)
        parser = BlueprintParser(allow_absolute_paths=False)
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for directory traversal")
        return False
    except BlueprintValidationError as e:
        if ".." in str(e):
            print(f"✅ Correctly caught directory traversal attempt")
            print(f"   Errors: {e.errors}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_absolute_path_rejection():
    """Test blueprint with absolute paths (should be rejected)"""
    print("\n" + "=" * 80)
    print("Test 5: Absolute Path Rejection")
    print("=" * 80)
    
    blueprint_with_absolute = {
        "task_id": "test-123",
        "audio_path": "/absolute/path/to/song.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/Bachata_steps/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(blueprint_with_absolute)
        parser = BlueprintParser(allow_absolute_paths=False)
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for absolute path")
        return False
    except BlueprintValidationError as e:
        if "absolute" in str(e).lower():
            print(f"✅ Correctly rejected absolute path")
            print(f"   Error: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_absolute_path_allowed():
    """Test blueprint with absolute paths when explicitly allowed"""
    print("\n" + "=" * 80)
    print("Test 6: Absolute Path Allowed (Testing Mode)")
    print("=" * 80)
    
    blueprint_with_absolute = {
        "task_id": "test-123",
        "audio_path": "/tmp/test_song.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "/tmp/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "output_config": {"output_path": "/tmp/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(blueprint_with_absolute)
        parser = BlueprintParser(allow_absolute_paths=True)
        result = parser.parse_and_validate(blueprint_json)
        
        print("✅ Absolute paths allowed when explicitly enabled")
        print(f"   Audio path: {result['audio_path']}")
        return True
    except BlueprintValidationError as e:
        print(f"❌ Should have allowed absolute paths: {e}")
        return False


def test_invalid_json():
    """Test parsing invalid JSON"""
    print("\n" + "=" * 80)
    print("Test 7: Invalid JSON")
    print("=" * 80)
    
    invalid_json = "{ this is not valid json }"
    
    try:
        parser = BlueprintParser()
        parser.parse_and_validate(invalid_json)
        
        print("❌ Should have raised validation error for invalid JSON")
        return False
    except BlueprintValidationError as e:
        if "json" in str(e).lower():
            print(f"✅ Correctly caught invalid JSON: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_invalid_move_fields():
    """Test blueprint with invalid move fields"""
    print("\n" + "=" * 80)
    print("Test 8: Invalid Move Fields")
    print("=" * 80)
    
    invalid_blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/basic_1.mp4",
                "start_time": -5.0,  # Negative start time
                "duration": 0.0  # Zero duration
            }
        ],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(invalid_blueprint)
        parser = BlueprintParser()
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for invalid move fields")
        return False
    except BlueprintValidationError as e:
        errors_str = str(e)
        has_negative_error = "negative" in errors_str.lower()
        has_positive_error = "positive" in errors_str.lower()
        
        if has_negative_error and has_positive_error:
            print(f"✅ Correctly caught invalid move fields")
            print(f"   Errors found: {len(e.errors)}")
            for error in e.errors:
                print(f"   - {error}")
            return True
        else:
            print(f"❌ Missing expected errors: {e}")
            return False


def test_invalid_transition_type():
    """Test blueprint with invalid transition type"""
    print("\n" + "=" * 80)
    print("Test 9: Invalid Transition Type")
    print("=" * 80)
    
    invalid_blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0,
                "transition_type": "invalid_transition"
            }
        ],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(invalid_blueprint)
        parser = BlueprintParser()
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for invalid transition type")
        return False
    except BlueprintValidationError as e:
        if "transition_type" in str(e):
            print(f"✅ Correctly caught invalid transition type")
            print(f"   Error: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_invalid_difficulty_level():
    """Test blueprint with invalid difficulty level"""
    print("\n" + "=" * 80)
    print("Test 10: Invalid Difficulty Level")
    print("=" * 80)
    
    invalid_blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "difficulty_level": "super_hard",  # Invalid difficulty
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(invalid_blueprint)
        parser = BlueprintParser()
        parser.parse_and_validate(blueprint_json)
        
        print("❌ Should have raised validation error for invalid difficulty level")
        return False
    except BlueprintValidationError as e:
        if "difficulty_level" in str(e):
            print(f"✅ Correctly caught invalid difficulty level")
            print(f"   Error: {e.errors[0]}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


def test_convenience_function():
    """Test the convenience parse_blueprint function"""
    print("\n" + "=" * 80)
    print("Test 11: Convenience Function")
    print("=" * 80)
    
    valid_blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "output_config": {"output_path": "data/output/test.mp4"}
    }
    
    try:
        blueprint_json = json.dumps(valid_blueprint)
        result = parse_blueprint(blueprint_json)
        
        print("✅ Convenience function works correctly")
        print(f"   Task ID: {result['task_id']}")
        return True
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
        return False


def test_complex_blueprint():
    """Test a complex blueprint with all optional fields"""
    print("\n" + "=" * 80)
    print("Test 12: Complex Blueprint with All Fields")
    print("=" * 80)
    
    complex_blueprint = {
        "task_id": "complex-test-456",
        "audio_path": "data/songs/complex_song.mp3",
        "audio_tempo": 128.5,
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0,
                "transition_type": "cut",
                "original_duration": 10.0,
                "trim_start": 1.0,
                "trim_end": 1.0,
                "volume_adjustment": 0.8
            },
            {
                "clip_id": "move_2",
                "video_path": "data/Bachata_steps/body_roll/body_roll_1.mp4",
                "start_time": 8.0,
                "duration": 8.0,
                "transition_type": "crossfade",
                "original_duration": 8.0,
                "trim_start": 0.0,
                "trim_end": 0.0,
                "volume_adjustment": 1.0
            },
            {
                "clip_id": "move_3",
                "video_path": "data/Bachata_steps/combination/combo_1.mp4",
                "start_time": 16.0,
                "duration": 12.0,
                "transition_type": "fade_black"
            }
        ],
        "total_duration": 28.0,
        "difficulty_level": "advanced",
        "generation_timestamp": "2025-11-09T12:00:00Z",
        "generation_parameters": {
            "energy_level": "high",
            "style": "modern",
            "user_id": 123
        },
        "output_config": {
            "output_path": "data/output/choreography_complex-test-456.mp4",
            "output_format": "mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "video_bitrate": "2M",
            "audio_bitrate": "128k",
            "frame_rate": 30,
            "transition_duration": 0.5,
            "fade_duration": 0.3,
            "add_audio_overlay": True,
            "normalize_audio": True
        }
    }
    
    try:
        blueprint_json = json.dumps(complex_blueprint)
        parser = BlueprintParser()
        result = parser.parse_and_validate(blueprint_json)
        
        print("✅ Complex blueprint parsed successfully")
        print(f"   Task ID: {result['task_id']}")
        print(f"   Number of moves: {len(result['moves'])}")
        print(f"   Total duration: {result['total_duration']}s")
        print(f"   Difficulty: {result['difficulty_level']}")
        print(f"   Has generation parameters: {bool(result.get('generation_parameters'))}")
        
        return True
    except BlueprintValidationError as e:
        print(f"❌ Complex blueprint validation failed: {e}")
        for error in e.errors:
            print(f"   - {error}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 80)
    print("BLUEPRINT PARSER TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Valid Blueprint", test_valid_blueprint),
        ("Missing Required Fields", test_missing_required_fields),
        ("Empty Moves Array", test_empty_moves_array),
        ("Directory Traversal Prevention", test_directory_traversal_attack),
        ("Absolute Path Rejection", test_absolute_path_rejection),
        ("Absolute Path Allowed", test_absolute_path_allowed),
        ("Invalid JSON", test_invalid_json),
        ("Invalid Move Fields", test_invalid_move_fields),
        ("Invalid Transition Type", test_invalid_transition_type),
        ("Invalid Difficulty Level", test_invalid_difficulty_level),
        ("Convenience Function", test_convenience_function),
        ("Complex Blueprint", test_complex_blueprint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 80)
    print(f"Results: {passed}/{total} tests passed ({100*passed//total}%)")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
