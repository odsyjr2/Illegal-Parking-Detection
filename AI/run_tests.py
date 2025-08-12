#!/usr/bin/env python3
"""
Quick Test Runner for AI Processor
Demonstrates the two main test scenarios:
1. Visual multi-stream CCTV detection 
2. API communication testing
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

def print_banner(title):
    """Print a formatted banner"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def check_prerequisites():
    """Check if prerequisites are available"""
    print_banner("Checking Prerequisites")
    
    ai_server_path = Path(__file__).parent / "ai_server"
    if not ai_server_path.exists():
        print("❌ ai_server directory not found")
        return False
    
    config_path = Path(__file__).parent / "config"
    if not config_path.exists():
        print("❌ config directory not found")
        return False
        
    test_path = ai_server_path / "test"
    if not test_path.exists():
        print("❌ test directory not found")
        return False
    
    print("✅ All prerequisites found")
    return True

def run_visual_test():
    """Run visual multi-stream detection test"""
    print_banner("Visual Multi-Stream Detection Test")
    print("This will open 6 OpenCV windows showing CCTV streams with AI overlays")
    print("Features:")
    print("- Real-time vehicle tracking")
    print("- Parking violation detection")
    print("- Performance metrics")
    print("- Interactive controls (SPACE=pause, S=screenshot, Q=quit)")
    
    response = input("\nRun visual test? (y/n): ").strip().lower()
    if response == 'y':
        try:
            print("\n🚀 Starting visual test...")
            print("Note: This requires OpenCV and test video files")
            
            # Change to ai_server directory
            ai_server_path = Path(__file__).parent / "ai_server"
            
            # Run the visual test
            result = subprocess.run([
                sys.executable, "test/multi_stream_visualizer.py"
            ], cwd=ai_server_path, capture_output=False)
            
            if result.returncode == 0:
                print("✅ Visual test completed successfully")
            else:
                print("❌ Visual test failed")
                
        except Exception as e:
            print(f"❌ Error running visual test: {e}")
    else:
        print("⏭️ Skipping visual test")

def run_api_test():
    """Run API communication test"""
    print_banner("API Communication Test")
    print("This will test sending violation data to backend via REST API")
    print("Features:")
    print("- Mock Spring Boot server")
    print("- Violation data transmission")
    print("- API response validation")
    print("- End-to-end pipeline testing")
    
    response = input("\nRun API test? (y/n): ").strip().lower()
    if response == 'y':
        try:
            print("\n🚀 Starting API test...")
            print("This will start a mock backend server and test API communication")
            
            # Change to ai_server directory
            ai_server_path = Path(__file__).parent / "ai_server"
            
            # Run the integration test
            result = subprocess.run([
                sys.executable, "test/integration_tester.py"
            ], cwd=ai_server_path, capture_output=False)
            
            if result.returncode == 0:
                print("✅ API test completed successfully")
            else:
                print("❌ API test failed")
                
        except Exception as e:
            print(f"❌ Error running API test: {e}")
    else:
        print("⏭️ Skipping API test")

def run_quick_config_test():
    """Run quick configuration validation"""
    print_banner("Quick Configuration Test")
    
    try:
        ai_server_path = Path(__file__).parent / "ai_server"
        
        result = subprocess.run([
            sys.executable, "test/simple_test_config.py"
        ], cwd=ai_server_path, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Configuration test passed")
            print(result.stdout)
        else:
            print("❌ Configuration test failed")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error running config test: {e}")

def run_all_tests():
    """Run complete test suite"""
    print_banner("Complete Test Suite")
    print("Running all automated tests...")
    
    try:
        ai_server_path = Path(__file__).parent / "ai_server"
        
        # Add ai_server to Python path for imports
        sys.path.insert(0, str(ai_server_path))
        
        # Import and run test suite
        import test
        result = test.run_all_tests()
        
        if result == 0:
            print("✅ All automated tests passed")
        else:
            print("❌ Some tests failed")
            
    except Exception as e:
        print(f"❌ Error running test suite: {e}")

def show_cleanup_instructions():
    """Show file cleanup instructions"""
    print_banner("File Cleanup Instructions")
    print("After successful testing, you can clean up unnecessary files:")
    print()
    print("Files to DELETE (FastAPI legacy):")
    print("- AI/ai_server/response_models.py")
    print("- AI/ai_server/visualization_manager.py")
    print("- AI/ai_server/frame_processor.py")
    print()
    print("Run cleanup:")
    print("cd AI/ai_server")
    print("rm -f response_models.py visualization_manager.py frame_processor.py")
    print()
    
    response = input("Run cleanup now? (y/n): ").strip().lower()
    if response == 'y':
        ai_server_path = Path(__file__).parent / "ai_server"
        
        files_to_remove = [
            "response_models.py",
            "visualization_manager.py", 
            "frame_processor.py"
        ]
        
        removed_count = 0
        for file_name in files_to_remove:
            file_path = ai_server_path / file_name
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"✅ Removed {file_name}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Failed to remove {file_name}: {e}")
            else:
                print(f"⏭️ {file_name} not found (already removed)")
        
        print(f"\n🧹 Cleanup completed - {removed_count} files removed")
    else:
        print("⏭️ Skipping cleanup")

def main():
    """Main test runner"""
    print_banner("AI Processor Test Runner")
    print("Choose testing options:")
    print("1. Visual Multi-Stream Detection Test (OpenCV windows)")
    print("2. API Communication Test (Mock backend)")
    print("3. Quick Configuration Test")
    print("4. Complete Test Suite")
    print("5. File Cleanup")
    print("6. Run All Tests (1,2,3)")
    print("0. Exit")
    
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please check AI directory structure.")
        return 1
    
    while True:
        try:
            choice = input("\nEnter choice (0-6): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                run_visual_test()
            elif choice == "2":
                run_api_test()
            elif choice == "3":
                run_quick_config_test()
            elif choice == "4":
                run_all_tests()
            elif choice == "5":
                show_cleanup_instructions()
            elif choice == "6":
                print_banner("Running All Main Tests")
                run_quick_config_test()
                run_visual_test()
                run_api_test()
                print_banner("All Tests Completed")
            else:
                print("❌ Invalid choice. Please enter 0-6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Test runner interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())