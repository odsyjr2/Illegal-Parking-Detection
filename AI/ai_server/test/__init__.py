"""
Test Package for AI Processor

This package contains comprehensive test utilities and test scripts for:
- Configuration system testing and validation
- Visual multi-stream processing testing with OpenCV windows
- Performance testing with concurrent streams and resource monitoring
- End-to-end integration testing with mock backend
- System validation and quality assurance

Test Modules:
- simple_test_config.py: Basic configuration system validation
- test_config.py: Comprehensive configuration system test with validation
- multi_stream_visualizer.py: Visual testing framework with 6 OpenCV windows
- performance_tester.py: Performance testing with 1-6 concurrent streams
- integration_tester.py: End-to-end pipeline testing with mock backend

Visual Testing Features:
- Real-time display of 6 CCTV streams with AI overlays
- Vehicle tracking visualization with bounding boxes and IDs
- Parking violation detection with visual alerts
- Interactive controls for pause/resume, screenshots, statistics
- Performance metrics display (FPS, processing times, violations)

Performance Testing Features:
- Progressive load testing (1-6 streams)
- Resource monitoring (CPU, memory, GPU usage)
- Performance bottleneck identification
- Comprehensive reporting with charts and statistics

Integration Testing Features:
- Complete pipeline validation (monitoring → analysis → reporting)
- Mock backend server for API testing
- Error handling and recovery validation
- Data integrity checks throughout workflow
"""

import sys
import asyncio
from pathlib import Path

# Ensure ai_server modules can be imported from test scripts
_ai_server_path = Path(__file__).parent.parent
if str(_ai_server_path) not in sys.path:
    sys.path.insert(0, str(_ai_server_path))

# Import test modules
try:
    from .simple_test_config import main as simple_test_main
    from .test_config import main as comprehensive_test_main
    from .multi_stream_visualizer import main as visual_test_main
    from .performance_tester import main as performance_test_main
    from .integration_tester import main as integration_test_main
    
    __all__ = [
        'simple_test_main', 'comprehensive_test_main', 'visual_test_main',
        'performance_test_main', 'integration_test_main',
        'run_simple_test', 'run_comprehensive_test', 'run_visual_test',
        'run_performance_test', 'run_integration_test', 'run_all_tests'
    ]
except ImportError as e:
    print(f"Warning: Some test modules could not be imported: {e}")
    __all__ = []

def run_simple_test():
    """Run the simple configuration system test"""
    try:
        from .simple_test_config import main as test_main
        return test_main()
    except ImportError as e:
        print(f"Failed to import simple configuration test: {e}")
        return 1

def run_comprehensive_test():
    """Run the comprehensive configuration system test"""
    try:
        from .test_config import main as test_main
        return test_main()
    except ImportError as e:
        print(f"Failed to import comprehensive configuration test: {e}")
        return 1

def run_visual_test():
    """Run the multi-stream visual demonstration"""
    try:
        from .multi_stream_visualizer import main as test_main
        return asyncio.run(test_main())
    except ImportError as e:
        print(f"Failed to import visual test: {e}")
        return 1
    except Exception as e:
        print(f"Visual test failed: {e}")
        return 1

def run_performance_test():
    """Run the performance testing suite"""
    try:
        from .performance_tester import main as test_main
        return asyncio.run(test_main())
    except ImportError as e:
        print(f"Failed to import performance test: {e}")
        return 1
    except Exception as e:
        print(f"Performance test failed: {e}")
        return 1

def run_integration_test():
    """Run the integration testing suite"""
    try:
        from .integration_tester import main as test_main
        return asyncio.run(test_main())
    except ImportError as e:
        print(f"Failed to import integration test: {e}")
        return 1
    except Exception as e:
        print(f"Integration test failed: {e}")
        return 1

