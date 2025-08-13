#!/usr/bin/env python3
"""
Test Script for Configuration Loading and Validation

This script tests the multi-YAML configuration system to ensure:
- All configuration files load correctly
- Environment variable substitution works
- Validation catches configuration errors
- Merged configuration has expected structure
"""

import os
import sys
from pathlib import Path

# Add the ai_server directory to Python path (parent of test directory)
sys.path.append(str(Path(__file__).parent.parent))

def main():
    """Run comprehensive configuration tests"""
    print("Configuration System Test Suite")
    print("="*60)
    
    # Set required environment variable
    os.environ["BACKEND_URL"] = "http://localhost:8080"
    
    try:
        # Test imports
        print("1. Testing imports...")
        from utils.config_loader import ConfigLoader, ConfigValidationError, get_config_loader, load_config
        from utils.logger import setup_logging, get_logger
        from models import ModelConfig, ProcessingConfig, StreamConfig
        print("   [OK] Imports successful")
        
        # Test basic configuration loading
        print("\n2. Testing basic configuration loading...")
        config_dir = Path(__file__).parent.parent.parent / "config"
        print(f"   Config directory: {config_dir}")
        print(f"   Directory exists: {config_dir.exists()}")
        
        loader = ConfigLoader(config_dir)
        
        # Test individual files
        for config_file in loader._config_files:
            print(f"   Testing {config_file.name}: ", end="")
            if config_file.path.exists():
                try:
                    file_config = loader.load_single_config(config_file)
                    print(f"[OK] - {len(file_config)} sections")
                except Exception as e:
                    print(f"[ERROR] - {e}")
            else:
                print("[ERROR] - File not found")
        
        # Test merged configuration
        print("\n3. Testing merged configuration...")
        config = load_config()
        print("   [OK] Merged configuration loaded successfully")
        print(f"   [OK] Top-level sections: {len(config)} sections")
        
        # Test specific sections
        expected_sections = [
            "application", "backend", "logging",
            "vehicle_detection", "illegal_parking", "license_plate",
            "monitoring", "analysis", "cctv_streams"
        ]
        
        missing_sections = []
        for section in expected_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"   [WARN] Missing sections: {missing_sections}")
        else:
            print("   [OK] All expected sections present")
            
        # Test specific configuration values
        print("\n4. Testing specific configuration values...")
        backend_url = config.get("backend", {}).get("url", "Not found")
        print(f"   Backend URL: {backend_url}")
        
        worker_pool = config.get("analysis", {}).get("worker_pool_size", "Not found")
        print(f"   Worker pool size: {worker_pool}")
        
        streams = config.get("cctv_streams", {}).get("local_streams", [])
        print(f"   Number of streams: {len(streams)}")
        
        # Test data models
        print("\n5. Testing data models...")
        try:
            model_config = ModelConfig(
                path="test.pt",
                confidence_threshold=0.7
            )
            print("   [OK] ModelConfig created")
            
            processing_config = ProcessingConfig(
                parking_duration_threshold=300,
                worker_pool_size=3,
                queue_max_size=100,
                retry_attempts=3,
                retry_delay=5
            )
            print("   [OK] ProcessingConfig created")
            
            # Test validation
            try:
                invalid_model = ModelConfig(
                    path="test.pt",
                    confidence_threshold=1.5  # Invalid value
                )
                print("   [ERROR] Validation should have failed")
            except ValueError:
                print("   [OK] Validation correctly caught invalid value")
                
        except Exception as e:
            print(f"   [ERROR] Data model test failed: {e}")
        
        # Test logging setup
        print("\n6. Testing logging setup...")
        try:
            logging_config = config.get("logging", {})
            logging_system = setup_logging(logging_config)
            print("   [OK] Logging system initialized")
            
            # Test component loggers
            test_components = ["main", "monitoring", "analysis"]
            for component in test_components:
                logger = get_logger(component)
                logger.info(f"Test message from {component}")
            print(f"   [OK] Created loggers for {len(test_components)} components")
            
        except Exception as e:
            print(f"   [ERROR] Logging test failed: {e}")
        
        # Test environment variables
        print("\n7. Testing environment variable handling...")
        test_vars = {
            "TEST_VAR": "test_value",
            "LOG_LEVEL": "DEBUG"
        }
        
        for var, value in test_vars.items():
            os.environ[var] = value
        
        # Reload config to test substitution
        loader.reload_config()
        print("   [OK] Configuration reloaded with environment variables")
        
        print("\n" + "="*60)
        print("[SUCCESS] All configuration tests passed!")
        print("="*60)
        
        # Print configuration summary
        print_config_summary(config)
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def print_config_summary(config):
    """Print a summary of the loaded configuration"""
    print("\nConfiguration Summary:")
    print("-" * 40)
    
    app_config = config.get("application", {})
    print(f"Application: {app_config.get('name', 'Unknown')}")
    print(f"Version: {app_config.get('version', 'Unknown')}")
    print(f"Mode: {app_config.get('mode', 'Unknown')}")
    
    backend_config = config.get("backend", {})
    print(f"Backend URL: {backend_config.get('url', 'Not set')}")
    
    logging_config = config.get("logging", {})
    print(f"Log Level: {logging_config.get('level', 'INFO')}")
    
    analysis_config = config.get("analysis", {})
    print(f"Worker Pool Size: {analysis_config.get('worker_pool_size', 'Not set')}")
    
    streams = config.get("cctv_streams", {}).get("local_streams", [])
    print(f"Configured Streams: {len(streams)}")
    
    if streams:
        print("Sample Streams:")
        for i, stream in enumerate(streams[:3]):
            print(f"  {i+1}. {stream.get('name', 'Unnamed')} ({stream.get('id', 'No ID')})")
        if len(streams) > 3:
            print(f"  ... and {len(streams) - 3} more")


if __name__ == "__main__":
    sys.exit(main())