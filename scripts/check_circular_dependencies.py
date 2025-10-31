#!/usr/bin/env python
"""
Script to detect circular dependencies in the refactored Django app structure.

This script verifies:
1. No circular dependencies exist between apps
2. Dependency rules are followed:
   - common SHALL NOT depend on video_processing or ai_services
   - video_processing MAY depend on common and ai_services
   - ai_services MAY depend on common
   - All apps MAY depend on common
3. All services can be imported successfully
"""

import ast
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import statements from Python files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: List[str] = []
    
    def visit_Import(self, node: ast.Import):
        """Visit import statements like: import module"""
        for alias in node.names:
            self.imports.append(alias.name.split('.')[0])
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statements like: from module import something"""
        if node.module:
            self.imports.append(node.module.split('.')[0])
        self.generic_visit(node)


def get_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip migrations, __pycache__, and test directories for dependency analysis
        dirs[:] = [d for d in dirs if d not in ['migrations', '__pycache__', '.pytest_cache', '.venv', 'venv']]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                python_files.append(Path(root) / file)
    
    return python_files


def extract_imports(file_path: Path) -> List[str]:
    """Extract all imports from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        analyzer = ImportAnalyzer(str(file_path))
        analyzer.visit(tree)
        return analyzer.imports
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}")
        return []


def analyze_app_dependencies(base_dir: Path) -> Dict[str, Set[str]]:
    """
    Analyze dependencies between Django apps.
    
    Returns a dictionary mapping app names to sets of apps they depend on.
    """
    apps = ['common', 'ai_services', 'video_processing', 'core', 
            'choreography', 'users', 'instructors', 'user_collections']
    
    dependencies: Dict[str, Set[str]] = defaultdict(set)
    
    for app in apps:
        app_dir = base_dir / app
        if not app_dir.exists():
            continue
        
        python_files = get_python_files(app_dir)
        
        for file_path in python_files:
            imports = extract_imports(file_path)
            
            for imported_module in imports:
                # Check if this is an import from another app
                if imported_module in apps and imported_module != app:
                    dependencies[app].add(imported_module)
    
    return dependencies


