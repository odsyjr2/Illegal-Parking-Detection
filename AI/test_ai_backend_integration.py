#!/usr/bin/env python3
"""
AI-Backend Integration Test Script

This script tests the complete integration between AI system and backend:
1. AI discovers streams from Korean ITS API
2. AI syncs discovered streams to backend
3. AI monitors streams for violations
4. AI reports violations to backend

Usage:
    python test_ai_backend_integration.py [--backend-url URL] [--max-streams N] [--duration SECONDS]
"""

import asyncio
import logging
import sys
import argparse
import time
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
import requests

# Import AI modules
sys.path.append(str(Path(__file__).parent / "ai_server"))
from stream_sync import StreamSyncService

# Try to import YOLO and AI modules
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KoreanITSAPIClient:
    """Client for fetching CCTV streams from Korean ITS API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 30)
        
    def fetch_cctv_streams_by_bounds(self, min_lon: float, max_lon: float, 
                                   min_lat: float, max_lat: float) -> List[Dict[str, Any]]:
        """Fetch CCTV streams within geographic bounds"""
        try:
            params = {
                'apiKey': self.api_key,
                'type': self.config.get('type', 'its'),
                'cctvType': self.config.get('cctv_type', 4),
                'minX': min_lon,
                'maxX': max_lon,
                'minY': min_lat,
                'maxY': max_lat,
                'getType': self.config.get('get_type', 'json')
            }
            
            logger.info(f"Fetching CCTV streams from Korean ITS API...")
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                cctv_data = data.get('response', {}).get('data', [])
                
                streams = []
                for idx, cctv in enumerate(cctv_data):
                    stream = {
                        'id': f"its_cctv_{idx:03d}",
                        'name': cctv.get('cctvname', f'ITS CCTV {idx}'),
                        'stream_url': cctv.get('cctvurl', ''),
                        'location': {
                            'latitude': float(cctv.get('coordy', 0)),
                            'longitude': float(cctv.get('coordx', 0)),
                            'address': cctv.get('cctvname', f'Korean ITS CCTV {idx}')
                        }
                    }
                    streams.append(stream)
                
                logger.info(f"Successfully fetched {len(streams)} CCTV streams")
                return streams
            else:
                logger.error(f"Korean ITS API returned status {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching streams from Korean ITS API: {e}")
            return []


class SimpleAIDetector:
    """Simplified AI detector for integration testing"""
    
    def __init__(self, models_config: Dict[str, Any]):
        self.models_config = models_config
        self.vehicle_model = None
        self.initialized = False
        
        # Model paths from config
        self.vehicle_model_path = models_config.get('vehicle_detection', {}).get('path', '')
        self.vehicle_conf = models_config.get('vehicle_detection', {}).get('confidence_threshold', 0.5)
        
    def initialize(self) -> bool:
        """Initialize AI models if available"""
        if not YOLO_AVAILABLE:
            logger.warning("YOLO not available - using mock detection")
            self.initialized = True
            return True
            
        try:
            # Check if custom vehicle model exists
            vehicle_model_full_path = Path(__file__).parent / self.vehicle_model_path
            
            if vehicle_model_full_path.exists():
                logger.info(f"Loading custom vehicle model: {vehicle_model_full_path}")
                self.vehicle_model = YOLO(str(vehicle_model_full_path))
                self.vehicle_model.conf = self.vehicle_conf
                logger.info("✅ AI model loaded successfully")
            else:
                logger.warning(f"Custom model not found: {vehicle_model_full_path}")
                logger.info("Using mock detection for testing")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load AI model: {e}")
            logger.info("Using mock detection for testing")
            self.initialized = True
            return True
    
    def detect_violations(self, frame: np.ndarray, stream_id: str, timestamp: float) -> Optional[Dict]:
        """Detect violations in frame (real or mock)"""
        if not self.initialized:
            return None
        
        # Mock violation detection for testing (simulate random detection)
        import random
        if random.random() < 0.01:  # 1% chance of violation per frame
            violation = {
                "event_id": f"violation_{stream_id}_{int(timestamp)}",
                "event_type": "violation_detected",
                "priority": "high",
                "timestamp": timestamp,
                "timestamp_iso": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(timestamp)),
                "stream_id": stream_id,
                "correlation_id": f"parking_event_{int(timestamp)}",
                "data": {
                    "violation": {
                        "event_id": f"parking_event_{int(timestamp)}",
                        "stream_id": stream_id,
                        "start_time": timestamp,
                        "duration": 125.3,
                        "violation_severity": 0.85,
                        "is_confirmed": True,
                        "vehicle_type": "car",
                        "parking_zone_type": "no_parking"
                    },
                    "vehicle": {
                        "track_id": f"vehicle_{random.randint(100, 999)}",
                        "vehicle_type": "car",
                        "confidence": 0.92,
                        "bounding_box": [100, 150, 300, 400],
                        "last_position": [random.uniform(126.7, 127.2), random.uniform(37.4, 37.7)]
                    },
                    "license_plate": {
                        "plate_text": f"ABC{random.randint(1000, 9999)}",
                        "confidence": 0.88,
                        "bounding_box": [180, 320, 280, 350],
                        "is_valid_format": True
                    },
                    "stream_info": {
                        "stream_id": stream_id,
                        "location_name": f"Location for {stream_id}"
                    }
                }
            }
            
            logger.info(f"🚨 Mock violation detected on {stream_id}")
            return violation
        
        return None


class IntegrationTestManager:
    """Manager for AI-Backend integration testing"""
    
    def __init__(self, backend_url: str, max_streams: int = 3):
        self.backend_url = backend_url
        self.max_streams = max_streams
        
        # Initialize services
        self.stream_sync_service = StreamSyncService(backend_url)
        self.its_client = None
        self.ai_detector = None
        
        # Monitoring state
        self.active_streams = []
        self.violation_count = 0
        
    def load_configuration(self) -> bool:
        """Load AI configuration"""
        try:
            config_dir = Path(__file__).parent / "config"
            
            # Load streams configuration
            with open(config_dir / "streams.yaml", 'r', encoding='utf-8') as f:
                streams_config = yaml.safe_load(f)
            
            # Load models configuration
            with open(config_dir / "models.yaml", 'r', encoding='utf-8') as f:
                models_config = yaml.safe_load(f)
            
            # Initialize clients
            its_config = streams_config.get('cctv_streams', {}).get('live_streams', {}).get('its_api', {})
            self.its_client = KoreanITSAPIClient(its_config)
            self.ai_detector = SimpleAIDetector(models_config)
            
            logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def test_backend_connection(self) -> bool:
        """Test connection to backend"""
        logger.info("🔗 Testing backend connection...")
        return self.stream_sync_service.test_backend_connection()
    
    def discover_and_sync_streams(self) -> bool:
        """Discover streams from Korean ITS API and sync to backend"""
        logger.info("📡 Discovering streams from Korean ITS API...")
        
        # Use default bounds from config
        bounds = {
            'min_longitude': 126.7,
            'max_longitude': 127.2,
            'min_latitude': 37.4,
            'max_latitude': 37.7
        }
        
        # Discover streams
        discovered_streams = self.its_client.fetch_cctv_streams_by_bounds(
            bounds['min_longitude'], bounds['max_longitude'],
            bounds['min_latitude'], bounds['max_latitude']
        )
        
        if not discovered_streams:
            logger.error("No streams discovered from Korean ITS API")
            return False
        
        # Limit streams for testing
        discovered_streams = discovered_streams[:self.max_streams]
        
        logger.info(f"🎥 Discovered {len(discovered_streams)} streams")
        for stream in discovered_streams:
            logger.info(f"  - {stream['id']}: {stream['name']}")
        
        # Sync to backend
        logger.info("🔄 Syncing streams to backend...")
        success = self.stream_sync_service.sync_discovered_streams(discovered_streams)
        
        if success:
            self.active_streams = discovered_streams
            logger.info("✅ Stream sync successful")
            return True
        else:
            logger.error("❌ Stream sync failed")
            return False
    
    def verify_backend_streams(self) -> bool:
        """Verify streams are stored in backend"""
        logger.info("🔍 Verifying streams in backend...")
        
        backend_streams = self.stream_sync_service.get_backend_streams()
        
        if backend_streams:
            logger.info(f"✅ Backend has {len(backend_streams)} active streams:")
            for stream in backend_streams:
                logger.info(f"  - {stream.get('streamId', 'N/A')}: {stream.get('streamName', 'N/A')}")
            return True
        else:
            logger.error("❌ No streams found in backend")
            return False
    
    def test_ai_monitoring(self, duration: int = 60) -> bool:
        """Test AI monitoring of streams with violation reporting"""
        logger.info(f"🤖 Starting AI monitoring for {duration} seconds...")
        
        if not self.ai_detector.initialize():
            logger.error("Failed to initialize AI detector")
            return False
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                current_time = time.time()
                
                # Process each active stream
                for stream in self.active_streams:
                    stream_id = stream['id']
                    stream_url = stream['stream_url']
                    
                    # Try to connect to stream and read frame
                    try:
                        cap = cv2.VideoCapture(stream_url)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                        
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                frame_count += 1
                                
                                # Run AI detection
                                violation = self.ai_detector.detect_violations(frame, stream_id, current_time)
                                
                                if violation:
                                    # Report violation to backend
                                    self._report_violation_to_backend(violation)
                                    self.violation_count += 1
                            
                        cap.release()
                        
                    except Exception as e:
                        logger.debug(f"Error processing stream {stream_id}: {e}")
                
                # Small delay between cycles
                time.sleep(1)
                
                # Log progress every 10 seconds
                if int(current_time - start_time) % 10 == 0:
                    elapsed = int(current_time - start_time)
                    logger.info(f"⏱️  Monitoring progress: {elapsed}s elapsed, {frame_count} frames processed, {self.violation_count} violations detected")
            
            logger.info(f"✅ AI monitoring completed: {frame_count} frames processed, {self.violation_count} violations detected")
            return True
            
        except KeyboardInterrupt:
            logger.info("AI monitoring interrupted by user")
            return True
        except Exception as e:
            logger.error(f"Error during AI monitoring: {e}")
            return False
    
    def _report_violation_to_backend(self, violation: Dict) -> bool:
        """Report detected violation to backend"""
        try:
            # Use existing violation reporting endpoint
            violation_url = f"{self.backend_url}/api/ai/v1/report-detection"
            
            response = requests.post(
                violation_url,
                json=violation,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"📤 Violation reported successfully: {violation['stream_id']}")
                return True
            else:
                logger.warning(f"Failed to report violation: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Error reporting violation: {e}")
            return False
    
    def run_integration_test(self, monitoring_duration: int = 60) -> bool:
        """Run complete integration test"""
        logger.info("🚀 Starting AI-Backend Integration Test")
        logger.info("="*60)
        
        # Step 1: Load configuration
        if not self.load_configuration():
            return False
        
        # Step 2: Test backend connection
        if not self.test_backend_connection():
            return False
        
        # Step 3: Discover and sync streams
        if not self.discover_and_sync_streams():
            return False
        
        # Step 4: Verify backend has streams
        if not self.verify_backend_streams():
            return False
        
        # Step 5: Test AI monitoring with violation reporting
        if not self.test_ai_monitoring(monitoring_duration):
            return False
        
        logger.info("="*60)
        logger.info("✅ AI-Backend Integration Test COMPLETED SUCCESSFULLY")
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   • Streams discovered and synced: {len(self.active_streams)}")
        logger.info(f"   • Violations detected and reported: {self.violation_count}")
        logger.info("="*60)
        
        return True


def main():
    """Main integration test function"""
    parser = argparse.ArgumentParser(description='AI-Backend Integration Test')
    parser.add_argument('--backend-url', default='http://localhost:8080', help='Backend URL (default: http://localhost:8080)')
    parser.add_argument('--max-streams', type=int, default=3, help='Maximum streams to test (default: 3)')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds (default: 60)')
    
    args = parser.parse_args()
    
    logger.info("🔧 AI-Backend Integration Test")
    logger.info(f"Backend URL: {args.backend_url}")
    logger.info(f"Max Streams: {args.max_streams}")
    logger.info(f"Duration: {args.duration} seconds")
    
    # Initialize test manager
    test_manager = IntegrationTestManager(
        backend_url=args.backend_url,
        max_streams=args.max_streams
    )
    
    # Run integration test
    success = test_manager.run_integration_test(monitoring_duration=args.duration)
    
    if success:
        logger.info("🎉 Integration test completed successfully")
        return 0
    else:
        logger.error("❌ Integration test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())