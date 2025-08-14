#!/usr/bin/env python3
"""
Configuration verification script for Korean ITS API integration
"""

import json
import requests
from pathlib import Path
import sys
import yaml

# Add AI server path
sys.path.append(str(Path(__file__).parent / "ai_server"))

def load_config_direct():
    """Load configuration directly from YAML files without environment validation"""
    config_dir = Path(__file__).parent / "config"
    
    # Load streams.yaml directly
    streams_config_path = config_dir / "streams.yaml"
    if streams_config_path.exists():
        with open(streams_config_path, 'r', encoding='utf-8') as f:
            streams_config = yaml.safe_load(f)
    else:
        streams_config = {}
    
    # Create minimal config structure
    config = {
        'cctv_streams': streams_config.get('cctv_streams', {}),
        'backend': {
            'url': 'http://localhost:8080',  # Default for testing
            'timeout': 30
        }
    }
    
    return config

def verify_configuration():
    """Verify all configuration settings"""
    print("🔍 Verifying Korean ITS API Integration Configuration...")
    print("=" * 60)
    
    try:
        # Load configuration directly (bypassing environment validation)
        config = load_config_direct()
        
        # Check Korean ITS API configuration
        its_config = config.get('cctv_streams', {}).get('live_streams', {}).get('its_api', {})
        
        print(f"📡 API Base URL: {its_config.get('base_url', 'NOT SET')}")
        print(f"🔑 API Key: {'SET' if its_config.get('api_key') else 'NOT SET'}")
        print(f"🌍 Geo Bounds: {its_config.get('default_bounds', 'NOT SET')}")
        print(f"⚙️ CCTV Type: {its_config.get('cctv_type', 'NOT SET')}")
        print(f"🎚️ Live Streams Enabled: {config.get('cctv_streams', {}).get('live_streams', {}).get('enabled', False)}")
        
        # Test API connection
        print("\n🧪 Testing Korean ITS API Connection...")
        api_url = its_config.get('base_url')
        api_key = its_config.get('api_key')
        
        if api_url and api_key:
            test_params = {
                'apiKey': api_key,
                'type': 'its',
                'cctvType': 4,
                'minX': 126.8,
                'maxX': 126.9,
                'minY': 37.5,
                'maxY': 37.6,
                'getType': 'json'
            }
            
            try:
                response = requests.get(api_url, params=test_params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    cctv_count = len(data.get('response', {}).get('data', []))
                    print(f"✅ API Connection Success! Found {cctv_count} CCTV streams")
                    
                    # Show first stream as example
                    if cctv_count > 0:
                        first_cctv = data['response']['data'][0]
                        print(f"📹 Example CCTV: {first_cctv.get('cctvname', 'Unknown')}")
                        print(f"🔗 Stream URL: {first_cctv.get('cctvurl', 'Unknown')[:50]}...")
                        
                        # Test a single stream connection
                        print(f"\n🎥 Testing Stream Connection...")
                        test_stream_url = first_cctv.get('cctvurl', '')
                        if test_stream_url:
                            import cv2
                            cap = cv2.VideoCapture(test_stream_url)
                            if cap.isOpened():
                                ret, frame = cap.read()
                                if ret and frame is not None:
                                    print(f"✅ Stream Connection Success! Frame shape: {frame.shape}")
                                else:
                                    print("⚠️ Stream opened but no frame received")
                                cap.release()
                            else:
                                print("❌ Failed to open stream")
                        
                elif response.status_code == 401:
                    print("❌ API Authentication Failed - Check your API key")
                elif response.status_code == 403:
                    print("❌ API Access Forbidden - Check API key permissions")
                else:
                    print(f"❌ API Connection Failed: HTTP {response.status_code}")
                    print(f"Response: {response.text[:200]}...")
            except requests.RequestException as e:
                print(f"❌ API Request Failed: {e}")
        else:
            print("❌ API URL or Key not configured properly")
        
        # Backend configuration (optional for testing)
        print(f"\n🔧 Backend Configuration (Optional for Testing):")
        backend_config = config.get('backend', {})
        backend_url = backend_config.get('url', 'http://localhost:8080')
        print(f"🌐 Backend URL: {backend_url}")
        
        # Test backend connection (optional)
        print("🧪 Testing Backend Connection (Optional)...")
        try:
            health_response = requests.get(f"{backend_url}/actuator/health", timeout=3)
            if health_response.status_code == 200:
                print("✅ Backend Connection Success!")
            else:
                print(f"⚠️ Backend Response: HTTP {health_response.status_code}")
        except requests.RequestException:
            print("⚠️ Backend Connection Failed - Backend not running (OK for API-only testing)")
        
        print("\n" + "=" * 60)
        print("✅ Configuration verification complete!")
        print("💡 You can test Korean ITS API integration without backend server")
        
    except Exception as e:
        print(f"❌ Configuration verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_configuration()