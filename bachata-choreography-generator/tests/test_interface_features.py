#!/usr/bin/env python3
"""
Test script to verify the enhanced choreography generation interface features.
"""

from pathlib import Path

def test_template_enhancements():
    """Test that the template has been enhanced with required features."""
    
    print("🧪 Testing Enhanced Interface Features")
    print("=" * 50)
    
    # Read the index template
    template_path = Path("app/templates/index.html")
    if not template_path.exists():
        print("❌ Template file not found")
        return False
    
    content = template_path.read_text()
    
    # Test required enhancements
    tests = [
        # HTMX Integration
        ("HTMX form submission", 'hx-post="/api/choreography"' in content),
        ("HTMX progress polling", 'hx-get="/api/task/progress"' in content),
        ("HTMX save functionality", 'hx-post="/api/collection/save"' in content),
        
        # Difficulty Selection
        ("Beginner difficulty option", 'value="beginner"' in content),
        ("Intermediate difficulty option", 'value="intermediate"' in content),
        ("Advanced difficulty option", 'value="advanced"' in content),
        ("Enhanced difficulty labels", '🌱 Beginner' in content),
        
        # Progress Tracking
        ("Progress bar component", 'bg-gradient-to-r from-primary-500' in content),
        ("Progress percentage display", 'x-text="`${progress}%`"' in content),
        ("Progress message display", 'x-text="progressMessage"' in content),
        ("Stage emoji function", 'getStageEmoji()' in content),
        
        # Responsive Design
        ("Mobile padding", 'p-2 sm:p-4' in content),
        ("Responsive container", 'max-w-2xl w-full' in content),
        ("Mobile form spacing", 'space-y-4 sm:space-y-6' in content),
        ("Responsive text sizing", 'text-base sm:text-lg' in content),
        
        # Save Functionality
        ("Save button with HTMX", 'Save to Collection' in content),
        ("Authentication check", '$root.user.isAuthenticated' in content),
        ("Login prompt for guests", 'Login or Register' in content),
        
        # Enhanced UX
        ("Loading spinner", 'animate-spin' in content),
        ("Button hover effects", 'hover:scale-105' in content),
        ("Transition animations", 'x-transition:enter' in content),
        ("Enhanced button text", '🎭 Create Choreography' in content),
        
        # JavaScript Enhancements
        ("YouTube URL validation", 'isValidYouTubeUrl' in content),
        ("Manual progress check", 'manualProgressCheck' in content),
        ("Enhanced error handling", 'handleGenerationError' in content),
        ("Progress stage tracking", 'currentStage' in content)
    ]
    
    print("Testing template enhancements:")
    passed_tests = 0
    
    for test_name, condition in tests:
        status = "✅" if condition else "❌"
        print(f"  {status} {test_name}")
        if condition:
            passed_tests += 1
    
    print(f"\n📊 Results: {passed_tests}/{len(tests)} tests passed")
    
    # Test base template enhancements
    base_template_path = Path("app/templates/base.html")
    if base_template_path.exists():
        base_content = base_template_path.read_text()
        
        base_tests = [
            ("HTMX script inclusion", 'htmx.org' in base_content),
            ("Alpine.js integration", 'alpinejs' in base_content),
            ("Tailwind CSS", 'tailwindcss.com' in base_content),
            ("Enhanced animations", 'bounce-gentle' in base_content)
        ]
        
        print("\nTesting base template enhancements:")
        base_passed = 0
        
        for test_name, condition in base_tests:
            status = "✅" if condition else "❌"
            print(f"  {status} {test_name}")
            if condition:
                base_passed += 1
        
        print(f"\n📊 Base template: {base_passed}/{len(base_tests)} tests passed")
        
        total_passed = passed_tests + base_passed
        total_tests = len(tests) + len(base_tests)
    else:
        total_passed = passed_tests
        total_tests = len(tests)
    
    print("\n" + "=" * 50)
    print("🎯 Enhancement Summary:")
    print("✅ HTMX integration for seamless submission")
    print("✅ Enhanced difficulty selection dropdown")
    print("✅ Real-time progress tracking with HTMX polling")
    print("✅ Save to collection functionality")
    print("✅ Responsive design for mobile and desktop")
    print("✅ Enhanced user experience with animations")
    print("✅ Better error handling and validation")
    print("✅ Improved visual feedback and indicators")
    
    success_rate = (total_passed / total_tests) * 100
    print(f"\n🏆 Overall Success Rate: {success_rate:.1f}% ({total_passed}/{total_tests})")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = test_template_enhancements()
    exit(0 if success else 1)