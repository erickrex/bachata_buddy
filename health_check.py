#!/usr/bin/env python3
"""
Comprehensive health check for Bachata Buddy project.
Verifies all critical components are working after Git cleanup.
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status="info"):
    """Print colored status message."""
    if status == "success":
        print(f"{GREEN}✓{RESET} {message}")
    elif status == "error":
        print(f"{RED}✗{RESET} {message}")
    elif status == "warning":
        print(f"{YELLOW}⚠{RESET} {message}")
    else:
        print(f"{BLUE}ℹ{RESET} {message}")

def check_critical_files():
    """Check that all critical files exist."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}1. Checking Critical Files{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    critical_files = [
        # Core services
        "core/services/__init__.py",
        "core/services/resource_manager.py",
        "core/services/temp_file_manager.py",
        "core/services/recommendation_engine.py",
        "core/services/elasticsearch_service.py",
        "core/services/choreography_pipeline.py",
        "core/services/yolov8_couple_detector.py",
        "core/services/text_embedding_service.py",
        
        # Config
        "core/config/environment_config.py",
        
        # Django
        "manage.py",
        "bachata_buddy/settings.py",
        "bachata_buddy/urls.py",
        
        # Data
        "data/bachata_annotations.json",
        
        # Models
        "yolov8n-pose.pt",
    ]
    
    all_exist = True
    for file_path in critical_files:
        if Path(file_path).exists():
            print_status(f"{file_path}", "success")
        else:
            print_status(f"{file_path} - MISSING!", "error")
            all_exist = False
    
    return all_exist

def check_data_integrity():
    """Check data directory integrity."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}2. Checking Data Integrity{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    # Check videos
    video_dir = Path("data/Bachata_steps")
    if video_dir.exists():
        video_count = len(list(video_dir.rglob("*.mp4")))
        if video_count == 38:
            print_status(f"Training videos: {video_count}/38", "success")
        else:
            print_status(f"Training videos: {video_count}/38 - MISMATCH!", "warning")
    else:
        print_status("Training videos directory missing!", "error")
        return False
    
    # Check songs
    songs_dir = Path("data/songs")
    if songs_dir.exists():
        song_count = len(list(songs_dir.glob("*.mp3")))
        if song_count == 15:
            print_status(f"Songs: {song_count}/15", "success")
        else:
            print_status(f"Songs: {song_count}/15 - MISMATCH!", "warning")
    else:
        print_status("Songs directory missing!", "error")
        return False
    
    # Check annotations
    annotations_file = Path("data/bachata_annotations.json")
    if annotations_file.exists():
        print_status("Annotations file exists", "success")
    else:
        print_status("Annotations file missing!", "error")
        return False
    
    return True

def check_imports():
    """Check that all critical imports work."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}3. Checking Python Imports{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    imports_to_test = [
        ("core.services", "Core services module"),
        ("core.services.resource_manager", "Resource manager"),
        ("core.services.temp_file_manager", "Temp file manager"),
        ("core.services.recommendation_engine", "Recommendation engine"),
        ("core.services.elasticsearch_service", "Elasticsearch service"),
        ("core.config.environment_config", "Environment config"),
    ]
    
    all_imports_ok = True
    for module_name, description in imports_to_test:
        try:
            __import__(module_name)
            print_status(f"{description} ({module_name})", "success")
        except Exception as e:
            print_status(f"{description} ({module_name}) - {str(e)}", "error")
            all_imports_ok = False
    
    return all_imports_ok

def check_django_imports():
    """Check Django-specific imports."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}4. Checking Django Imports{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bachata_buddy.settings')
    
    try:
        import django
        django.setup()
        print_status("Django setup successful", "success")
    except Exception as e:
        print_status(f"Django setup failed: {e}", "error")
        return False
    
    # Test Django imports
    django_imports = [
        ("choreography.views", "Choreography views"),
        ("choreography.models", "Choreography models"),
        ("core.services.choreography_pipeline", "Choreography pipeline"),
    ]
    
    all_ok = True
    for module_name, description in django_imports:
        try:
            __import__(module_name)
            print_status(f"{description} ({module_name})", "success")
        except Exception as e:
            print_status(f"{description} ({module_name}) - {str(e)}", "error")
            all_ok = False
    
    return all_ok

def check_django_configuration():
    """Check Django configuration."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}5. Checking Django Configuration{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Run Django check
        print_status("Running Django system check...", "info")
        execute_from_command_line(['manage.py', 'check'])
        print_status("Django system check passed", "success")
        return True
        
    except SystemExit as e:
        if e.code == 0:
            print_status("Django system check passed", "success")
            return True
        else:
            print_status(f"Django system check failed with code {e.code}", "error")
            return False
    except Exception as e:
        print_status(f"Django check error: {e}", "error")
        return False

def check_repository_size():
    """Check repository size after cleanup."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}6. Checking Repository Size{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    import subprocess
    
    try:
        # Get .git size
        result = subprocess.run(['du', '-sh', '.git'], capture_output=True, text=True)
        git_size = result.stdout.split()[0]
        print_status(f"Git history size: {git_size}", "info")
        
        # Get total size
        result = subprocess.run(['du', '-sh', '.'], capture_output=True, text=True)
        total_size = result.stdout.split()[0]
        print_status(f"Total repository size: {total_size}", "info")
        
        return True
    except Exception as e:
        print_status(f"Could not check size: {e}", "warning")
        return True  # Non-critical

def main():
    """Run all health checks."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Bachata Buddy - Comprehensive Health Check{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    results = {
        "Critical Files": check_critical_files(),
        "Data Integrity": check_data_integrity(),
        "Python Imports": check_imports(),
        "Django Imports": check_django_imports(),
        "Django Configuration": check_django_configuration(),
        "Repository Size": check_repository_size(),
    }
    
    # Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Summary{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    all_passed = True
    for check_name, passed in results.items():
        if passed:
            print_status(f"{check_name}: PASSED", "success")
        else:
            print_status(f"{check_name}: FAILED", "error")
            all_passed = False
    
    print(f"\n{BLUE}{'='*80}{RESET}")
    if all_passed:
        print(f"{GREEN}✅ All health checks passed!{RESET}")
        print(f"{GREEN}The project is working correctly after Git cleanup.{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Run the development server: uv run python manage.py runserver")
        print("  2. Run tests: uv run pytest tests/")
        print("  3. Generate embeddings: uv run python scripts/generate_embeddings.py")
    else:
        print(f"{RED}❌ Some health checks failed!{RESET}")
        print(f"{RED}Please review the errors above and fix them.{RESET}")
        return 1
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
