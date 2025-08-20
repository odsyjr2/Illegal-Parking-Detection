#!/usr/bin/env python3
"""
Illegal Parking Detection AI Processor - Main Application
13-Step Sequential Processing System

This module implements the complete AI processing pipeline:
1-2.  YAML Configuration Loading
3-4.  CCTV Stream Search & Parsing  
5.    Geocoding Enhancement
6.    Backend CCTV Synchronization
7.    AI Model Loading
8-9.  Multi-stream Vehicle Tracking
10.   Illegal Parking Detection
11.   Bbox-based Image Cropping
12.   OCR Processing
13.   Backend Violation Transmission

Author: AI Processor Development Team
Date: 2024-12-19
"""

import asyncio
import signal
import sys
import time
import threading
import cv2
import json
import base64
import numpy as np
import requests
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import psutil

# Add ai_server to path for imports
sys.path.append(str(Path(__file__).parent))

# Import configuration and utilities
from utils.config_loader import load_config
from utils.logger import setup_logging, get_logger

# Import AI models directly
from ultralytics import YOLO
from easyocr import Reader

# Import existing modules
from event_reporter import initialize_event_reporter, get_event_reporter
from geocoding_service import VWorldGeocodingService, reverse_geocode_coordinates, initialize_geocoding_service

# Configure logging to reduce noise from ultralytics
import logging
logging.getLogger('ultralytics').setLevel(logging.WARNING)

# Configure logging
logger = get_logger("main")

# Data structures
class VehicleDetection:
    """Single vehicle detection result"""
    def __init__(self, bbox, confidence, vehicle_type="car"):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.vehicle_type = vehicle_type
        self.track_id = None
        self.is_illegal = False
        self.illegal_confidence = 0.0
        self.illegal_bbox = None  # bbox from illegal parking detection
        self.license_plate = None
        self.license_text = ""
        self.license_confidence = 0.0
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.stationary_start = None
        
    def update_position(self, bbox, confidence):
        """Update vehicle position and timing"""
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = time.time()
        
        # Check if vehicle is stationary (simple distance check)
        # In real implementation, this would be more sophisticated
        if self.stationary_start is None:
            self.stationary_start = time.time()
    
    def get_parking_duration(self):
        """Get current parking duration in seconds"""
        if self.stationary_start:
            return time.time() - self.stationary_start
        return 0.0

class IllegalParkingResult:
    """Result from illegal parking detection"""
    def __init__(self):
        self.is_illegal = False
        self.confidence = 0.0
        self.bbox = None  # bbox within vehicle crop

class OCRResult:
    """OCR recognition result"""
    def __init__(self, recognized_text="", confidence=0.0, is_valid_format=False):
        self.recognized_text = recognized_text
        self.confidence = confidence
        self.is_valid_format = is_valid_format

