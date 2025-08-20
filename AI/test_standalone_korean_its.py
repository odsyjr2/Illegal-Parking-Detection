#!/usr/bin/env python3
"""
Standalone Korean ITS API Integration Test Script

This script tests the Korean ITS API integration WITHOUT requiring backend server.
It directly loads configuration and tests:
1. Korean ITS API connection and stream fetching
2. Live CCTV stream connections and frame reading
3. Multi-streaming windows with mock detection visualization

Usage:
    python test_standalone_korean_its.py [--visual] [--max-streams N]
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

# Try to import YOLO and AI modules
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("YOLO not available - install ultralytics package for real AI detection")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealAIDetector:
    """Real AI detection using YOLO models"""
    
    def __init__(self, models_config: Dict[str, Any]):
        self.models_config = models_config
        self.vehicle_model = None
        self.illegal_parking_model = None
        self.license_plate_model = None
        self.initialized = False
        
        # Model paths from config
        self.vehicle_model_path = models_config.get('vehicle_detection', {}).get('path', '')
        self.illegal_model_path = models_config.get('illegal_parking', {}).get('path', '')
        self.plate_model_path = models_config.get('license_plate', {}).get('detector', {}).get('path', '')
        
        # Detection parameters
        self.vehicle_conf = models_config.get('vehicle_detection', {}).get('confidence_threshold', 0.5)
        self.vehicle_iou = models_config.get('vehicle_detection', {}).get('iou_threshold', 0.45)
        
        # Vehicle class names (common YOLO classes)
        self.vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']
        
    def initialize(self) -> bool:
        """Initialize YOLO models using only custom models from models.yaml"""
        if not YOLO_AVAILABLE:
            logger.warning("🤖 YOLO not available - ultralytics package not installed")
            return False
            
        try:
            logger.info("🚀 Initializing Custom AI Detection Models...")
            
            # Check if custom vehicle model exists
            vehicle_model_full_path = Path(__file__).parent / self.vehicle_model_path
            
            if not vehicle_model_full_path.exists():
                logger.error(f"❌ Custom vehicle model not found: {vehicle_model_full_path}")
                logger.error("💡 Please ensure your custom model is saved at the configured path")
                logger.error("💡 Check config/models.yaml for correct model paths")
                return False
            
            logger.info(f"📦 Loading custom vehicle detection model: {vehicle_model_full_path}")
            
            # Load only the custom model (no fallback to pretrained)
            self.vehicle_model = YOLO(str(vehicle_model_full_path))
            self.vehicle_model.conf = self.vehicle_conf
            self.vehicle_model.iou = self.vehicle_iou
            
            # Get model information
            model_classes = list(self.vehicle_model.names.values())
            logger.info(f"✅ Custom vehicle model loaded successfully")
            logger.info(f"📋 Model classes: {model_classes}")
            logger.info(f"⚙️ Confidence threshold: {self.vehicle_conf}")
            logger.info(f"⚙️ IoU threshold: {self.vehicle_iou}")
            
            # Test model with dummy input to ensure it works
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.vehicle_model(dummy_frame, verbose=False)
            logger.info("🧪 Custom model test successful")
            
            # Load illegal parking model if configured
            if self.illegal_model_path:
                illegal_model_full_path = Path(__file__).parent / self.illegal_model_path
                if illegal_model_full_path.exists():
                    logger.info(f"📦 Loading illegal parking model: {illegal_model_full_path}")
                    self.illegal_parking_model = YOLO(str(illegal_model_full_path))
                    logger.info("✅ Illegal parking model loaded")
                else:
                    logger.warning(f"⚠️ Illegal parking model not found: {illegal_model_full_path}")
            
            # Load license plate model if configured
            if self.plate_model_path:
                plate_model_full_path = Path(__file__).parent / self.plate_model_path
                if plate_model_full_path.exists():
                    logger.info(f"📦 Loading license plate model: {plate_model_full_path}")
                    self.license_plate_model = YOLO(str(plate_model_full_path))
                    logger.info("✅ License plate model loaded")
                else:
                    logger.warning(f"⚠️ License plate model not found: {plate_model_full_path}")
            
            self.initialized = True
            logger.info("🎯 All custom AI models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize custom AI models: {e}")
            logger.error("💡 Check if your model files are valid YOLO format (.pt files)")
            return False
    
    def detect_vehicles(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Detect vehicles in frame using YOLO"""
        if not self.initialized or self.vehicle_model is None:
            return []
            
        try:
            # Run YOLO inference
            results = self.vehicle_model(frame, verbose=False)
            
            detections = []
            
            # Process YOLO results
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes
                    
                    for box in boxes:
                        # Extract bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # Get class name
                        class_name = self.vehicle_model.names.get(class_id, f"class_{class_id}")
                        
                        # Filter for vehicle classes
                        if self._is_vehicle_class(class_name):
                            detection = {
                                'track_id': f'det_{len(detections)}_{int(timestamp)}',
                                'vehicle_type': class_name,
                                'confidence': confidence,
                                'bounding_box': [int(x1), int(y1), int(x2), int(y2)],
                                'center_point': [(x1 + x2) / 2, (y1 + y2) / 2],
                                'area': (x2 - x1) * (y2 - y1),
                                'timestamp': timestamp,
                                'is_real_detection': True
                            }
                            detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in vehicle detection: {e}")
            return []
    
    def _is_vehicle_class(self, class_name: str) -> bool:
        """Check if detected class is a vehicle"""
        # For custom models, you might have different class names
        # This method checks for common vehicle-related keywords
        vehicle_keywords = [
            'car', 'truck', 'bus', 'motorcycle', 'bicycle', 'bike',
            'vehicle', 'auto', 'van', 'suv', 'taxi', 'pickup',
            # Add Korean vehicle class names if your model uses them
            '자동차', '트럭', '버스', '오토바이', '자전거'
        ]
        
        class_lower = class_name.lower()
        return any(keyword in class_lower for keyword in vehicle_keywords)


