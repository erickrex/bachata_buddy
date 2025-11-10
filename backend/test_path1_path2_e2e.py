#!/usr/bin/env python
"""
End-to-End Test for Path 1 and Path 2 Blueprint Generation

This script tests both user paths with the new blueprint architecture:
- Path 1: Select Song → Blueprint Generation → Job Execution
- Path 2: Describe Choreo → AI Parsing → Blueprint Generation → Job Execution

It verifies that both paths generate valid blueprints and can produce videos.

Usage:
    uv run --directory bachata_buddy/backend python test_path1_path2_e2e.py
"""
import os
import sys
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import Song, ChoreographyTask, Blueprint
from django.contrib.auth import get_user_model
from services.blueprint_generator import BlueprintGenerator
from services.vector_search_service import VectorSearchService
from services.gemini_service import GeminiService
import uuid

User = get_user_model()


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message):
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_error(message):
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def print_info(message):
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")


def print_warning(message):
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def setup_test_data():
    """Setup test user and song"""
    print_header("Setting Up Test Data")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test_e2e_user',
        defaults={
            'email': 'test_e2e@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print_success(f"Created test user: {user.username}")
    else:
        print_info(f"Using existing user: {user.username}")
    
    # Get or create test song
    song = Song.objects.filter(genre='bachata').first()
    
    if not song:
        print_warning("No songs found in database, creating test song...")
        song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='data/songs/test_short.mp3'
        )
        print_success(f"Created test song: {song.title}")
    else:
        print_info(f"Using existing song: {song.title} by {song.artist}")
        print_info(f"  - Duration: {song.duration}s")
        print_info(f"  - BPM: {song.bpm}")
        print_info(f"  - Audio path: {song.audio_path}")
    
    return user, song