def run_all_tests():
    """Run all available tests in sequence"""
    print("Running All Tests for Illegal Parking Detection System")
    print("=" * 60)
    
    tests = [
        ("Configuration Tests", [run_simple_test, run_comprehensive_test]),
        ("Integration Tests", [run_integration_test]),
        ("Performance Tests", [run_performance_test])
        # Note: Visual test is interactive and should be run separately
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_category, test_functions in tests:
        print(f"\n{test_category}:")
        print("-" * len(test_category))
        
        for test_func in test_functions:
            total_tests += 1
            try:
                result = test_func()
                if result == 0:
                    print(f"[PASS] {test_func.__name__}")
                    passed_tests += 1
                else:
                    print(f"[FAIL] {test_func.__name__}")
            except Exception as e:
                print(f"[ERROR] {test_func.__name__}: {e}")
    
    print(f"\nTest Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("[SUCCESS] All automated tests passed!")
        print("\nTo run the visual demonstration:")
        print("  python test/multi_stream_visualizer.py")
        return 0
    else:
        print(f"[WARNING] {total_tests - passed_tests} tests failed")
        return 1

def list_available_tests():
    """List all available test modules with their status"""
    available_tests = []
    
    test_files = [
        ("simple_test_config", "Basic configuration system validation", True),
        ("test_config", "Comprehensive configuration system test", True),
        ("multi_stream_visualizer", "Visual testing with 6 OpenCV windows", True),
        ("performance_tester", "Performance testing with concurrent streams", True),
        ("integration_tester", "End-to-end pipeline testing", True)
    ]
    
    for test_name, description, implemented in test_files:
        test_path = Path(__file__).parent / f"{test_name}.py"
        if test_path.exists() and implemented:
            available_tests.append((test_name, description, "Available"))
        elif implemented:
            available_tests.append((test_name, description, "Missing"))
        else:
            available_tests.append((test_name, description, "Not implemented"))
    
    return available_tests

def print_test_help():
    """Print help information for running tests"""
    print("AI Processor Test Package - Help")
    print("=" * 40)
    print()
    print("Available Test Categories:")
    print("  1. Configuration Tests - Validate YAML configuration system")
    print("  2. Visual Tests - Interactive demonstration with OpenCV windows")
    print("  3. Performance Tests - System performance with concurrent streams")
    print("  4. Integration Tests - End-to-end pipeline validation")
    print()
    print("Quick Start:")
    print("  # Run all automated tests")
    print("  python -c \"import test; test.run_all_tests()\"")
    print()
    print("  # Run visual demonstration (interactive)")
    print("  python test/multi_stream_visualizer.py")
    print()
    print("  # Run individual tests")
    print("  python test/simple_test_config.py")
    print("  python test/test_config.py")
    print("  python test/performance_tester.py")
    print("  python test/integration_tester.py")
    print()
    print("Test Requirements:")
    print("  - Configuration files in AI/config/ directory")
    print("  - Test video data in data/test_videos/ directory")
    print("  - OpenCV for visual tests")
    print("  - Matplotlib for performance charts")
    print("  - Flask for integration tests (mock backend)")
    print()

if __name__ == "__main__":
    print("AI Processor Test Package")
    print("=" * 40)
    
    tests = list_available_tests()
    print("\nAvailable Tests:")
    for name, description, status in tests:
        status_icon = "[OK]" if status == "Available" else "[MISSING]"
        print(f"  {status_icon} {name}: {description} [{status}]")
    
    print("\nUsage Options:")
    print("  1. Run all automated tests: python -c \"import test; test.run_all_tests()\"")
    print("  2. Run visual demo: python test/multi_stream_visualizer.py") 
    print("  3. Run individual tests: python test/<test_name>.py")
    print("  4. Get help: python -c \"import test; test.print_test_help()\"")
    
    available_count = len([t for t in tests if t[2] == "Available"])
    total_count = len(tests)
    
    print(f"\nTest Suite Status: {available_count}/{total_count} tests available")
    
    if available_count == total_count:
        print("[SUCCESS] All test modules are ready!")
    else:
        missing_tests = [t[0] for t in tests if t[2] != "Available"]
        print(f"[WARNING] Missing tests: {', '.join(missing_tests)}")