class IllegalParkingProcessor:
    """Main AI processor coordinating the 13-step processing system"""
    
    def __init__(self):
        # Configuration storage
        self.config: Optional[Dict[str, Any]] = None
        self.models_config: Optional[Dict[str, Any]] = None
        self.streams_config: Optional[Dict[str, Any]] = None
        self.processing_config: Optional[Dict[str, Any]] = None
        
        # AI models
        self.models: Dict[str, Any] = {}
        
        # CCTV and stream data
        self.cctv_list: List[Dict[str, Any]] = []
        self.active_streams: Dict[str, Any] = {}
        
        # Processing state
        self.is_running = False
        self.start_time: Optional[float] = None
        
        # Services
        self.geocoding_service: Optional[VWorldGeocodingService] = None
        
        # Statistics
        self.stats = {
            'total_frames_processed': 0,
            'total_vehicles_tracked': 0,
            'total_violations_detected': 0,
            'total_violations_sent': 0
        }
        
        logger.info("IllegalParkingProcessor initialized")
        print("🚀 Illegal Parking Detection AI Processor")
        print("=" * 60)

    # =================================================================
    # STEP 1-2: Configuration Loading System
    # =================================================================
    
    def load_configurations(self) -> bool:
        """Load all 4 YAML configuration files into dictionaries"""
        try:
            print("📁 Step 1-2: Loading YAML Configurations...")
            
            # Load main configuration (loads all 4 YAML files)
            self.config = load_config()
            
            if not self.config:
                print("❌ Failed to load configurations")
                return False
            
            # Extract individual config sections
            self.models_config = self.config  # models.yaml keys are at root level
            self.streams_config = self.config  # streams.yaml keys are at root level 
            self.processing_config = self.config  # processing.yaml keys are at root level
            
            # Setup logging from config
            setup_logging(self.config.get('logging', {}))
            
            # Print loaded configurations
            print("✅ Config loading completed successfully!")
            print(f"   📋 Main config keys: {list(self.config.keys())}")
            print(f"   🤖 Models config: {list(self.models_config.keys())}")
            print(f"   📺 Streams config: {list(self.streams_config.keys())}")
            print(f"   ⚙️  Processing config: {list(self.processing_config.keys())}")
            
            # Initialize geocoding service (both instance and global)
            vworld_config = self.config.get('vworld', {})
            self.geocoding_service = VWorldGeocodingService(vworld_config)
            
            # Initialize global geocoding service for event_reporter
            initialize_success = initialize_geocoding_service(vworld_config)
            if initialize_success:
                print("✅ VWorld geocoding service initialized globally")
            else:
                print("⚠️ VWorld geocoding service global initialization failed")
            
            logger.info("All configurations loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Configuration loading failed: {e}")
            logger.error(f"Configuration loading error: {e}")
            return False

    # =================================================================
    # STEP 3-4: CCTV Stream Search & Parsing System  
    # =================================================================
    
    def fetch_cctv_streams(self) -> List[Dict[str, Any]]:
        """Fetch CCTV streams from Korean ITS API and parse response"""
        try:
            print("\n🔍 Step 3-4: CCTV Stream Search & Parsing...")
            
            # Get ITS API configuration - streams.yaml keys are merged at root level
            cctv_streams_config = self.streams_config.get('cctv_streams', {})
            live_streams_config = cctv_streams_config.get('live_streams', {})
            its_api_config = live_streams_config.get('its_api', {})
            
            if not its_api_config:
                print("❌ No ITS API configuration found")
                return []
            
            # Build API request URL
            base_url = its_api_config.get('base_url')
            api_key = its_api_config.get('api_key')
            cctv_type = its_api_config.get('cctv_type', 4)
            get_type = its_api_config.get('get_type', 'json')
            
            # Get geographic bounds from config
            bounds = its_api_config.get('default_bounds', {})
            min_x = bounds.get('min_longitude', 126.7)
            max_x = bounds.get('max_longitude', 127.2)
            min_y = bounds.get('min_latitude', 37.4)
            max_y = bounds.get('max_latitude', 37.7)
            
            api_url = f"{base_url}?apiKey={api_key}&type=its&cctvType={cctv_type}&getType={get_type}&minX={min_x}&maxX={max_x}&minY={min_y}&maxY={max_y}"
            
            print(f"📡 CCTV API Request: {base_url}")
            print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")
            print(f"   CCTV Type: {cctv_type} (HTTP/HLS streams)")
            
            # Make API request
            timeout = its_api_config.get('timeout', 30)
            response = requests.get(api_url, timeout=timeout)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Extract CCTV list from response
            cctv_list = self._parse_its_api_response(data, its_api_config)
            
            print(f"✅ CCTV Stream Search: {len(cctv_list)} streams discovered")
            
            # Print sample CCTV info
            if cctv_list:
                sample = cctv_list[0]
                print(f"   📺 Sample CCTV: {sample.get('name', 'Unknown')} at ({sample.get('latitude', 0):.4f}, {sample.get('longitude', 0):.4f})")
            
            self.cctv_list = cctv_list
            logger.info(f"Fetched {len(cctv_list)} CCTV streams from ITS API")
            return cctv_list
            
        except requests.RequestException as e:
            print(f"❌ CCTV API Request failed: {e}")
            logger.error(f"CCTV API error: {e}")
            return []
        except Exception as e:
            print(f"❌ CCTV Stream parsing failed: {e}")
            logger.error(f"CCTV parsing error: {e}")
            return []

    def _parse_its_api_response(self, data: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Korean ITS API response into CCTV stream list"""
        try:
            cctv_list = []
            
            # Korean ITS API returns data in nested structure: {"response": {"data": [...]}}
            response_data = data.get('response', {})
            if isinstance(response_data, dict):
                api_data = response_data.get('data', [])
            else:
                # Fallback for different API response formats
                api_data = data.get('data', data)
            
            if isinstance(api_data, list):
                items = api_data
            elif isinstance(api_data, dict) and 'items' in api_data:
                items = api_data['items']
            else:
                print("⚠️ Unknown API response format")
                logger.warning(f"API response structure: {list(data.keys())}")
                items = []
            
            # Get filtering configuration
            filters = config.get('filters', {})
            max_streams = filters.get('max_streams', 10)
            exclude_keywords = filters.get('exclude_keywords', [])
            
            processed_count = 0
            
            for item in items:
                if processed_count >= max_streams:
                    break
                    
                try:
                    # Extract basic info
                    cctv_name = item.get('cctvname', item.get('name', f'CCTV_{processed_count+1}'))
                    
                    # Skip if contains excluded keywords
                    if any(keyword in cctv_name for keyword in exclude_keywords):
                        continue
                    
                    # Extract coordinates
                    latitude = float(item.get('coordy', item.get('latitude', 0.0)))
                    longitude = float(item.get('coordx', item.get('longitude', 0.0)))
                    
                    # Skip invalid coordinates
                    if latitude == 0.0 or longitude == 0.0:
                        continue
                    
                    # Extract stream URL
                    stream_url = item.get('cctvurl', item.get('streamUrl', ''))
                    if not stream_url:
                        continue
                    
                    # Create CCTV info
                    cctv_info = {
                        'streamId': f'cctv_{processed_count+1:03d}',
                        'streamName': cctv_name,
                        'streamUrl': stream_url,
                        'latitude': latitude,
                        'longitude': longitude,
                        'location': '',  # Will be filled by geocoding
                        'streamSource': 'korean_its_api',
                        'active': True,
                        'cctvType': config.get('cctv_type', 4)
                    }
                    
                    cctv_list.append(cctv_info)
                    processed_count += 1
                    
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipped invalid CCTV item: {e}")
                    continue
            
            return cctv_list
            
        except Exception as e:
            logger.error(f"Error parsing ITS API response: {e}")
            return []

    # =================================================================
    # STEP 5: Geocoding Enhancement System
    # =================================================================
    
    def enhance_cctv_with_geocoding(self, cctv_list: List[Dict[str, Any]]) -> None:
        """Enhance CCTV information with reverse geocoding (GPS → Korean address)"""
        try:
            print(f"\n🗺️ Step 5: Geocoding Enhancement...")
            
            if not self.geocoding_service or not self.geocoding_service.is_available():
                print("⚠️ VWorld geocoding service not available, using coordinate fallback")
                
                # Fill with coordinate-based location
                for cctv in cctv_list:
                    lat, lon = cctv['latitude'], cctv['longitude']
                    cctv['location'] = f"좌표: {lat:.6f}, {lon:.6f}"
                return
            
            geocoded_count = 0
            failed_count = 0
            
            for i, cctv in enumerate(cctv_list):
                try:
                    lat, lon = cctv['latitude'], cctv['longitude']
                    
                    # Perform reverse geocoding using instance method
                    geocoding_result = self.geocoding_service.reverse_geocode(lat, lon)
                    
                    if geocoding_result.is_geocoded:
                        cctv['location'] = geocoding_result.formatted_address
                        geocoded_count += 1
                        print(f"🗺️ Geocoding [{i+1:2d}/{len(cctv_list)}]: {cctv['streamName'][:30]:<30} → {geocoding_result.formatted_address[:50]}")
                    else:
                        # Fallback to coordinates
                        cctv['location'] = f"좌표: {lat:.6f}, {lon:.6f}"
                        failed_count += 1
                        
                    # Rate limiting - VWorld API has limits
                    if i < len(cctv_list) - 1:
                        time.sleep(0.1)  # 100ms delay between requests
                        
                except Exception as e:
                    logger.warning(f"Geocoding failed for CCTV {cctv['streamName']}: {e}")
                    cctv['location'] = f"좌표: {cctv['latitude']:.6f}, {cctv['longitude']:.6f}"
                    failed_count += 1
            
            print(f"✅ Geocoding completed: {geocoded_count} success, {failed_count} fallback")
            logger.info(f"Geocoding results: {geocoded_count} geocoded, {failed_count} fallback")
            
        except Exception as e:
            print(f"❌ Geocoding enhancement failed: {e}")
            logger.error(f"Geocoding error: {e}")

    # =================================================================
    # STEP 6: Backend CCTV Synchronization
    # =================================================================
    
    async def sync_cctv_to_backend(self, cctv_list: List[Dict[str, Any]]) -> bool:
        """Synchronize CCTV stream information to backend database"""
        try:
            print(f"\n📡 Step 6: Backend CCTV Synchronization...")
            
            if not cctv_list:
                print("⚠️ No CCTV streams to synchronize")
                return False
            
            # Get event reporter
            reporter = get_event_reporter()
            if not reporter:
                print("❌ Event reporter not initialized")
                return False
            
            # Format CCTV data for backend
            formatted_streams = []
            for cctv in cctv_list:
                formatted_stream = {
                    "streamId": cctv["streamId"],
                    "streamName": cctv["streamName"], 
                    "streamUrl": cctv["streamUrl"],
                    "location": cctv["location"],
                    "latitude": cctv["latitude"],
                    "longitude": cctv["longitude"],
                    "streamSource": cctv.get("streamSource", "korean_its_api"),
                    "active": cctv.get("active", True),
                    "discoveredAt": datetime.now().isoformat()
                }
                formatted_streams.append(formatted_stream)
            
            # Send to backend
            print("📡 Backend CCTV Synchronization API Request:")
            print(f"   Endpoint: POST /api/cctvs/sync")
            print(f"   Payload: {len(formatted_streams)} CCTV streams")
            
            # Print sample payload
            if formatted_streams:
                sample = formatted_streams[0]
                print(f"   Sample: {sample['streamName']} at {sample['location'][:50]}")
            
            success = await reporter.sync_cctv_streams(formatted_streams)
            
            if success:
                print(f"   Status: ✅ SUCCESS - {len(formatted_streams)} streams synchronized")
                logger.info(f"CCTV synchronization successful: {len(formatted_streams)} streams")
            else:
                print(f"   Status: ❌ FAILED - Backend synchronization error")
                logger.error("CCTV synchronization failed")
            
            return success
            
        except Exception as e:
            print(f"❌ Backend synchronization failed: {e}")
            logger.error(f"Backend sync error: {e}")
            return False

    # =================================================================
    # STEP 7: AI Model Loading System
    # =================================================================
    
    def load_ai_models(self) -> bool:
        """Load all 4 AI models sequentially with configuration"""
        try:
            print(f"\n🤖 Step 7: AI Model Loading...")
            
            models = {}
            
            # 1. Vehicle Detection Model
            print("🚗 Loading Vehicle Detection Model...")
            vehicle_config = self.models_config.get('vehicle_detection', {})
            vehicle_path = vehicle_config.get('path', '')
            device = vehicle_config.get('device', 'auto')
            
            if Path(vehicle_path).exists():
                models['vehicle'] = YOLO(vehicle_path)
                if device != 'auto':
                    models['vehicle'].to(device)
                print(f"✅ Vehicle Detection loaded: {vehicle_path}")
                print(f"   Device: {device}, Confidence: {vehicle_config.get('confidence_threshold', 0.5)}")
            else:
                print(f"❌ Vehicle Detection model not found: {vehicle_path}")
                return False
            
            # 2. Illegal Parking Classification Model
            print("🚫 Loading Illegal Parking Model...")
            illegal_config = self.models_config.get('illegal_parking', {})
            illegal_path = illegal_config.get('path', '')
            
            if Path(illegal_path).exists():
                models['illegal'] = YOLO(illegal_path)
                if device != 'auto':
                    models['illegal'].to(device)
                print(f"✅ Illegal Parking loaded: {illegal_path}")
                print(f"   Device: {device}, Confidence: {illegal_config.get('confidence_threshold', 0.6)}")
            else:
                print(f"❌ Illegal Parking model not found: {illegal_path}")
                return False
            
            # 3. License Plate Detection Model
            print("🔍 Loading License Plate Detection Model...")
            plate_config = self.models_config.get('license_plate', {}).get('detector', {})
            plate_path = plate_config.get('path', '')
            
            if Path(plate_path).exists():
                models['plate_detection'] = YOLO(plate_path)
                if device != 'auto':
                    models['plate_detection'].to(device)
                print(f"✅ License Plate Detection loaded: {plate_path}")
                print(f"   Device: {device}, Confidence: {plate_config.get('confidence_threshold', 0.7)}")
            else:
                print(f"❌ License Plate Detection model not found: {plate_path}")
                return False
            
            # 4. License Plate OCR Model
            print("📝 Loading License Plate OCR Model...")
            ocr_config = self.models_config.get('license_plate', {}).get('ocr', {})
            languages = ocr_config.get('languages', ['ko', 'en'])
            gpu_enabled = ocr_config.get('gpu_enabled', True) and device != 'cpu'
            
            try:
                models['ocr'] = Reader(languages, gpu=gpu_enabled)
                print(f"✅ License Plate OCR loaded: {languages}")
                print(f"   GPU Enabled: {gpu_enabled}, Confidence: {ocr_config.get('confidence_threshold', 0.8)}")
            except Exception as e:
                print(f"⚠️ OCR loading with GPU failed, trying CPU: {e}")
                try:
                    models['ocr'] = Reader(languages, gpu=False)
                    print(f"✅ License Plate OCR loaded (CPU): {languages}")
                except Exception as e2:
                    print(f"❌ OCR loading failed completely: {e2}")
                    return False
            
            # Model warmup
            print("🔥 Performing model warmup...")
            warmup_runs = self.models_config.get('model_loading', {}).get('warmup_runs', 3)
            self._warmup_models(models, warmup_runs)
            
            # GPU memory status
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory_used = torch.cuda.memory_allocated() / 1024 / 1024
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
                    print(f"🔧 GPU Memory Usage: {gpu_memory_used:.1f}MB / {gpu_memory_total:.1f}MB")
            except:
                pass
            
            self.models = models
            print(f"✅ All AI models loaded successfully!")
            logger.info("All AI models loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ AI model loading failed: {e}")
            logger.error(f"AI model loading error: {e}")
            return False

    def _warmup_models(self, models: Dict[str, Any], warmup_runs: int) -> None:
        """Warm up AI models with dummy inference"""
        try:
            # Create dummy image
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            
            for i in range(warmup_runs):
                # Warmup YOLO models
                for model_name in ['vehicle', 'illegal', 'plate_detection']:
                    if model_name in models:
                        models[model_name].predict(dummy_image, verbose=False)
                
                # Warmup OCR
                if 'ocr' in models:
                    models['ocr'].recognize(dummy_image, detail=0)
            
            print(f"🔥 Model warmup completed: {warmup_runs} runs")
            
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")

    # =================================================================
    # STEP 8-9: Multi-stream Processing Engine
    # =================================================================
    
    async def start_multi_stream_processing(self, cctv_list: List[Dict[str, Any]]) -> None:
        """Start multi-stream processing with vehicle tracking"""
        try:
            print(f"\n🎬 Step 8-9: Multi-stream Processing Engine...")
            
            if not cctv_list:
                print("❌ No CCTV streams available for processing")
                return
            
            if not self.models:
                print("❌ AI models not loaded")
                return
            
            # Limit concurrent streams based on configuration
            max_streams = self.processing_config.get('monitoring', {}).get('max_concurrent_streams', 4)
            active_cctv_list = cctv_list[:max_streams]  # Limit concurrent streams
            
            print(f"🎬 Multi-stream processing starting: {len(active_cctv_list)} parallel streams")
            print(f"   Max concurrent streams: {max_streams}")
            print(f"   Processing interval: {self.processing_config.get('monitoring', {}).get('processing_interval', 0.5)}s")
            
            # Create tasks for each stream
            tasks = []
            for cctv in active_cctv_list:
                task = asyncio.create_task(
                    self.process_single_stream(cctv),
                    name=f"Stream_{cctv['streamId']}"
                )
                tasks.append(task)
                print(f"   📺 {cctv['streamId']}: {cctv['streamName'][:40]}")
            
            self.is_running = True
            self.start_time = time.time()
            
            print("✅ All stream processors started successfully!")
            print("🔄 Real-time processing active... (Press Ctrl+C to stop)")
            
            # Run all streams concurrently
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                print("🛑 Stream processing cancelled")
            
        except Exception as e:
            print(f"❌ Multi-stream processing failed: {e}")
            logger.error(f"Multi-stream processing error: {e}")

    async def process_single_stream(self, cctv: Dict[str, Any]) -> None:
        """Process single CCTV stream with vehicle tracking and violation detection"""
        stream_id = cctv['streamId']
        stream_name = cctv['streamName']
        
        # Initialize stream-specific tracking
        tracked_vehicles = {}
        next_track_id = 1
        frame_count = 0
        
        # Get processing configuration
        processing_interval = self.processing_config.get('monitoring', {}).get('processing_interval', 0.5)
        frame_skip_rate = self.processing_config.get('monitoring', {}).get('frame_skip_rate', 2)
        
        logger.info(f"Stream processor started: {stream_id}")
        
        try:
            while self.is_running:
                try:
                    frame_count += 1
                    
                    # For demonstration, create a synthetic frame
                    # In real implementation, this would capture from stream_url
                    frame = self._get_synthetic_frame(cctv, frame_count)
                    
                    # Skip frames based on configuration
                    if frame_count % (frame_skip_rate + 1) != 0:
                        await asyncio.sleep(processing_interval / 10)  # Small delay
                        continue
                    
                    # Step 8: Vehicle tracking
                    current_vehicles = self._track_vehicles_in_frame(frame, stream_id, tracked_vehicles, next_track_id)
                    
                    # Update tracked vehicles
                    for vehicle in current_vehicles:
                        if vehicle.track_id not in tracked_vehicles:
                            tracked_vehicles[vehicle.track_id] = vehicle
                            next_track_id += 1
                        else:
                            # Update existing track
                            tracked_vehicles[vehicle.track_id].update_position(vehicle.bbox, vehicle.confidence)
                    
                    # Step 9: Check parking violations
                    for track_id, vehicle in tracked_vehicles.items():
                        parking_duration = vehicle.get_parking_duration()
                        threshold = self.processing_config.get('monitoring', {}).get('parking_duration_threshold', 300)
                        
                        if parking_duration > threshold and not vehicle.is_illegal:
                            print(f"⏰ [{stream_id}] Parking violation detected:")
                            print(f"   Duration: {parking_duration:.1f}s > {threshold}s threshold")
                            print(f"   Vehicle ID: {track_id}")
                            
                            # Step 10-13: Process violation
                            await self._process_parking_violation(frame, vehicle, stream_id, cctv)
                    
                    # Cleanup old tracks
                    self._cleanup_old_tracks(tracked_vehicles)
                    
                    # # 🧪 FORCED VIOLATION TEST FOR BACKEND TRANSMISSION (COMMENTED OUT)
                    # # Trigger backend test at frame 12 (processed frame due to skip rate)
                    # if frame_count == 12:  # Only once per stream
                    #     print(f"🧪 [{stream_id}] FORCED BACKEND TRANSMISSION TEST")
                    #     print("   Creating mock violation for backend testing...")
                    #     
                    #     # Create a mock vehicle for testing
                    #     test_vehicle = VehicleDetection(
                    #         bbox=(100, 100, 200, 200),
                    #         confidence=0.95,
                    #         vehicle_type="car"
                    #     )
                    #     test_vehicle.track_id = 999
                    #     test_vehicle.is_illegal = True  # Force as illegal
                    #     test_vehicle.first_seen = time.time() - 400  # Make it appear parked for 400s
                    #     
                    #     # 🧪 BYPASS AI DETECTION - Direct backend transmission test
                    #     print(f"🧪 [{stream_id}] BYPASSING AI DETECTION FOR DIRECT BACKEND TEST")
                    #     await self._direct_backend_test(frame, test_vehicle, stream_id, cctv)
                    
                    # Status update every 20 frames (more frequent for debugging)
                    if frame_count % 20 == 0:
                        print(f"🚗 [{stream_id}] Frame {frame_count}: {len(tracked_vehicles)} vehicles tracked")
                    
                    # Early frame debugging  
                    if frame_count <= 15:
                        print(f"🔍 [{stream_id}] Processing Frame {frame_count} (after skip check)")
                    
                    await asyncio.sleep(processing_interval)
                    
                except Exception as e:
                    logger.error(f"Error in stream {stream_id}: {e}")
                    await asyncio.sleep(1.0)  # Error recovery delay
                    
        except asyncio.CancelledError:
            logger.info(f"Stream processor cancelled: {stream_id}")
        except Exception as e:
            logger.error(f"Stream processor failed: {stream_id}: {e}")
        finally:
            logger.info(f"Stream processor ended: {stream_id}")

    def _get_synthetic_frame(self, cctv: Dict[str, Any], frame_count: int) -> np.ndarray:
        """Generate synthetic frame for demonstration (replace with real stream capture)"""
        # Create a simple synthetic frame with moving vehicles
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # Dark gray background
        
        # Add some synthetic "vehicles"
        t = frame_count * 0.1
        for i in range(2):  # 2 vehicles per stream
            x = int(100 + i * 200 + 30 * np.sin(t + i))
            y = int(200 + 20 * np.cos(t + i * 0.5))
            
            # Draw vehicle rectangle
            cv2.rectangle(frame, (x, y), (x + 80, y + 40), (0, 255, 0), 2)
            
            # Add some variation to simulate parking
            if frame_count > 50 and i == 0:  # First vehicle "parks" after frame 50
                x = 150  # Fixed position for parking simulation
                y = 200
                cv2.rectangle(frame, (x, y), (x + 80, y + 40), (0, 0, 255), 2)
        
        # Add stream info
        cv2.putText(frame, f"{cctv['streamId']}: {cctv['streamName'][:20]}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Frame: {frame_count}", 
                   (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

    def _track_vehicles_in_frame(self, frame: np.ndarray, stream_id: str, 
                               tracked_vehicles: Dict[int, VehicleDetection], 
                               next_track_id: int) -> List[VehicleDetection]:
        """Track vehicles in current frame using YOLO detection"""
        try:
            vehicles = []
            
            # Get vehicle detection configuration
            vehicle_config = self.models_config.get('vehicle_detection', {})
            confidence_threshold = vehicle_config.get('confidence_threshold', 0.5)
            
            # Run vehicle detection
            if 'vehicle' in self.models:
                results = self.models['vehicle'].predict(frame, conf=confidence_threshold, verbose=False)
                
                if results and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    confidences = results[0].boxes.conf.cpu().numpy()
                    
                    for i, (box, conf) in enumerate(zip(boxes, confidences)):
                        vehicle = VehicleDetection(
                            bbox=tuple(map(int, box)),
                            confidence=float(conf),
                            vehicle_type="car"
                        )
                        
                        # Simple tracking - in real implementation this would be more sophisticated
                        vehicle.track_id = self._assign_track_id(vehicle, tracked_vehicles, next_track_id)
                        vehicles.append(vehicle)
            
            self.stats['total_frames_processed'] += 1
            self.stats['total_vehicles_tracked'] += len(vehicles)
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Vehicle tracking error in {stream_id}: {e}")
            return []

    def _assign_track_id(self, vehicle: VehicleDetection, 
                        tracked_vehicles: Dict[int, VehicleDetection], 
                        next_track_id: int) -> int:
        """Assign track ID to detected vehicle (simple implementation)"""
        # Simple distance-based tracking
        min_distance = float('inf')
        best_track_id = next_track_id
        
        vx1, vy1, vx2, vy2 = vehicle.bbox
        v_center = ((vx1 + vx2) / 2, (vy1 + vy2) / 2)
        
        for track_id, tracked_vehicle in tracked_vehicles.items():
            tx1, ty1, tx2, ty2 = tracked_vehicle.bbox
            t_center = ((tx1 + tx2) / 2, (ty1 + ty2) / 2)
            
            distance = np.sqrt((v_center[0] - t_center[0])**2 + (v_center[1] - t_center[1])**2)
            
            if distance < min_distance and distance < 100:  # 100 pixel threshold
                min_distance = distance
                best_track_id = track_id
        
        return best_track_id

    def _cleanup_old_tracks(self, tracked_vehicles: Dict[int, VehicleDetection]) -> None:
        """Remove old vehicle tracks that haven't been seen recently"""
        current_time = time.time()
        max_age = 30.0  # 30 seconds
        
        to_remove = []
        for track_id, vehicle in tracked_vehicles.items():
            if current_time - vehicle.last_seen > max_age:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del tracked_vehicles[track_id]

    # =================================================================
    # STEP 10-13: Violation Detection and Processing Pipeline
    # =================================================================
    
    async def _process_parking_violation(self, frame: np.ndarray, vehicle: VehicleDetection, 
                                       stream_id: str, cctv: Dict[str, Any]) -> None:
        """Process parking violation through complete pipeline (Steps 10-13)"""
        try:
            print(f"📸 [{stream_id}] Processing violation for vehicle {vehicle.track_id}")
            
            # Step 10: Illegal Parking Detection
            illegal_result = self._detect_illegal_parking(frame, vehicle)
            
            if not illegal_result.is_illegal:
                print(f"   ✅ Legal parking - no violation")
                return
            
            print(f"🚫 [{stream_id}] Illegal parking detected:")
            print(f"   Confidence: {illegal_result.confidence:.2f}")
            print(f"   Illegal bbox: {illegal_result.bbox}")
            
            # Step 11: Bbox-based Image Cropping
            cropped_image = self._crop_violation_region(frame, vehicle.bbox, illegal_result.bbox)
            
            if cropped_image is None:
                print(f"   ❌ Image cropping failed")
                return
            
            # Step 12: OCR Processing
            ocr_result = self._apply_ocr_to_cropped_image(cropped_image)
            
            print(f"🔍 [{stream_id}] OCR Results:")
            print(f"   License plate: '{ocr_result.recognized_text}'")
            print(f"   Confidence: {ocr_result.confidence:.2f}")
            print(f"   Valid format: {ocr_result.is_valid_format}")
            
            # Step 13: Backend Violation Transmission
            success = await self._send_violation_to_backend(
                illegal_result, cropped_image, ocr_result, vehicle, stream_id, cctv
            )
            
            if success:
                self.stats['total_violations_sent'] += 1
                vehicle.is_illegal = True  # Mark as processed
                print(f"✅ [{stream_id}] Violation successfully reported to backend")
            else:
                print(f"❌ [{stream_id}] Failed to send violation to backend")
            
            self.stats['total_violations_detected'] += 1
            
        except Exception as e:
            print(f"❌ [{stream_id}] Violation processing failed: {e}")
            logger.error(f"Violation processing error: {e}")

    # async def _direct_backend_test(self, frame: np.ndarray, vehicle: VehicleDetection, 
    #                              stream_id: str, cctv: Dict[str, Any]) -> None:
    #     """🧪 Direct backend test - bypass AI detection for testing (COMMENTED OUT)"""
    #     try:
    #         print(f"🧪 [{stream_id}] DIRECT BACKEND TEST - Skipping AI detection")
    #         
    #         # Create mock illegal result
    #         from collections import namedtuple
    #         IllegalParkingResult = namedtuple('IllegalParkingResult', ['is_illegal', 'confidence', 'bbox'])
    #         illegal_result = IllegalParkingResult(
    #             is_illegal=True,
    #             confidence=0.92,
    #             bbox=(100, 100, 200, 200)
    #         )
    #         
    #         print(f"🚫 [{stream_id}] MOCK Illegal parking:")
    #         print(f"   Confidence: {illegal_result.confidence:.2f}")
    #         print(f"   Illegal bbox: {illegal_result.bbox}")
    #         
    #         # Step 11: Bbox-based Image Cropping
    #         cropped_image = self._crop_violation_region(frame, vehicle.bbox, illegal_result.bbox)
    #         
    #         if cropped_image is None:
    #             print(f"   ❌ Image cropping failed")
    #             return
    #         
    #         # Step 12: Mock OCR Results
    #         from collections import namedtuple
    #         OCRResult = namedtuple('OCRResult', ['recognized_text', 'confidence', 'is_valid_format'])
    #         ocr_result = OCRResult(
    #             recognized_text='123가4567',
    #             confidence=0.88,
    #             is_valid_format=True
    #         )
    #         
    #         print(f"🔍 [{stream_id}] MOCK OCR Results:")
    #         print(f"   License plate: '{ocr_result.recognized_text}'")
    #         print(f"   Confidence: {ocr_result.confidence:.2f}")
    #         print(f"   Valid format: {ocr_result.is_valid_format}")
    #         
    #         # Step 13: Backend Violation Transmission
    #         success = await self._send_violation_to_backend(
    #             illegal_result, cropped_image, ocr_result, vehicle, stream_id, cctv
    #         )
    #         
    #         if success:
    #             self.stats['total_violations_sent'] += 1
    #             vehicle.is_illegal = True  # Mark as processed
    #             print(f"✅ [{stream_id}] DIRECT TEST: Violation successfully reported to backend")
    #         else:
    #             print(f"❌ [{stream_id}] DIRECT TEST: Failed to send violation to backend")
    #         
    #         self.stats['total_violations_detected'] += 1
    #         
    #     except Exception as e:
    #         print(f"❌ [{stream_id}] Direct backend test failed: {e}")
    #         logger.error(f"Direct backend test error: {e}")

    def _detect_illegal_parking(self, frame: np.ndarray, vehicle: VehicleDetection) -> IllegalParkingResult:
        """Step 10: Detect illegal parking using YOLO classification model"""
        result = IllegalParkingResult()
        
        try:
            # Extract vehicle region
            x1, y1, x2, y2 = vehicle.bbox
            vehicle_crop = frame[y1:y2, x1:x2]
            
            if vehicle_crop.size == 0:
                return result
            
            # Get illegal parking configuration
            illegal_config = self.models_config.get('illegal_parking', {})
            confidence_threshold = illegal_config.get('confidence_threshold', 0.6)
            
            # Run illegal parking classification
            if 'illegal' in self.models:
                results = self.models['illegal'].predict(vehicle_crop, conf=confidence_threshold, verbose=False)
                
                if results and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    confidences = results[0].boxes.conf.cpu().numpy()
                    
                    # Get best detection
                    best_idx = np.argmax(confidences)
                    result.confidence = float(confidences[best_idx])
                    result.bbox = tuple(map(int, boxes[best_idx]))
                    result.is_illegal = result.confidence > confidence_threshold
            
            return result
            
        except Exception as e:
            logger.error(f"Illegal parking detection error: {e}")
            return result

    def _crop_violation_region(self, frame: np.ndarray, vehicle_bbox: Tuple[int, int, int, int], 
                             illegal_bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Step 11: Crop violation region based on illegal parking bbox + margin"""
        try:
            # Get cropping configuration
            crop_config = self.processing_config.get('analysis', {}).get('image_cropping', {})
            margin = crop_config.get('margin_pixels', 20)
            min_size = crop_config.get('min_crop_size', [100, 50])
            max_size = crop_config.get('max_crop_size', [400, 200])
            
            # Convert to absolute coordinates
            vx1, vy1, vx2, vy2 = vehicle_bbox
            ix1, iy1, ix2, iy2 = illegal_bbox
            
            # Absolute coordinates of illegal parking region
            abs_x1 = vx1 + ix1
            abs_y1 = vy1 + iy1
            abs_x2 = vx1 + ix2
            abs_y2 = vy1 + iy2
            
            # Apply margin
            crop_x1 = max(0, abs_x1 - margin)
            crop_y1 = max(0, abs_y1 - margin)
            crop_x2 = min(frame.shape[1], abs_x2 + margin)
            crop_y2 = min(frame.shape[0], abs_y2 + margin)
            
            crop_width = crop_x2 - crop_x1
            crop_height = crop_y2 - crop_y1
            
            # Check size constraints
            if crop_width < min_size[0] or crop_height < min_size[1]:
                logger.warning(f"Crop size too small: {crop_width}x{crop_height}")
                return None
            
            # Apply max size constraints if needed
            if crop_width > max_size[0] or crop_height > max_size[1]:
                center_x = (crop_x1 + crop_x2) // 2
                center_y = (crop_y1 + crop_y2) // 2
                crop_x1 = max(0, center_x - max_size[0] // 2)
                crop_x2 = min(frame.shape[1], center_x + max_size[0] // 2)
                crop_y1 = max(0, center_y - max_size[1] // 2)
                crop_y2 = min(frame.shape[0], center_y + max_size[1] // 2)
                crop_width = crop_x2 - crop_x1
                crop_height = crop_y2 - crop_y1
            
            # Extract cropped region
            cropped_image = frame[crop_y1:crop_y2, crop_x1:crop_x2]
            
            print(f"✂️ Image cropping completed:")
            print(f"   Original frame: {frame.shape[1]}x{frame.shape[0]}")
            print(f"   Vehicle bbox: {vehicle_bbox}")
            print(f"   Illegal bbox: {illegal_bbox}")
            print(f"   Crop region: {crop_width}x{crop_height} (margin: {margin}px)")
            
            return cropped_image
            
        except Exception as e:
            logger.error(f"Image cropping error: {e}")
            return None

    def _apply_ocr_to_cropped_image(self, cropped_image: np.ndarray) -> OCRResult:
        """Step 12: Apply OCR to cropped violation region"""
        try:
            # Get OCR configuration
            ocr_config = self.models_config.get('license_plate', {}).get('ocr', {})
            confidence_threshold = ocr_config.get('confidence_threshold', 0.8)
            
            if 'ocr' not in self.models:
                return OCRResult()
            
            # Apply OCR
            ocr_results = self.models['ocr'].recognize(cropped_image, detail=0)
            
            if ocr_results and len(ocr_results) > 0:
                recognized_text = ocr_results[0].strip()
                
                # Korean license plate format validation
                import re
                korean_plate_pattern = r'^\d{2,3}[가-힣]\d{4}$'
                is_valid_format = bool(re.match(korean_plate_pattern, recognized_text))
                
                # Confidence estimation (EasyOCR doesn't provide direct confidence)
                confidence = 0.9 if is_valid_format and len(recognized_text) >= 7 else 0.6
                
                return OCRResult(
                    recognized_text=recognized_text,
                    confidence=confidence,
                    is_valid_format=is_valid_format
                )
            
            return OCRResult()
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return OCRResult()

    async def _send_violation_to_backend(self, illegal_result: IllegalParkingResult,
                                       cropped_image: np.ndarray, ocr_result: OCRResult,
                                       vehicle: VehicleDetection, stream_id: str, 
                                       cctv: Dict[str, Any]) -> bool:
        """Step 13: Send violation data to backend via API"""
        try:
            # Encode cropped image to Base64
            _, buffer = cv2.imencode('.jpg', cropped_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Prepare violation data
            violation_data = {
                'violation_severity': illegal_result.confidence,
                'is_confirmed': True,
                'license_plate_text': ocr_result.recognized_text,
                'license_plate_confidence': ocr_result.confidence,
                'vehicle_type': vehicle.vehicle_type,
                'vehicle_confidence': vehicle.confidence,
                'parking_duration': vehicle.get_parking_duration(),
                'stream_id': stream_id,
                'cctv_name': cctv.get('streamName', ''),
                'location': cctv.get('location', ''),
                'latitude': cctv.get('latitude', 0.0),
                'longitude': cctv.get('longitude', 0.0),
                'vehicle_image': f"data:image/jpeg;base64,{image_base64}",
                'detected_at': datetime.now().isoformat()
            }
            
            # # 🧪 HARDCODED TEST JSON FOR BACKEND TRANSMISSION TEST (COMMENTED OUT)
            # # Create a small test image (black 100x100 image)
            # test_image = np.zeros((100, 100, 3), dtype=np.uint8)
            # _, test_buffer = cv2.imencode('.jpg', test_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            # test_image_base64 = base64.b64encode(test_buffer).decode('utf-8')
            
            # # MOCK DATA FOR TESTING (COMMENTED OUT)
            # mock_violation_data = {
            #     'violation_severity': 0.92,
            #     'is_confirmed': True,
            #     'license_plate_text': '123가4567',
            #     'license_plate_confidence': 0.88,
            #     'vehicle_type': 'car',
            #     'vehicle_confidence': 0.95,
            #     'parking_duration': 420.5,
            #     'stream_id': stream_id or 'test_stream_001',
            #     'cctv_name': '[테스트] 불법주차 탐지 CCTV',
            #     'location': '서울특별시 강남구 테헤란로 123',
            #     'latitude': 37.5013,
            #     'longitude': 127.0396,
            #     'vehicle_image': f"data:image/jpeg;base64,{test_image_base64}",
            #     'detected_at': datetime.now().isoformat()
            # }
            # 
            # print("🧪 Using mock_violation_data for backend test")
            # print(f"📋 Mock JSON: {mock_violation_data}")
            # 
            # # Use mock data instead of real data for testing
            # violation_data = mock_violation_data
            # 
            # print("🧪 BACKEND TRANSMISSION TEST - Sending hardcoded violation data")
            # print(f"📋 Mock violation data being sent: {violation_data}")
            
            # Get event reporter and send
            reporter = get_event_reporter()
            if not reporter:
                print("❌ Event reporter not available")
                return False
            
            # # Format as violation event (using existing event_reporter structure) - COMMENTED OUT
            # from parking_monitor import ParkingEvent  # Mock event structure
            # 
            # # Create a mock parking event for the reporter
            # parking_event = type('MockParkingEvent', (), {
            #     'event_id': f"violation_{stream_id}_{int(time.time())}",
            #     'stream_id': stream_id,
            #     'start_time': time.time() - vehicle.get_parking_duration(),
            #     'duration': vehicle.get_parking_duration(),
            #     'violation_severity': illegal_result.confidence,
            #     'is_confirmed': True,
            #     'vehicle_class': vehicle.vehicle_type,
            #     'location': (cctv.get('latitude', 0.0), cctv.get('longitude', 0.0)),
            #     'violation_frame': cropped_image
            # })()
            
            # Send to backend
            print("📡 Backend Violation Report API Request:")
            print(f"   Endpoint: POST /api/ai/v1/report-detection")
            print(f"   Stream: {stream_id}")
            print(f"   License Plate: '{ocr_result.recognized_text}'")
            print(f"   Confidence: {illegal_result.confidence:.2f}")
            print(f"   Image Size: {len(image_base64)} bytes (cropped region)")
            print(f"   Location: {cctv.get('location', 'Unknown')}")
            
            # # MOCK EVENT USAGE - COMMENTED OUT
            # success = await reporter.report_violation(
            #     parking_event=parking_event,
            #     vehicle_track=None,
            #     plate_detection=None,
            #     ocr_result=None
            # )
            
            # Get event reporter for actual backend transmission
            reporter = get_event_reporter()
            if not reporter:
                print("❌ Event reporter not available")
                return False

            # Create ParkingEvent object for the reporter
            from parking_monitor import ParkingEvent
            parking_event = ParkingEvent(
                event_id=f"violation_{stream_id}_{int(time.time())}",
                track_id=str(vehicle.track_id),
                stream_id=stream_id,
                vehicle_class=vehicle.vehicle_type,
                start_time=time.time() - vehicle.get_parking_duration(),
                duration=vehicle.get_parking_duration(),
                location=(cctv.get('latitude', 0.0), cctv.get('longitude', 0.0)),
                is_violation=True,
                violation_severity=illegal_result.confidence,
                confidence_score=vehicle.confidence
            )
            
            # Send violation to backend using event reporter
            success = await reporter.report_violation(
                parking_event=parking_event,
                vehicle_track=None,
                plate_detection=None,
                ocr_result=None
            )
            
            if success:
                print(f"   Status: ✅ SUCCESS - Violation reported to backend")
            else:
                print(f"   Status: ❌ FAILED - Backend API error")
            
            return success
            
        except Exception as e:
            print(f"❌ Backend transmission error: {e}")
            logger.error(f"Backend transmission error: {e}")
            return False

    async def run_visualization_mode(self, cctv_list: List[Dict[str, Any]], visualizer) -> None:
        """Run interactive visualization mode with OpenCV windows"""
        try:
            if not cctv_list:
                print("❌ No CCTV streams available for visualization")
                return
            
            if not self.models:
                print("❌ AI models not loaded")
                return
            
            # Limit streams for visualization
            max_streams = min(len(cctv_list), visualizer.max_streams if visualizer else 4)
            active_cctv_list = cctv_list[:max_streams]
            
            print(f"🎬 Interactive Visualization Mode")
            print(f"   Streams: {len(active_cctv_list)}")
            print("   Press 'q' to quit, 'space' to pause/resume")
            
            # Initialize visualization state
            self.is_running = True
            self.start_time = time.time()
            is_paused = False
            
            # Prepare stream data for visualization
            streams = {}
            for i, cctv in enumerate(active_cctv_list):
                stream_id = cctv.get('streamId', f'stream_{i}')
                stream_name = cctv.get('streamName', f'CCTV {i+1}')
                streams[stream_id] = {
                    'name': stream_name,
                    'active': True
                }
            
            print("✅ Visualization streams initialized")
            print("🎬 Starting interactive visualization loop...")
            print("   OpenCV windows should appear now...")
            
            # Main visualization loop (blocking, similar to standalone_demo.py)
            frame_count = 0
            
            while self.is_running:
                try:
                    if not is_paused:
                        # Create frames for each stream
                        display_frames = {}
                        
                        for stream_id, stream_info in streams.items():
                            if not stream_info['active']:
                                continue
                                
                            # Create demo frame (in real implementation, get from CCTV)
                            frame = self._create_demo_frame_direct(stream_info['name'], stream_id, frame_count)
                            display_frames[stream_id] = frame
                        
                        # Display frames in grid
                        if display_frames:
                            self._display_multi_stream_direct(display_frames)
                    
                    # Handle keyboard input
                    key = cv2.waitKey(30) & 0xFF
                    
                    if key == ord('q') or key == ord('Q'):
                        print("\n🛑 Quit requested by user ('q' pressed)")
                        break
                    elif key == ord(' '):
                        is_paused = not is_paused
                        status = "PAUSED" if is_paused else "RESUMED"
                        print(f"🎬 Visualization {status}")
                    
                    frame_count += 1
                    
                    # Small delay for ~30 FPS
                    await asyncio.sleep(0.033)
                        
                except Exception as e:
                    print(f"❌ Visualization loop error: {e}")
                    break
            
            print("✅ Visualization mode stopped")
            
        except Exception as e:
            print(f"❌ Visualization mode failed: {e}")
            logger.error(f"Visualization mode error: {e}")
        finally:
            # Cleanup OpenCV windows
            cv2.destroyAllWindows()
            print("🔄 OpenCV windows closed")

    def _create_demo_frame_direct(self, stream_name: str, stream_id: str, frame_count: int, width: int = 640, height: int = 480) -> np.ndarray:
        """Create a demo frame for direct visualization"""
        # Create black frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add gradient background
        for y in range(height):
            intensity = int(50 + (y / height) * 100)
            frame[y, :] = [intensity//3, intensity//2, intensity]
        
        # Add stream information
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Stream name
        cv2.putText(frame, stream_name[:30], (20, 40), font, 0.8, (255, 255, 255), 2)
        
        # Stream ID
        cv2.putText(frame, f"ID: {stream_id}", (20, 70), font, 0.6, (200, 200, 200), 1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (20, height - 50), font, 0.5, (150, 150, 150), 1)
        
        # Frame count
        cv2.putText(frame, f"Frame: {frame_count}", (20, height - 20), font, 0.5, (150, 150, 150), 1)
        
        # Live indicator
        cv2.circle(frame, (width - 50, 30), 8, (0, 255, 0), -1)
        cv2.putText(frame, "LIVE", (width - 90, 38), font, 0.4, (255, 255, 255), 1)
        
        # Add some moving elements for demo
        t = int(frame_count * 0.1)
        x_pos = (t % (width - 40)) + 20
        cv2.rectangle(frame, (x_pos - 20, height//2 - 10), (x_pos + 20, height//2 + 10), (0, 255, 255), -1)
        cv2.putText(frame, "DEMO", (x_pos - 15, height//2 + 5), font, 0.4, (0, 0, 0), 1)
        
        # Add mock vehicle detection boxes
        if frame_count % 60 < 30:  # Show detection for half the time
            cv2.rectangle(frame, (150, 200), (250, 280), (0, 255, 0), 2)
            cv2.putText(frame, "Vehicle: 0.85", (150, 190), font, 0.5, (0, 255, 0), 1)
        
        return frame
    
    def _display_multi_stream_direct(self, frames: Dict[str, np.ndarray]):
        """Display multiple streams in a grid directly"""
        stream_count = len(frames)
        if stream_count == 0:
            return
            
        # Calculate grid layout
        if stream_count == 1:
            rows, cols = 1, 1
        elif stream_count <= 2:
            rows, cols = 1, 2
        elif stream_count <= 4:
            rows, cols = 2, 2
        else:
            rows, cols = 2, 3
        
        # Resize frames for grid display
        target_width = 400
        target_height = 300
        
        resized_frames = []
        stream_ids = list(frames.keys())
        
        for i in range(rows * cols):
            if i < len(stream_ids):
                frame = frames[stream_ids[i]]
                resized_frame = cv2.resize(frame, (target_width, target_height))
            else:
                # Create empty black frame for unused grid positions
                resized_frame = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                cv2.putText(resized_frame, "Empty", (target_width//2 - 30, target_height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            
            resized_frames.append(resized_frame)
        
        # Create grid
        grid_rows = []
        for row in range(rows):
            row_frames = resized_frames[row * cols:(row + 1) * cols]
            grid_row = np.hstack(row_frames)
            grid_rows.append(grid_row)
        
        # Combine grid rows
        if len(grid_rows) > 1:
            grid = np.vstack(grid_rows)
        else:
            grid = grid_rows[0]
        
        # Add title
        title_height = 50
        title_frame = np.zeros((title_height, grid.shape[1], 3), dtype=np.uint8)
        cv2.putText(title_frame, f"Illegal Parking Detection - Live CCTV Streams ({stream_count})", 
                   (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add instructions
        cv2.putText(title_frame, "Press 'q' to quit, SPACE to pause", 
                   (grid.shape[1] - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Combine title and grid
        final_display = np.vstack([title_frame, grid])
        
        # Display
        cv2.imshow('CCTV Live Streams - Illegal Parking Detection', final_display)

    # =================================================================
    # System Management and Cleanup
    # =================================================================
    
    def print_final_statistics(self) -> None:
        """Print final processing statistics"""
        try:
            runtime = time.time() - self.start_time if self.start_time else 0
            
            print("\n" + "=" * 60)
            print("📊 FINAL PROCESSING STATISTICS")
            print("=" * 60)
            print(f"🕒 Total Runtime: {runtime:.1f} seconds")
            print(f"🎞️  Frames Processed: {self.stats['total_frames_processed']}")
            print(f"🚗 Vehicles Tracked: {self.stats['total_vehicles_tracked']}")
            print(f"🚫 Violations Detected: {self.stats['total_violations_detected']}")
            print(f"📡 Violations Sent: {self.stats['total_violations_sent']}")
            
            if runtime > 0:
                fps = self.stats['total_frames_processed'] / runtime
                print(f"📈 Average FPS: {fps:.1f}")
            
            if self.stats['total_violations_detected'] > 0:
                success_rate = self.stats['total_violations_sent'] / self.stats['total_violations_detected']
                print(f"✅ Transmission Success Rate: {success_rate:.1%}")
            
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"Error printing statistics: {e}")

    def cleanup(self) -> None:
        """Cleanup resources and connections"""
        try:
            print("\n🧹 Cleaning up resources...")
            
            self.is_running = False
            
            # Cleanup models (free GPU memory)
            if self.models:
                for model_name in self.models.keys():
                    try:
                        if hasattr(self.models[model_name], 'cpu'):
                            self.models[model_name].cpu()
                    except:
                        pass
                self.models.clear()
            
            # Clear GPU cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            
            print("✅ Cleanup completed")
            logger.info("Processor cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# =================================================================
# CCTV Stream Visualizer
# =================================================================

class CCTVStreamVisualizer:
    """Real-time CCTV stream visualizer for multiple streams"""
    
    def __init__(self, max_streams: int = 4):
        self.max_streams = max_streams
        self.streams = {}
        self.running = False
        self.visualizer_thread = None
        
    def start_visualization(self, cctv_list: List[Dict[str, Any]]):
        """Start visualizing CCTV streams"""
        print(f"\n📺 Starting CCTV Stream Visualization...")
        print(f"   Max streams: {self.max_streams}")
        
        # Select streams to visualize
        selected_streams = cctv_list[:self.max_streams]
        print(f"   Selected streams: {len(selected_streams)}")
        
        for i, cctv in enumerate(selected_streams):
            stream_id = cctv.get('streamId', f'stream_{i}')
            stream_url = cctv.get('streamUrl', '')
            stream_name = cctv.get('streamName', f'CCTV {i+1}')
            
            print(f"   📹 [{stream_id}] {stream_name}")
            
            # For demonstration, we'll create synthetic video feeds
            # In real implementation, you would use cv2.VideoCapture(stream_url)
            self.streams[stream_id] = {
                'name': stream_name,
                'url': stream_url,
                'cap': None,
                'frame': None,
                'active': True
            }
        
        # Start visualization thread
        self.running = True
        self.visualizer_thread = threading.Thread(target=self._visualization_loop, daemon=True)
        self.visualizer_thread.start()
        
        print("✅ CCTV Stream Visualization started")
        print("   Press 'q' in any stream window to quit visualization")
        
    def _visualization_loop(self):
        """Main visualization loop"""
        try:
            while self.running:
                # Create frames for each stream
                display_frames = {}
                
                for stream_id, stream_info in self.streams.items():
                    if not stream_info['active']:
                        continue
                        
                    # Create synthetic frame (in real implementation, read from stream_info['cap'])
                    frame = self._create_demo_frame(stream_info['name'], stream_id)
                    display_frames[stream_id] = frame
                
                # Display frames
                if display_frames:
                    self._display_multi_stream(display_frames)
                
                # Check for quit key
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("\n🛑 User requested visualization stop (pressed 'q')")
                    break
                    
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            print(f"❌ Visualization error: {e}")
        finally:
            self._cleanup_visualization()
    
    def _create_demo_frame(self, stream_name: str, stream_id: str, width: int = 640, height: int = 480) -> np.ndarray:
        """Create a demo frame for visualization"""
        # Create black frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add gradient background
        for y in range(height):
            intensity = int(50 + (y / height) * 100)
            frame[y, :] = [intensity//3, intensity//2, intensity]
        
        # Add stream information
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Stream name
        cv2.putText(frame, stream_name, (20, 40), font, 0.8, (255, 255, 255), 2)
        
        # Stream ID
        cv2.putText(frame, f"ID: {stream_id}", (20, 70), font, 0.6, (200, 200, 200), 1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (20, height - 20), font, 0.5, (150, 150, 150), 1)
        
        # Live indicator
        cv2.circle(frame, (width - 50, 30), 8, (0, 255, 0), -1)
        cv2.putText(frame, "LIVE", (width - 90, 38), font, 0.4, (255, 255, 255), 1)
        
        # Add some moving elements for demo
        t = int(time.time() * 2) % width
        cv2.rectangle(frame, (t - 20, height//2 - 10), (t + 20, height//2 + 10), (0, 255, 255), -1)
        cv2.putText(frame, "DEMO", (t - 15, height//2 + 5), font, 0.4, (0, 0, 0), 1)
        
        return frame
    
    def _display_multi_stream(self, frames: Dict[str, np.ndarray]):
        """Display multiple streams in a grid"""
        stream_count = len(frames)
        if stream_count == 0:
            return
            
        # Calculate grid layout
        if stream_count == 1:
            rows, cols = 1, 1
        elif stream_count <= 2:
            rows, cols = 1, 2
        elif stream_count <= 4:
            rows, cols = 2, 2
        else:
            rows, cols = 2, 3
        
        # Resize frames for grid display
        target_width = 400
        target_height = 300
        
        resized_frames = []
        stream_ids = list(frames.keys())
        
        for i in range(rows * cols):
            if i < len(stream_ids):
                frame = frames[stream_ids[i]]
                resized_frame = cv2.resize(frame, (target_width, target_height))
            else:
                # Create empty black frame for unused grid positions
                resized_frame = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                cv2.putText(resized_frame, "Empty", (target_width//2 - 30, target_height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            
            resized_frames.append(resized_frame)
        
        # Create grid
        grid_rows = []
        for row in range(rows):
            row_frames = resized_frames[row * cols:(row + 1) * cols]
            grid_row = np.hstack(row_frames)
            grid_rows.append(grid_row)
        
        # Combine grid rows
        if len(grid_rows) > 1:
            grid = np.vstack(grid_rows)
        else:
            grid = grid_rows[0]
        
        # Add title
        title_height = 50
        title_frame = np.zeros((title_height, grid.shape[1], 3), dtype=np.uint8)
        cv2.putText(title_frame, f"Illegal Parking Detection - Live CCTV Streams ({stream_count})", 
                   (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add instructions
        cv2.putText(title_frame, "Press 'q' to quit", 
                   (grid.shape[1] - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Combine title and grid
        final_display = np.vstack([title_frame, grid])
        
        # Display
        cv2.imshow('CCTV Live Streams', final_display)
    
    def _cleanup_visualization(self):
        """Clean up visualization resources"""
        print("\n🔄 Cleaning up visualization...")
        
        # Close video captures
        for stream_info in self.streams.values():
            if stream_info.get('cap'):
                stream_info['cap'].release()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        print("✅ Visualization cleanup complete")
    
    def stop(self):
        """Stop visualization"""
        if self.running:
            print("\n🛑 Stopping CCTV visualization...")
            self.running = False
            
            if self.visualizer_thread and self.visualizer_thread.is_alive():
                self.visualizer_thread.join(timeout=2)
            
            self._cleanup_visualization()

# =================================================================
# Signal Handling and Main Entry Point
# =================================================================

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received shutdown signal ({signum})")
    print("Initiating graceful shutdown...")
    
    # Cancel all running asyncio tasks
    import asyncio
    import sys
    import os
    
    try:
        print("🔄 Canceling asyncio tasks...")
        loop = asyncio.get_running_loop()
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
            
        print("🛑 Tasks canceled. Forcing shutdown...")
        loop.stop()
    except:
        pass
    
    # Force immediate exit
    print("💀 Emergency shutdown...")
    os._exit(0)


async def main(show_streams: bool = False, max_streams: int = 4):
    """Main entry point for the AI processor - implements 13-step sequential processing"""
    processor = None
    visualizer = None
    
    try:
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("🚀 Starting Illegal Parking Detection AI Processor")
        print("Implementation: 13-Step Sequential Processing System")
        print("=" * 60)
        
        # Create processor instance
        processor = IllegalParkingProcessor()
        
        # Initialize event reporter for backend communication
        print("📡 Initializing backend communication...")
        config = processor.config or {}  # Will be loaded in step 1
        await initialize_event_reporter(config.get('backend', {}))
        print("✅ Backend communication initialized")
        
        # Execute 13-step processing sequence
        print("\n🎯 Executing 13-Step Processing Sequence...")
        print("=" * 60)
        
        # Step 1-2: Configuration Loading
        if not processor.load_configurations():
            print("❌ Configuration loading failed - aborting")
            return
        
        # Step 3-4: CCTV Stream Search & Parsing
        cctv_list = processor.fetch_cctv_streams()
        if not cctv_list:
            print("❌ No CCTV streams found - aborting")
            return
        
        # Step 5: Geocoding Enhancement
        processor.enhance_cctv_with_geocoding(cctv_list)
        
        # Step 6: Backend CCTV Synchronization
        await processor.sync_cctv_to_backend(cctv_list)
        
        # Optional: Start CCTV Stream Visualization
        if show_streams:
            print(f"\n📺 Initializing CCTV Stream Visualization...")
            visualizer = CCTVStreamVisualizer(max_streams=max_streams)
            visualizer.start_visualization(cctv_list)
        
        # Step 7: AI Model Loading
        if not processor.load_ai_models():
            print("❌ AI model loading failed - aborting")
            return
        
        # Step 8-13: Multi-stream Processing
        if show_streams:
            # Visualization mode: Run interactive OpenCV loop
            print(f"\n🎬 Starting Interactive Visualization Mode...")
            print("   Controls: 'q' to quit, 'space' to pause/resume")
            await processor.run_visualization_mode(cctv_list, visualizer)
        else:
            # Background processing mode: Run continuous processing
            await processor.start_multi_stream_processing(cctv_list)
        
    except KeyboardInterrupt:
        print("\n🛑 User requested shutdown (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error in main: {e}")
    finally:
        # Cleanup visualizer first (if active)
        if visualizer:
            print("🔄 Stopping CCTV visualization...")
            visualizer.stop()
        
        if processor:
            processor.print_final_statistics()
            processor.cleanup()
        
        # Cleanup event reporter
        reporter = get_event_reporter()
        if reporter:
            await reporter.cleanup()
        
        print("\n👋 AI Processor shutdown complete. Goodbye!")


if __name__ == "__main__":
    """
    Main entry point for the Illegal Parking Detection AI Processor.
    
    Usage:
        python main.py                    # Run full AI processing pipeline
        python main.py --show 4           # Run with live CCTV stream visualization (max 4 streams)
    
    The processor will execute the complete 13-step pipeline:
    1-2.  Load YAML configurations
    3-4.  Fetch and parse CCTV streams from Korean ITS API
    5.    Enhance with VWorld geocoding
    6.    Synchronize CCTV data to backend
    7.    Load all AI models (Vehicle, Illegal Parking, License Plate, OCR)
    8-9.  Start multi-stream processing with vehicle tracking
    10.   Detect illegal parking violations
    11.   Crop violation regions with margin
    12.   Apply OCR to cropped images
    13.   Send violation reports to backend
    """
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Illegal Parking Detection AI Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full AI processing pipeline
  python main.py --show 2           # Show live streams for max 2 CCTV cameras
  python main.py --show 6           # Show live streams for max 6 CCTV cameras

13-Step Processing Pipeline:
  1-2.  YAML Configuration Loading
  3-4.  CCTV Stream Search & Parsing
  5.    Geocoding Enhancement  
  6.    Backend CCTV Synchronization
  7.    AI Model Loading
  8-9.  Multi-stream Vehicle Tracking
  10.   Illegal Parking Detection
  11.   Bbox-based Image Cropping
  12.   OCR Processing
  13.   Backend Violation Transmission
        """
    )
    
    parser.add_argument(
        '--show', 
        type=int, 
        metavar='N',
        help='Enable live CCTV stream visualization for max N streams (e.g., --show 4)'
    )
    
    args = parser.parse_args()
    
    # Determine visualization parameters
    show_streams = args.show is not None
    max_streams = args.show if show_streams else 4
    
    # Validate max_streams parameter
    if show_streams:
        if max_streams < 1 or max_streams > 10:
            print("❌ Error: Maximum streams must be between 1 and 10")
            sys.exit(1)
        
        print(f"🎬 Visualization mode enabled - showing up to {max_streams} streams")
        print("   Press 'q' in the visualization window to quit")
        
    try:
        asyncio.run(main(show_streams=show_streams, max_streams=max_streams))
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Startup error: {e}")
        sys.exit(1)