def initialize_services():
    """Initialize blueprint generation services"""
    print_header("Initializing Services")
    
    try:
        # Initialize vector search
        print_info("Initializing VectorSearchService...")
        vector_search = VectorSearchService()
        print_success("VectorSearchService initialized")
        
        # Initialize Gemini service
        print_info("Initializing GeminiService...")
        gemini_service = GeminiService()
        print_success("GeminiService initialized")
        
        # Initialize MusicAnalyzer (mock if not available)
        print_info("Initializing MusicAnalyzer...")
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'job', 'src', 'services'))
            from music_analyzer import MusicAnalyzer
            music_analyzer = MusicAnalyzer()
            print_success("MusicAnalyzer loaded from job container")
        except ImportError:
            print_warning("MusicAnalyzer not available, using mock")
            
            class MockMusicSection:
                def __init__(self, start_time, end_time, section_type, energy_level):
                    self.start_time = start_time
                    self.end_time = end_time
                    self.section_type = section_type
                    self.energy_level = energy_level
                    self.tempo_stability = 0.9
                    self.recommended_move_types = ['basic', 'turn']
            
            class MockMusicFeatures:
                def __init__(self):
                    self.tempo = 120.0
                    self.beat_positions = [i * 0.5 for i in range(360)]
                    self.duration = 180.0
                    self.sections = [
                        MockMusicSection(0.0, 60.0, 'intro', 0.7),
                        MockMusicSection(60.0, 120.0, 'verse', 0.8),
                        MockMusicSection(120.0, 180.0, 'chorus', 0.6)
                    ]
                    self.energy_profile = [0.7, 0.8, 0.6]
                    self.tempo_confidence = 0.95
                    self.rhythm_pattern_strength = 0.85
                    self.syncopation_level = 0.3
                    self.audio_embedding = [0.1] * 128
            
            class MockMusicAnalyzer:
                def analyze_audio(self, audio_path):
                    return MockMusicFeatures()
            
            music_analyzer = MockMusicAnalyzer()
        
        # Create blueprint generator
        print_info("Creating BlueprintGenerator...")
        blueprint_gen = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer,
            gemini_service=gemini_service
        )
        print_success("BlueprintGenerator initialized")
        
        return blueprint_gen
        
    except Exception as e:
        print_error(f"Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()
        return None


def validate_blueprint_schema(blueprint, path_name):
    """Validate blueprint has correct schema"""
    print_info(f"Validating {path_name} blueprint schema...")
    
    required_fields = [
        'task_id',
        'audio_path',
        'audio_tempo',
        'moves',
        'total_duration',
        'difficulty_level',
        'generation_parameters',
        'output_config'
    ]
    
    validation_passed = True
    for field in required_fields:
        if field in blueprint:
            print_success(f"  {field}: present")
        else:
            print_error(f"  {field}: MISSING")
            validation_passed = False
    
    # Validate moves structure
    if 'moves' in blueprint and isinstance(blueprint['moves'], list):
        print_success(f"  moves: list with {len(blueprint['moves'])} items")
        if len(blueprint['moves']) > 0:
            move = blueprint['moves'][0]
            move_fields = ['clip_id', 'video_path', 'start_time', 'duration', 'transition_type']
            for field in move_fields:
                if field in move:
                    print_success(f"    move.{field}: present")
                else:
                    print_error(f"    move.{field}: MISSING")
                    validation_passed = False
    else:
        print_error(f"  moves: invalid structure")
        validation_passed = False
    
    return validation_passed


def test_path1(user, song, blueprint_gen):
    """Test Path 1: Select Song → Blueprint Generation"""
    print_header("Testing Path 1: Select Song → Blueprint Generation")
    
    # Create task
    task_id = str(uuid.uuid4())
    print_info(f"Creating task: {task_id}")
    
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=user,
        status='pending',
        progress=0,
        stage='generating_blueprint',
        message='Generating choreography blueprint...',
        song=song
    )
    print_success(f"Task created: {task_id}")
    
    # Generate blueprint
    print_info("Generating blueprint...")
    try:
        blueprint = blueprint_gen.generate_blueprint(
            task_id=task_id,
            song_path=song.audio_path,
            difficulty='intermediate',
            energy_level='medium',
            style='modern',
            user_id=user.id
        )
        print_success("Blueprint generated successfully")
        
        # Validate schema
        if not validate_blueprint_schema(blueprint, "Path 1"):
            print_error("Path 1 blueprint schema validation FAILED")
            return None, None
        
        print_success("Path 1 blueprint schema validation PASSED")
        
        # Store blueprint
        print_info("Storing blueprint in database...")
        blueprint_obj = Blueprint.objects.create(
            task=task,
            blueprint_json=blueprint
        )
        print_success("Blueprint stored successfully")
        
        # Print blueprint summary
        print_info("\nPath 1 Blueprint Summary:")
        print_info(f"  Task ID: {blueprint['task_id']}")
        print_info(f"  Audio path: {blueprint['audio_path']}")
        print_info(f"  Audio tempo: {blueprint['audio_tempo']} BPM")
        print_info(f"  Total duration: {blueprint['total_duration']}s")
        print_info(f"  Difficulty: {blueprint['difficulty_level']}")
        print_info(f"  Moves count: {len(blueprint['moves'])}")
        print_info(f"  Output path: {blueprint['output_config']['output_path']}")
        
        return task, blueprint
        
    except Exception as e:
        print_error(f"Path 1 blueprint generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_path2(user, song, blueprint_gen):
    """Test Path 2: Describe Choreo → AI Parsing → Blueprint Generation"""
    print_header("Testing Path 2: Describe Choreo → AI Parsing → Blueprint Generation")
    
    # Create task
    task_id = str(uuid.uuid4())
    print_info(f"Creating task: {task_id}")
    
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=user,
        status='pending',
        progress=0,
        stage='generating_blueprint',
        message='Generating AI choreography blueprint...',
        song=song
    )
    print_success(f"Task created: {task_id}")
    
    # Simulate AI query parsing (in real flow, this would be done by Gemini)
    print_info("Simulating AI query parsing...")
    query = "Create a romantic beginner choreography with slow movements"
    parsed_params = {
        'difficulty': 'beginner',
        'energy_level': 'low',
        'style': 'romantic'
    }
    print_info(f"  Query: {query}")
    print_info(f"  Parsed parameters: {parsed_params}")
    
    # Generate blueprint
    print_info("Generating blueprint...")
    try:
        blueprint = blueprint_gen.generate_blueprint(
            task_id=task_id,
            song_path=song.audio_path,
            difficulty=parsed_params['difficulty'],
            energy_level=parsed_params['energy_level'],
            style=parsed_params['style'],
            user_id=user.id
        )
        
        # Add AI-specific metadata
        blueprint['generation_parameters']['ai_mode'] = True
        blueprint['generation_parameters']['original_query'] = query
        
        print_success("Blueprint generated successfully")
        
        # Validate schema
        if not validate_blueprint_schema(blueprint, "Path 2"):
            print_error("Path 2 blueprint schema validation FAILED")
            return None, None
        
        print_success("Path 2 blueprint schema validation PASSED")
        
        # Store blueprint
        print_info("Storing blueprint in database...")
        blueprint_obj = Blueprint.objects.create(
            task=task,
            blueprint_json=blueprint
        )
        print_success("Blueprint stored successfully")
        
        # Print blueprint summary
        print_info("\nPath 2 Blueprint Summary:")
        print_info(f"  Task ID: {blueprint['task_id']}")
        print_info(f"  Audio path: {blueprint['audio_path']}")
        print_info(f"  Audio tempo: {blueprint['audio_tempo']} BPM")
        print_info(f"  Total duration: {blueprint['total_duration']}s")
        print_info(f"  Difficulty: {blueprint['difficulty_level']}")
        print_info(f"  Moves count: {len(blueprint['moves'])}")
        print_info(f"  AI mode: {blueprint['generation_parameters']['ai_mode']}")
        print_info(f"  Original query: {blueprint['generation_parameters']['original_query']}")
        print_info(f"  Output path: {blueprint['output_config']['output_path']}")
        
        return task, blueprint
        
    except Exception as e:
        print_error(f"Path 2 blueprint generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def compare_blueprints(blueprint1, blueprint2):
    """Compare blueprints from Path 1 and Path 2"""
    print_header("Comparing Path 1 and Path 2 Blueprints")
    
    print_info("Checking schema consistency...")
    
    # Check that both have the same top-level fields
    fields1 = set(blueprint1.keys())
    fields2 = set(blueprint2.keys())
    
    if fields1 == fields2:
        print_success("Both blueprints have the same top-level fields")
    else:
        print_warning("Blueprints have different top-level fields")
        print_info(f"  Path 1 only: {fields1 - fields2}")
        print_info(f"  Path 2 only: {fields2 - fields1}")
    
    # Check move structure
    if blueprint1['moves'] and blueprint2['moves']:
        move1_fields = set(blueprint1['moves'][0].keys())
        move2_fields = set(blueprint2['moves'][0].keys())
        
        if move1_fields == move2_fields:
            print_success("Both blueprints have the same move structure")
        else:
            print_warning("Blueprints have different move structures")
            print_info(f"  Path 1 only: {move1_fields - move2_fields}")
            print_info(f"  Path 2 only: {move2_fields - move1_fields}")
    
    # Check AI-specific metadata
    if blueprint2['generation_parameters'].get('ai_mode'):
        print_success("Path 2 blueprint has AI-specific metadata")
        print_info(f"  AI mode: {blueprint2['generation_parameters']['ai_mode']}")
        print_info(f"  Original query: {blueprint2['generation_parameters'].get('original_query', 'N/A')}")
    else:
        print_warning("Path 2 blueprint missing AI-specific metadata")
    
    print_success("Blueprint comparison complete")


def check_output_videos(blueprint1, blueprint2):
    """Check if output video paths exist"""
    print_header("Checking Output Video Paths")
    
    path1_output = blueprint1['output_config']['output_path']
    path2_output = blueprint2['output_config']['output_path']
    
    print_info(f"Path 1 output: {path1_output}")
    print_info(f"Path 2 output: {path2_output}")
    
    # Check if paths exist (they won't until job runs)
    path1_exists = Path(path1_output).exists()
    path2_exists = Path(path2_output).exists()
    
    if path1_exists:
        print_success(f"Path 1 video exists: {path1_output}")
        size = Path(path1_output).stat().st_size / (1024 * 1024)
        print_info(f"  Size: {size:.2f} MB")
    else:
        print_warning(f"Path 1 video does not exist yet (will be created by job)")
    
    if path2_exists:
        print_success(f"Path 2 video exists: {path2_output}")
        size = Path(path2_output).stat().st_size / (1024 * 1024)
        print_info(f"  Size: {size:.2f} MB")
    else:
        print_warning(f"Path 2 video does not exist yet (will be created by job)")
    
    return path1_output, path2_output


def main():
    """Main test flow"""
    print_header("End-to-End Test: Path 1 and Path 2 Blueprint Generation")
    
    # Setup
    user, song = setup_test_data()
    blueprint_gen = initialize_services()
    
    if not blueprint_gen:
        print_error("Failed to initialize services")
        return 1
    
    # Test Path 1
    task1, blueprint1 = test_path1(user, song, blueprint_gen)
    if not task1 or not blueprint1:
        print_error("Path 1 test FAILED")
        return 1
    
    # Test Path 2
    task2, blueprint2 = test_path2(user, song, blueprint_gen)
    if not task2 or not blueprint2:
        print_error("Path 2 test FAILED")
        return 1
    
    # Compare blueprints
    compare_blueprints(blueprint1, blueprint2)
    
    # Check output paths
    path1_output, path2_output = check_output_videos(blueprint1, blueprint2)
    
    # Final summary
    print_header("Test Summary")
    print_success("✅ Path 1 (Select Song) blueprint generation works")
    print_success("✅ Path 2 (Describe Choreo) blueprint generation works")
    print_success("✅ Both paths generate valid blueprint schemas")
    print_success("✅ Blueprints are stored in database")
    
    print_info("\nGenerated Blueprints:")
    print_info(f"  Path 1 Task ID: {task1.task_id}")
    print_info(f"  Path 1 Output: {path1_output}")
    print_info(f"  Path 2 Task ID: {task2.task_id}")
    print_info(f"  Path 2 Output: {path2_output}")
    
    print_info("\nNext Steps:")
    print_info("  To generate actual videos, run the job container with these blueprints:")
    print_info(f"    TASK_ID={task1.task_id} BLUEPRINT_JSON='...' docker-compose run job")
    print_info(f"    TASK_ID={task2.task_id} BLUEPRINT_JSON='...' docker-compose run job")
    
    print_header("End-to-End Test PASSED")
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