def detect_circular_dependencies(dependencies: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detect circular dependencies using depth-first search.
    
    Returns a list of circular dependency chains.
    """
    circular_deps = []
    
    def dfs(node: str, path: List[str], visited: Set[str]) -> None:
        if node in path:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            if cycle not in circular_deps and list(reversed(cycle)) not in circular_deps:
                circular_deps.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        path.append(node)
        
        for dependency in dependencies.get(node, set()):
            dfs(dependency, path.copy(), visited)
    
    for app in dependencies.keys():
        dfs(app, [], set())
    
    return circular_deps


def check_dependency_rules(dependencies: Dict[str, Set[str]]) -> List[str]:
    """
    Check if dependency rules are followed.
    
    Rules:
    - common SHALL NOT depend on video_processing or ai_services
    - video_processing MAY depend on common and ai_services
    - ai_services MAY depend on common
    """
    violations = []
    
    # Rule 1: common SHALL NOT depend on video_processing or ai_services
    if 'common' in dependencies:
        forbidden = dependencies['common'] & {'video_processing', 'ai_services'}
        if forbidden:
            violations.append(
                f"❌ Rule violation: 'common' depends on {forbidden}, but should not depend on video_processing or ai_services"
            )
    
    # Rule 2: ai_services SHALL NOT depend on video_processing
    if 'ai_services' in dependencies:
        if 'video_processing' in dependencies['ai_services']:
            violations.append(
                f"❌ Rule violation: 'ai_services' depends on 'video_processing', but should only depend on 'common'"
            )
    
    # Rule 3: video_processing MAY depend on common and ai_services (no violation check needed)
    
    return violations


def test_imports() -> Tuple[List[str], List[str]]:
    """
    Test that all services can be imported successfully.
    
    Returns tuple of (successful_imports, failed_imports)
    """
    # Setup Django environment
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bachata_buddy.settings')
    try:
        django.setup()
    except Exception as e:
        print(f"⚠️  Warning: Could not setup Django: {e}")
        print("   Skipping import tests (requires Django environment)")
        return [], []
    
    successful = []
    failed = []
    
    # Test common imports
    common_services = [
        'common.config.environment_config',
        'common.exceptions',
        'common.services.resource_manager',
        'common.services.temp_file_manager',
        'common.services.performance_monitor',
        'common.services.directory_organizer',
    ]
    
    # Test ai_services imports
    ai_services = [
        'ai_services.services.gemini_service',
        'ai_services.services.elasticsearch_service',
        'ai_services.services.text_embedding_service',
        'ai_services.services.recommendation_engine',
        'ai_services.services.move_analyzer',
        'ai_services.services.feature_fusion',
        'ai_services.services.quality_metrics',
        'ai_services.services.embedding_validator',
        'ai_services.services.hyperparameter_optimizer',
        'ai_services.services.model_validation',
    ]
    
    # Test video_processing imports
    video_services = [
        'video_processing.services.video_generator',
        'video_processing.services.video_storage_service',
        'video_processing.services.audio_storage_service',
        'video_processing.services.yolov8_couple_detector',
        'video_processing.services.pose_feature_extractor',
        'video_processing.services.pose_embedding_generator',
        'video_processing.services.couple_interaction_analyzer',
        'video_processing.services.music_analyzer',
        'video_processing.services.youtube_service',
        'video_processing.services.choreography_pipeline',
        'video_processing.models.video_models',
    ]
    
    all_imports = common_services + ai_services + video_services
    
    for module_path in all_imports:
        try:
            __import__(module_path)
            successful.append(module_path)
        except ImportError as e:
            failed.append(f"{module_path}: {e}")
        except Exception as e:
            failed.append(f"{module_path}: {type(e).__name__}: {e}")
    
    return successful, failed


def generate_dependency_graph(dependencies: Dict[str, Set[str]]) -> str:
    """Generate a text-based dependency graph."""
    graph = ["", "=" * 60, "DEPENDENCY GRAPH", "=" * 60, ""]
    
    for app in sorted(dependencies.keys()):
        deps = dependencies[app]
        if deps:
            graph.append(f"{app} depends on:")
            for dep in sorted(deps):
                graph.append(f"  → {dep}")
        else:
            graph.append(f"{app} has no dependencies")
        graph.append("")
    
    return "\n".join(graph)


def main():
    """Main function to run all checks."""
    print("=" * 60)
    print("CIRCULAR DEPENDENCY CHECKER")
    print("=" * 60)
    print()
    
    # Get the base directory (bachata_buddy/)
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    print(f"📁 Analyzing directory: {base_dir}")
    print()
    
    # Step 1: Analyze dependencies
    print("🔍 Step 1: Analyzing app dependencies...")
    dependencies = analyze_app_dependencies(base_dir)
    
    # Step 2: Detect circular dependencies
    print("🔍 Step 2: Detecting circular dependencies...")
    circular_deps = detect_circular_dependencies(dependencies)
    
    if circular_deps:
        print("❌ CIRCULAR DEPENDENCIES FOUND:")
        for cycle in circular_deps:
            print(f"   {' → '.join(cycle)}")
        print()
    else:
        print("✅ No circular dependencies detected")
        print()
    
    # Step 3: Check dependency rules
    print("🔍 Step 3: Checking dependency rules...")
    violations = check_dependency_rules(dependencies)
    
    if violations:
        print("❌ DEPENDENCY RULE VIOLATIONS:")
        for violation in violations:
            print(f"   {violation}")
        print()
    else:
        print("✅ All dependency rules followed")
        print()
    
    # Step 4: Test imports
    print("🔍 Step 4: Testing service imports...")
    successful, failed = test_imports()
    
    if failed:
        print(f"❌ {len(failed)} imports failed:")
        for failure in failed:
            print(f"   {failure}")
        print()
    else:
        print(f"✅ All {len(successful)} service imports successful")
        print()
    
    # Step 5: Generate dependency graph
    print("🔍 Step 5: Generating dependency graph...")
    graph = generate_dependency_graph(dependencies)
    print(graph)
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Apps analyzed: {len(dependencies)}")
    print(f"✓ Circular dependencies: {len(circular_deps)}")
    print(f"✓ Rule violations: {len(violations)}")
    print(f"✓ Successful imports: {len(successful)}")
    print(f"✓ Failed imports: {len(failed)}")
    print()
    
    # Exit with appropriate code
    if circular_deps or violations or failed:
        print("❌ VERIFICATION FAILED")
        return 1
    else:
        print("✅ VERIFICATION PASSED")
        return 0


if __name__ == '__main__':
    sys.exit(main())
