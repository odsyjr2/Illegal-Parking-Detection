#!/usr/bin/env python3
"""
Korean ITS API Integration Test Script

This script tests the Korean ITS API integration with the AI detection system.
It verifies:
1. Korean ITS API connection and stream fetching
2. Real-time event-driven API transfer to backend
3. Multi-streaming windows with detection visualization

Usage:
    python test_korean_its_integration.py [--visual] [--backend-test] [--max-streams N]
"""

import asyncio
import logging
import sys
import argparse
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import cv2
import numpy as np

# Add AI server path
sys.path.append(str(Path(__file__).parent / "ai_server"))

# Import AI components
from core.monitoring import MonitoringService, KoreanITSAPIClient
from utils.config_loader import load_config
from utils.logger import setup_logging
from cctv_manager import get_cctv_manager
from multi_vehicle_tracker import get_vehicle_tracker
from parking_monitor import get_parking_monitor
from event_reporter import EventReporter

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


class KoreanITSTestVisualizer:
    """Visual test interface for Korean ITS API streams"""
    
    def __init__(self, max_streams: int = 4):
        self.max_streams = max_streams
        self.windows = {}
        self.streams_data = {}
        self.detection_overlay = True
        
    def create_stream_window(self, stream_id: str, stream_name: str):
        """Create a new window for stream visualization"""
        window_name = f"Stream: {stream_name} ({stream_id})"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 640, 480)
        self.windows[stream_id] = window_name
        logger.info(f"Created window for stream: {stream_id}")
    
    def update_stream_frame(self, stream_id: str, frame: np.ndarray, detections: List[Dict] = None):
        """Update frame in stream window with detection overlay"""
        if stream_id not in self.windows:
            return
            
        display_frame = frame.copy()
        
        # Add detection overlay if enabled
        if self.detection_overlay and detections:
            for detection in detections:
                # Draw bounding box
                bbox = detection.get('bounding_box', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    
                    # Add label
                    label = f"{detection.get('vehicle_type', 'Vehicle')} ({detection.get('confidence', 0):.2f})"
                    cv2.putText(display_frame, label, (int(x1), int(y1-10)), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Add stream info overlay
        stream_name = self.streams_data.get(stream_id, {}).get('name', stream_id)
        cv2.putText(display_frame, f"Stream: {stream_name}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f"Time: {time.strftime('%H:%M:%S')}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display frame
        cv2.imshow(self.windows[stream_id], display_frame)
    
    def cleanup(self):
        """Close all windows"""
        for window_name in self.windows.values():
            cv2.destroyWindow(window_name)
        cv2.destroyAllWindows()


class KoreanITSTestRunner:
    """Main test runner for Korean ITS API integration"""
    
    def __init__(self, config: Dict[str, Any], enable_visual: bool = False, 
                 enable_backend_test: bool = False, max_streams: int = 4):
        self.config = config
        self.enable_visual = enable_visual
        self.enable_backend_test = enable_backend_test
        self.max_streams = max_streams
        
        # Initialize components
        self.its_client = None
        self.monitoring_service = None
        self.event_reporter = None
        self.visualizer = None
        
        # Test results
        self.test_results = {
            'api_connection': False,
            'streams_fetched': 0,
            'streams_connected': 0,
            'backend_events_sent': 0,
            'detection_events': 0
        }
    
    async def initialize(self):
        """Initialize all test components"""
        try:
            logger.info("🚀 Initializing Korean ITS API Test Runner...")
            
            # Initialize Korean ITS API client
            its_config = self.config.get('cctv_streams', {}).get('live_streams', {}).get('its_api', {})
            if not its_config:
                raise Exception("Korean ITS API configuration not found")
            
            self.its_client = KoreanITSAPIClient(its_config)
            logger.info("✅ Korean ITS API client initialized")
            
            # Initialize monitoring service
            self.monitoring_service = MonitoringService(self.config)
            task_queue = asyncio.Queue()
            
            if not self.monitoring_service.initialize_components(task_queue):
                raise Exception("Failed to initialize monitoring components")
            logger.info("✅ Monitoring service initialized")
            
            # Initialize event reporter for backend testing
            if self.enable_backend_test:
                backend_config = self.config.get('backend', {})
                self.event_reporter = EventReporter(backend_config)
                logger.info("✅ Event reporter initialized for backend testing")
            
            # Initialize visual interface
            if self.enable_visual:
                self.visualizer = KoreanITSTestVisualizer(self.max_streams)
                logger.info("✅ Visual interface initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize test runner: {e}")
            return False
    
    async def test_api_connection(self):
        """Test 1: Korean ITS API Connection and Stream Fetching"""
        logger.info("🔍 Testing Korean ITS API connection...")
        
        try:
            # Fetch streams from Korean ITS API
            streams = self.its_client.fetch_default_streams()
            
            if streams:
                self.test_results['api_connection'] = True
                self.test_results['streams_fetched'] = len(streams)
                
                logger.info(f"✅ API Connection Success! Fetched {len(streams)} streams")
                
                # Log first few streams
                for i, stream in enumerate(streams[:3]):
                    logger.info(f"   Stream {i+1}: {stream['name']} - {stream['stream_url'][:50]}...")
                
                return streams[:self.max_streams]  # Limit for testing
            else:
                logger.error("❌ No streams fetched from Korean ITS API")
                return []
                
        except Exception as e:
            logger.error(f"❌ API Connection Failed: {e}")
            return []
    
    async def test_stream_connections(self, streams: List[Dict[str, Any]]):
        """Test 2: Stream Connection and Frame Reading"""
        logger.info("🎥 Testing stream connections...")
        
        connected_streams = []
        
        for stream_config in streams:
            try:
                stream_id = stream_config['id']
                stream_url = stream_config['stream_url']
                
                logger.info(f"Testing connection to {stream_id}: {stream_url[:50]}...")
                
                # Test OpenCV VideoCapture
                cap = cv2.VideoCapture(stream_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logger.info(f"✅ {stream_id}: Connected, frame shape: {frame.shape}")
                        connected_streams.append((stream_config, cap))
                        self.test_results['streams_connected'] += 1
                        
                        # Create visual window if enabled
                        if self.enable_visual:
                            self.visualizer.create_stream_window(stream_id, stream_config['name'])
                            self.visualizer.streams_data[stream_id] = stream_config
                    else:
                        logger.warning(f"⚠️ {stream_id}: Connected but no frame received")
                        cap.release()
                else:
                    logger.error(f"❌ {stream_id}: Failed to open stream")
                    cap.release()
                    
            except Exception as e:
                logger.error(f"❌ Error testing stream {stream_config['id']}: {e}")
        
        logger.info(f"✅ Connected to {len(connected_streams)} out of {len(streams)} streams")
        return connected_streams
    
    async def test_detection_and_backend_integration(self, connected_streams: List):
        """Test 3: Detection System and Backend Integration"""
        logger.info("🤖 Testing detection system and backend integration...")
        
        # Load AI detection components (mock for testing)
        vehicle_tracker = get_vehicle_tracker()
        parking_monitor = get_parking_monitor()
        
        test_duration = 60  # Test for 60 seconds
        start_time = time.time()
        frame_count = 0
        
        logger.info(f"Running detection test for {test_duration} seconds...")
        
        try:
            while time.time() - start_time < test_duration:
                for stream_config, cap in connected_streams:
                    stream_id = stream_config['id']
                    
                    # Read frame
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    frame_count += 1
                    current_time = time.time()
                    
                    # Mock vehicle detection (for testing purposes)
                    mock_vehicles = self._create_mock_vehicles(frame, current_time)
                    
                    # Mock parking monitoring
                    mock_parking_events = self._create_mock_parking_events(mock_vehicles, current_time)
                    
                    # Check for violations and send to backend
                    for event in mock_parking_events:
                        if event.get('is_violation', False):
                            await self._send_mock_violation_to_backend(event, stream_config, frame)
                    
                    # Update visual display
                    if self.enable_visual:
                        self.visualizer.update_stream_frame(stream_id, frame, mock_vehicles)
                    
                    # Log periodic status
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        logger.info(f"📊 Processed {frame_count} frames, "
                                  f"FPS: {fps:.1f}, "
                                  f"Events sent: {self.test_results['backend_events_sent']}")
                
                # Handle keyboard input for visual mode
                if self.enable_visual:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User requested quit")
                        break
                    elif key == ord('d'):
                        self.visualizer.detection_overlay = not self.visualizer.detection_overlay
                        logger.info(f"Detection overlay: {self.visualizer.detection_overlay}")
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        finally:
            # Cleanup
            for _, cap in connected_streams:
                cap.release()
            
            if self.enable_visual:
                self.visualizer.cleanup()
    
    def _create_mock_vehicles(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Create mock vehicle detections for testing"""
        h, w = frame.shape[:2]
        mock_vehicles = []
        
        # Create 1-3 random mock vehicles
        import random
        num_vehicles = random.randint(1, 3)
        
        for i in range(num_vehicles):
            x1 = random.randint(0, w//2)
            y1 = random.randint(0, h//2)
            x2 = x1 + random.randint(50, 150)
            y2 = y1 + random.randint(30, 100)
            
            vehicle = {
                'track_id': f'vehicle_{i}_{int(timestamp)}',
                'vehicle_type': random.choice(['car', 'truck', 'motorcycle']),
                'confidence': random.uniform(0.7, 0.95),
                'bounding_box': [x1, y1, x2, y2],
                'position': [(x1+x2)/2, (y1+y2)/2],
                'timestamp': timestamp
            }
            mock_vehicles.append(vehicle)
        
        return mock_vehicles
    
    def _create_mock_parking_events(self, vehicles: List[Dict], timestamp: float) -> List[Dict]:
        """Create mock parking events for testing"""
        parking_events = []
        
        for vehicle in vehicles:
            # Randomly simulate parking violation (10% chance)
            import random
            is_violation = random.random() < 0.1
            
            if is_violation:
                event = {
                    'vehicle_id': vehicle['track_id'],
                    'stream_id': 'test_stream',
                    'is_violation': True,
                    'duration': random.randint(300, 900),  # 5-15 minutes
                    'violation_type': 'illegal_parking',
                    'confidence': random.uniform(0.8, 0.95),
                    'location': vehicle['position'],
                    'timestamp': timestamp,
                    'vehicle_info': vehicle
                }
                parking_events.append(event)
                self.test_results['detection_events'] += 1
        
        return parking_events
    
    async def _send_mock_violation_to_backend(self, event: Dict, stream_config: Dict, frame: np.ndarray):
        """Send mock violation event to backend"""
        if not self.enable_backend_test or not self.event_reporter:
            return
        
        try:
            # Create mock violation report
            violation_report = {
                'event_id': f"test_violation_{int(time.time())}_{event['vehicle_id']}",
                'event_type': 'violation_detected',
                'priority': 'high',
                'timestamp': event['timestamp'],
                'timestamp_iso': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(event['timestamp'])),
                'stream_id': stream_config['id'],
                'data': {
                    'violation': {
                        'duration': event['duration'],
                        'violation_severity': event['confidence'],
                        'is_confirmed': True,
                        'vehicle_type': event['vehicle_info']['vehicle_type'],
                        'parking_zone_type': 'no_parking'
                    },
                    'vehicle': event['vehicle_info'],
                    'license_plate': {
                        'plate_text': f"TEST{event['vehicle_id'][-4:]}",
                        'confidence': 0.85,
                        'is_valid_format': True
                    },
                    'stream_info': {
                        'stream_id': stream_config['id'],
                        'location_name': stream_config['name']
                    }
                }
            }
            
            # Send to backend (async)
            success = await self.event_reporter.send_event_async(violation_report)
            if success:
                self.test_results['backend_events_sent'] += 1
                logger.info(f"✅ Sent violation event to backend: {violation_report['event_id']}")
            else:
                logger.warning(f"⚠️ Failed to send violation event to backend")
                
        except Exception as e:
            logger.error(f"❌ Error sending violation to backend: {e}")
    
    def print_test_results(self):
        """Print comprehensive test results"""
        logger.info("=" * 60)
        logger.info("🎯 KOREAN ITS API INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        
        results = self.test_results
        
        logger.info(f"📡 API Connection: {'✅ SUCCESS' if results['api_connection'] else '❌ FAILED'}")
        logger.info(f"📋 Streams Fetched: {results['streams_fetched']}")
        logger.info(f"🎥 Streams Connected: {results['streams_connected']}")
        logger.info(f"🤖 Detection Events: {results['detection_events']}")
        
        if self.enable_backend_test:
            logger.info(f"🔄 Backend Events Sent: {results['backend_events_sent']}")
        
        # Overall success assessment
        overall_success = (
            results['api_connection'] and 
            results['streams_connected'] > 0
        )
        
        status = "✅ OVERALL SUCCESS" if overall_success else "❌ OVERALL FAILED"
        logger.info(f"🏆 Test Status: {status}")
        logger.info("=" * 60)


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Korean ITS API Integration Test')
    parser.add_argument('--visual', action='store_true', 
                       help='Enable visual stream windows')
    parser.add_argument('--backend-test', action='store_true',
                       help='Enable backend API testing')
    parser.add_argument('--max-streams', type=int, default=4,
                       help='Maximum number of streams to test (default: 4)')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Korean ITS API Integration Test")
    logger.info(f"Visual Mode: {'ON' if args.visual else 'OFF'}")
    logger.info(f"Backend Test: {'ON' if args.backend_test else 'OFF'}")
    logger.info(f"Max Streams: {args.max_streams}")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize test runner
        test_runner = KoreanITSTestRunner(
            config=config,
            enable_visual=args.visual,
            enable_backend_test=args.backend_test,
            max_streams=args.max_streams
        )
        
        # Initialize components
        if not await test_runner.initialize():
            logger.error("❌ Failed to initialize test runner")
            return 1
        
        # Run tests
        logger.info("🔍 Step 1: Testing API connection...")
        streams = await test_runner.test_api_connection()
        
        if not streams:
            logger.error("❌ No streams available for testing")
            return 1
        
        logger.info("🎥 Step 2: Testing stream connections...")
        connected_streams = await test_runner.test_stream_connections(streams)
        
        if not connected_streams:
            logger.error("❌ No streams connected successfully")
            return 1
        
        logger.info("🤖 Step 3: Testing detection and backend integration...")
        await test_runner.test_detection_and_backend_integration(connected_streams)
        
        # Print results
        test_runner.print_test_results()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))