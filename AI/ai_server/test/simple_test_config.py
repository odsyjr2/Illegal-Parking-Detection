#!/usr/bin/env python3
"""
Simple Configuration Test Script

Tests basic configuration loading functionality.
"""

import os
import sys
from pathlib import Path

# Add the ai_server directory to Python path (parent of test directory)
sys.path.append(str(Path(__file__).parent.parent))

def main():
    print("Testing Configuration System...")
    
    # Set required environment variable
    os.environ["BACKEND_URL"] = "http://localhost:8080"
    
    try:
        # Test imports
        print("1. Testing imports...")
        from utils.config_loader import ConfigLoader, load_config
        from utils.logger import setup_logging
        from models import ModelConfig, ProcessingConfig
        print("   [OK] Imports successful")
        
        # Test configuration loading
        print("2. Testing configuration loading...")
        config = load_config()
        print("   [OK] Configuration loaded successfully")
        
        # Test configuration structure
        print("3. Testing configuration structure...")
        expected_sections = ["application", "backend", "logging", "vehicle_detection", 
                           "illegal_parking", "monitoring", "analysis", "cctv_streams"]
        
        for section in expected_sections:
            if section in config:
                print(f"   [OK] Found section: {section}")
            else:
                print(f"   [WARN] Missing section: {section}")
        
        # Test specific values
        print("4. Testing specific configuration values...")
        backend_url = config.get("backend", {}).get("url", "Not found")
        print(f"   Backend URL: {backend_url}")
        
        worker_pool = config.get("analysis", {}).get("worker_pool_size", "Not found")
        print(f"   Worker pool size: {worker_pool}")
        
        streams = config.get("cctv_streams", {}).get("local_streams", [])
        print(f"   Number of streams: {len(streams)}")
        
        # Test logging setup
        print("5. Testing logging setup...")
        logging_config = config.get("logging", {})
        logging_system = setup_logging(logging_config)
        print("   [OK] Logging system initialized")
        
        # Test data models
        print("6. Testing data models...")
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
        
        print("\n[SUCCESS] All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())