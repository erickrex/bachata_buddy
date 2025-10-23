#!/usr/bin/env python3
"""
Test API connections for Gemini and Elasticsearch.

This script verifies that both APIs are properly configured and working.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("API CONNECTION TEST")
print("=" * 70)
print()

# Test 1: Gemini API
print("1. Testing Gemini API...")
print("-" * 70)
try:
    from core.services.gemini_service import GeminiService, ChoreographyParameters
    
    service = GeminiService()
    print("✅ Gemini service initialized")
    
    # Test parsing
    print("\n   Testing query parsing...")
    params = service.parse_choreography_request(
        "Create a romantic beginner bachata with slow tempo"
    )
    print(f"   ✅ Parsed successfully:")
    print(f"      - Difficulty: {params.difficulty}")
    print(f"      - Style: {params.style}")
    print(f"      - Tempo: {params.tempo}")
    print(f"      - Energy: {params.energy_level}")
    
    # Test explanation
    print("\n   Testing explanation generation...")
    move = {
        'move_label': 'Cross-body Lead',
        'difficulty': 'beginner',
        'energy_level': 'medium'
    }
    context = {'parameters': params}
    explanation = service.explain_move_selection(move, context)
    print(f"   ✅ Explanation generated:")
    print(f"      {explanation[:100]}...")
    
    # Test suggestions
    print("\n   Testing suggestion generation...")
    metadata = {
        'difficulties': ['beginner', 'intermediate', 'advanced'],
        'styles': ['romantic', 'energetic', 'sensual', 'playful']
    }
    suggestions = service.suggest_alternatives('impossible query', metadata)
    print(f"   ✅ Suggestions generated:")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"      {i}. {suggestion}")
    
    print("\n✅ Gemini API: ALL TESTS PASSED")
    gemini_ok = True
    
except Exception as e:
    print(f"\n❌ Gemini API: FAILED")
    print(f"   Error: {e}")
    print(f"\n   Fix: Check GOOGLE_API_KEY in .env file")
    print(f"   Get key at: https://makersuite.google.com/app/apikey")
    gemini_ok = False

print()
print("=" * 70)
print()

# Test 2: Elasticsearch
print("2. Testing Elasticsearch...")
print("-" * 70)
try:
    from core.config.environment_config import EnvironmentConfig
    from core.services.elasticsearch_service import ElasticsearchService
    
    config = EnvironmentConfig()
    print(f"   Host: {config.elasticsearch.host}")
    print(f"   Port: {config.elasticsearch.port}")
    print(f"   Index: {config.elasticsearch.index_name}")
    print(f"   API Key: {config.elasticsearch.api_key[:20] if config.elasticsearch.api_key else 'None'}...")
    
    es = ElasticsearchService(config.elasticsearch)
    print("   ✅ Connected to Elasticsearch")
    
    # Test index operations
    print("\n   Testing index operations...")
    exists = es.index_exists()
    print(f"   Index exists: {exists}")
    
    if exists:
        count = es.count_documents()
        print(f"   ✅ Document count: {count}")
    else:
        print(f"   ℹ️  Index doesn't exist yet (will be created on upload)")
    
    print("\n✅ Elasticsearch: ALL TESTS PASSED")
    elasticsearch_ok = True
    
except Exception as e:
    print(f"\n❌ Elasticsearch: FAILED")
    print(f"   Error: {e}")
    print(f"\n   Fix: Check ELASTICSEARCH_HOST and ELASTICSEARCH_API_KEY in .env")
    print(f"   Get credentials at: https://cloud.elastic.co/")
    elasticsearch_ok = False

print()
print("=" * 70)
print()

# Summary
print("SUMMARY")
print("=" * 70)
print(f"Gemini API:      {'✅ WORKING' if gemini_ok else '❌ FAILED'}")
print(f"Elasticsearch:   {'✅ WORKING' if elasticsearch_ok else '❌ FAILED'}")
print()

if gemini_ok and elasticsearch_ok:
    print("🎉 All APIs are working! You're ready to:")
    print("   1. Upload embeddings: uv run python scripts/upload_embeddings_to_cloud.py")
    print("   2. Start server: uv run python manage.py runserver")
    print("   3. Test AI template: http://localhost:8000/choreography/describe-choreo/")
    sys.exit(0)
else:
    print("⚠️  Some APIs are not working. Please fix the issues above.")
    sys.exit(1)