class MockAIDetector:
    """Mock AI detection for fallback"""
    
    def __init__(self):
        self.initialized = True
        
    def initialize(self) -> bool:
        return True
        
    def detect_vehicles(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Create mock vehicle detections"""
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
                'track_id': f'mock_vehicle_{i}_{int(timestamp)}',
                'vehicle_type': random.choice(['car', 'truck', 'motorcycle']),
                'confidence': random.uniform(0.7, 0.95),
                'bounding_box': [x1, y1, x2, y2],
                'center_point': [(x1+x2)/2, (y1+y2)/2],
                'area': (x2 - x1) * (y2 - y1),
                'timestamp': timestamp,
                'is_real_detection': False
            }
            mock_vehicles.append(vehicle)
        
        return mock_vehicles


class KoreanITSAPIClient:
    """Standalone Korean ITS API client"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 30)
        
    def fetch_cctv_streams_by_bounds(self, min_lon: float, max_lon: float, 
                                   min_lat: float, max_lat: float) -> List[Dict[str, Any]]:
        """Fetch CCTV streams within geographic bounds from Korean ITS API"""
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
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                cctv_data = data.get('response', {}).get('data', [])
                
                # Convert to internal format
                streams = []
                for idx, cctv in enumerate(cctv_data):
                    stream = {
                        'id': f"its_cctv_{idx:03d}",
                        'name': cctv.get('cctvname', f'ITS CCTV {idx}'),
                        'source_type': 'hls' if cctv.get('cctvformat') == 'HLS' else 'http',
                        'stream_url': cctv.get('cctvurl', ''),
                        'fps': 15,  # Default FPS for live streams
                        'enabled': True,
                        'location': {
                            'latitude': cctv.get('coordy', 0),
                            'longitude': cctv.get('coordx', 0),
                            'address': cctv.get('cctvname', ''),
                            'zone_type': 'road'
                        }
                    }
                    streams.append(stream)
                
                logger.info(f"Fetched {len(streams)} CCTV streams from Korean ITS API")
                return streams
            else:
                logger.warning(f"Korean ITS API returned status {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch CCTV streams from Korean ITS API: {e}")
            return []
    
    def fetch_default_streams(self) -> List[Dict[str, Any]]:
        """Fetch CCTV streams using default geographic bounds"""
        bounds = self.config.get('default_bounds', {})
        return self.fetch_cctv_streams_by_bounds(
            min_lon=bounds.get('min_longitude', 126.7),
            max_lon=bounds.get('max_longitude', 127.2),
            min_lat=bounds.get('min_latitude', 37.4),
            max_lat=bounds.get('max_latitude', 37.7)
        )


class StandaloneTestVisualizer:
    """Visual test interface for Korean ITS API streams"""
    
    def __init__(self, max_streams: int = 4):
        self.max_streams = max_streams
        self.windows = {}
        self.streams_data = {}
        self.detection_overlay = True
        
    def create_stream_window(self, stream_id: str, stream_name: str):
        """Create a new window for stream visualization"""
        window_name = f"Stream: {stream_name[:30]} ({stream_id})"
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
        cv2.putText(display_frame, f"Stream: {stream_name[:40]}", (10, 30), 
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


class StandaloneTestRunner:
    """Standalone test runner for Korean ITS API integration"""
    
    def __init__(self, enable_visual: bool = False, max_streams: int = 4, force_mock: bool = False):
        self.enable_visual = enable_visual
        self.max_streams = max_streams
        self.force_mock = force_mock
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.its_client = None
        self.visualizer = None
        self.ai_detector = None
        
        # Test results
        self.test_results = {
            'api_connection': False,
            'streams_fetched': 0,
            'streams_connected': 0,
            'frames_processed': 0,
            'detection_events': 0,
            'ai_type': 'unknown'  # 'real' or 'mock'
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from both streams.yaml and models.yaml"""
        config_dir = Path(__file__).parent / "config"
        
        # Load streams configuration
        streams_config_path = config_dir / "streams.yaml"
        if streams_config_path.exists():
            with open(streams_config_path, 'r', encoding='utf-8') as f:
                streams_config = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"Streams configuration file not found: {streams_config_path}")
        
        # Load models configuration
        models_config_path = config_dir / "models.yaml"
        if models_config_path.exists():
            with open(models_config_path, 'r', encoding='utf-8') as f:
                models_config = yaml.safe_load(f)
        else:
            logger.warning(f"Models configuration file not found: {models_config_path}")
            models_config = {}
        
        # Combine configurations
        config = streams_config
        config['models'] = models_config
        
        return config
    
    def initialize(self):
        """Initialize all test components"""
        try:
            logger.info("🚀 Initializing Standalone Korean ITS API Test Runner...")
            
            # Initialize Korean ITS API client
            its_config = self.config.get('cctv_streams', {}).get('live_streams', {}).get('its_api', {})
            if not its_config:
                raise Exception("Korean ITS API configuration not found in streams.yaml")
            
            self.its_client = KoreanITSAPIClient(its_config)
            logger.info("✅ Korean ITS API client initialized")
            
            # Initialize AI detector
            models_config = self.config.get('models', {})
            force_mock = getattr(self, 'force_mock', False)
            
            if not force_mock and models_config and YOLO_AVAILABLE:
                self.ai_detector = RealAIDetector(models_config)
                if self.ai_detector.initialize():
                    logger.info("✅ Custom AI models successfully initialized")
                    self.test_results['ai_type'] = 'real'
                else:
                    logger.warning("⚠️ Custom AI models failed to load, using mock detector")
                    logger.warning("💡 Make sure your .pt model files exist at the configured paths")
                    self.ai_detector = MockAIDetector()
                    self.test_results['ai_type'] = 'mock'
            else:
                if force_mock:
                    logger.info("🔄 Using mock AI detection (forced)")
                elif not models_config:
                    logger.info("🔄 Using mock AI detection (no models.yaml config found)")
                elif not YOLO_AVAILABLE:
                    logger.info("🔄 Using mock AI detection (ultralytics not installed)")
                self.ai_detector = MockAIDetector()
                self.test_results['ai_type'] = 'mock'
            
            # Initialize visual interface
            if self.enable_visual:
                self.visualizer = StandaloneTestVisualizer(self.max_streams)
                logger.info("✅ Visual interface initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize test runner: {e}")
            return False
    
    def test_api_connection(self):
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
    
    def test_stream_connections(self, streams: List[Dict[str, Any]]):
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
    
    def test_streaming_and_detection(self, connected_streams: List):
        """Test 3: Live Streaming with Mock Detection"""
        logger.info("🤖 Testing live streaming with mock detection...")
        
        test_duration = 60  # Test for 60 seconds
        start_time = time.time()
        frame_count = 0
        
        logger.info(f"Running streaming test for {test_duration} seconds...")
        logger.info("Press 'q' to quit, 'd' to toggle detection overlay (if visual mode)")
        
        try:
            while time.time() - start_time < test_duration:
                for stream_config, cap in connected_streams:
                    stream_id = stream_config['id']
                    
                    # Read frame
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    frame_count += 1
                    self.test_results['frames_processed'] += 1
                    current_time = time.time()
                    
                    # Real AI vehicle detection
                    detected_vehicles = self.ai_detector.detect_vehicles(frame, current_time)
                    
                    # Log detection results
                    if len(detected_vehicles) > 0:
                        # Periodic logging of detections
                        if frame_count % 50 == 0:  # Every 50 frames
                            detection_info = []
                            for vehicle in detected_vehicles:
                                detection_type = "🤖 REAL" if vehicle.get('is_real_detection', False) else "🎭 MOCK"
                                detection_info.append(f"{detection_type} {vehicle['vehicle_type']} (conf: {vehicle['confidence']:.2f})")
                            
                            logger.info(f"🚗 Detected in {stream_id}: {', '.join(detection_info)}")
                        
                        # Count significant detections as events
                        high_conf_detections = [v for v in detected_vehicles if v['confidence'] > 0.8]
                        if high_conf_detections and frame_count % 100 == 0:  # Every 100 frames with high confidence
                            self.test_results['detection_events'] += 1
                            logger.info(f"🚨 High confidence detections in {stream_id}: {len(high_conf_detections)} vehicles")
                    
                    # Update visual display
                    if self.enable_visual:
                        self.visualizer.update_stream_frame(stream_id, frame, detected_vehicles)
                    
                    # Log periodic status
                    if frame_count % 300 == 0:  # Every 300 frames
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        logger.info(f"📊 Processed {frame_count} frames, "
                                  f"FPS: {fps:.1f}, "
                                  f"Events: {self.test_results['detection_events']}")
                
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
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        finally:
            # Cleanup
            for _, cap in connected_streams:
                cap.release()
            
            if self.enable_visual:
                self.visualizer.cleanup()
    
    def print_test_results(self):
        """Print comprehensive test results"""
        logger.info("=" * 60)
        logger.info("🎯 STANDALONE KOREAN ITS API TEST RESULTS")
        logger.info("=" * 60)
        
        results = self.test_results
        
        logger.info(f"📡 API Connection: {'✅ SUCCESS' if results['api_connection'] else '❌ FAILED'}")
        logger.info(f"📋 Streams Fetched: {results['streams_fetched']}")
        logger.info(f"🎥 Streams Connected: {results['streams_connected']}")
        logger.info(f"📊 Frames Processed: {results['frames_processed']}")
        logger.info(f"🤖 Detection Events: {results['detection_events']}")
        
        # AI detection type
        ai_type = results.get('ai_type', 'unknown')
        ai_status = "🤖 REAL YOLO" if ai_type == 'real' else "🎭 MOCK"
        logger.info(f"🧠 AI Detection Type: {ai_status}")
        
        # Overall success assessment
        overall_success = (
            results['api_connection'] and 
            results['streams_connected'] > 0 and
            results['frames_processed'] > 0
        )
        
        status = "✅ OVERALL SUCCESS" if overall_success else "❌ OVERALL FAILED"
        logger.info(f"🏆 Test Status: {status}")
        logger.info("=" * 60)


def show_model_configuration():
    """Show detailed model configuration information"""
    logger.info("=" * 60)
    logger.info("🤖 CUSTOM AI MODELS CONFIGURATION")
    logger.info("=" * 60)
    
    try:
        # Load models configuration
        config_dir = Path(__file__).parent / "config"
        models_config_path = config_dir / "models.yaml"
        
        if not models_config_path.exists():
            logger.error(f"❌ models.yaml not found at: {models_config_path}")
            return
        
        with open(models_config_path, 'r', encoding='utf-8') as f:
            models_config = yaml.safe_load(f)
        
        # Check vehicle detection model
        vehicle_config = models_config.get('vehicle_detection', {})
        vehicle_path = vehicle_config.get('path', '')
        vehicle_model_full_path = Path(__file__).parent / vehicle_path
        
        logger.info("🚗 VEHICLE DETECTION MODEL:")
        logger.info(f"   📁 Path: {vehicle_path}")
        logger.info(f"   📍 Full Path: {vehicle_model_full_path}")
        logger.info(f"   📋 Exists: {'✅ YES' if vehicle_model_full_path.exists() else '❌ NO'}")
        logger.info(f"   🎯 Confidence: {vehicle_config.get('confidence_threshold', 0.5)}")
        logger.info(f"   🔗 IoU: {vehicle_config.get('iou_threshold', 0.45)}")
        logger.info(f"   💾 Device: {vehicle_config.get('device', 'auto')}")
        
        # Check illegal parking model
        illegal_config = models_config.get('illegal_parking', {})
        illegal_path = illegal_config.get('path', '')
        if illegal_path:
            illegal_model_full_path = Path(__file__).parent / illegal_path
            logger.info("\n🚫 ILLEGAL PARKING MODEL:")
            logger.info(f"   📁 Path: {illegal_path}")
            logger.info(f"   📍 Full Path: {illegal_model_full_path}")
            logger.info(f"   📋 Exists: {'✅ YES' if illegal_model_full_path.exists() else '❌ NO'}")
            logger.info(f"   🎯 Confidence: {illegal_config.get('confidence_threshold', 0.6)}")
        
        # Check license plate model
        plate_config = models_config.get('license_plate', {}).get('detector', {})
        plate_path = plate_config.get('path', '')
        if plate_path:
            plate_model_full_path = Path(__file__).parent / plate_path
            logger.info("\n🔢 LICENSE PLATE MODEL:")
            logger.info(f"   📁 Path: {plate_path}")
            logger.info(f"   📍 Full Path: {plate_model_full_path}")
            logger.info(f"   📋 Exists: {'✅ YES' if plate_model_full_path.exists() else '❌ NO'}")
            logger.info(f"   🎯 Confidence: {plate_config.get('confidence_threshold', 0.7)}")
        
        # Check model loading configuration
        loading_config = models_config.get('model_loading', {})
        logger.info("\n⚙️ MODEL LOADING SETTINGS:")
        logger.info(f"   💾 Cache Models: {loading_config.get('cache_models', True)}")
        logger.info(f"   🚀 Lazy Loading: {loading_config.get('lazy_loading', False)}")
        logger.info(f"   🧠 Memory Optimization: {loading_config.get('memory_optimization', True)}")
        logger.info(f"   🔄 Retry Attempts: {loading_config.get('retry_attempts', 3)}")
        logger.info(f"   🖥️ Fallback to CPU: {loading_config.get('fallback_to_cpu', True)}")
        
        # Check YOLO availability
        logger.info("\n🔧 SYSTEM REQUIREMENTS:")
        logger.info(f"   📦 Ultralytics YOLO: {'✅ AVAILABLE' if YOLO_AVAILABLE else '❌ NOT INSTALLED'}")
        
        if not YOLO_AVAILABLE:
            logger.info("   💡 Install with: pip install ultralytics")
        
        logger.info("\n" + "=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error reading model configuration: {e}")


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Standalone Korean ITS API Integration Test')
    parser.add_argument('--visual', action='store_true', 
                       help='Enable visual stream windows')
    parser.add_argument('--max-streams', type=int, default=4,
                       help='Maximum number of streams to test (default: 4)')
    parser.add_argument('--force-mock', action='store_true',
                       help='Force use of mock AI detection instead of real YOLO models')
    parser.add_argument('--show-model-info', action='store_true',
                       help='Show detailed model configuration information and exit')
    
    args = parser.parse_args()
    
    # Show model info if requested
    if args.show_model_info:
        show_model_configuration()
        return 0
    
    logger.info("🚀 Starting Standalone Korean ITS API Integration Test with REAL AI Detection")
    logger.info(f"Visual Mode: {'ON' if args.visual else 'OFF'}")
    logger.info(f"Max Streams: {args.max_streams}")
    logger.info(f"AI Detection: {'FORCED MOCK' if args.force_mock else 'REAL YOLO (with fallback to mock)'}")
    logger.info("💡 No backend server required for this test")
    
    try:
        # Initialize test runner
        test_runner = StandaloneTestRunner(
            enable_visual=args.visual,
            max_streams=args.max_streams,
            force_mock=args.force_mock
        )
        
        # Initialize components
        if not test_runner.initialize():
            logger.error("❌ Failed to initialize test runner")
            return 1
        
        # Run tests
        logger.info("🔍 Step 1: Testing API connection...")
        streams = test_runner.test_api_connection()
        
        if not streams:
            logger.error("❌ No streams available for testing")
            return 1
        
        logger.info("🎥 Step 2: Testing stream connections...")
        connected_streams = test_runner.test_stream_connections(streams)
        
        if not connected_streams:
            logger.error("❌ No streams connected successfully")
            return 1
        
        logger.info("🎬 Step 3: Testing live streaming and detection...")
        test_runner.test_streaming_and_detection(connected_streams)
        
        # Print results
        test_runner.print_test_results()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())