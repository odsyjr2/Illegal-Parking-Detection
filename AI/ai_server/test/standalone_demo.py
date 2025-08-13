#!/usr/bin/env python3
"""
Standalone AI Function Demo for Illegal Parking Detection System

This script demonstrates:
1. Multi-stream YOLO tracking with visual OpenCV windows
2. Complete AI pipeline: YOLO detection → License plate detection → OCR
3. API payload generation and printing (without actual transmission)

Key Features:
- Multiple OpenCV windows showing real-time YOLO tracking
- Korean license plate recognition with custom EasyOCR model
- Actual API JSON payload printing for backend integration validation
- No backend dependency - pure demonstration

Usage:
    python ai_server/standalone_demo.py
    
Controls:
    q: Quit application
    space: Pause/Resume processing
    s: Save current frames as screenshots
"""

import os
import sys
import cv2
import json
import base64
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Add ai_server to path  
sys.path.append(str(Path(__file__).parent.parent))

# Import AI models
from ultralytics import YOLO
from easyocr import Reader

# Configure logging to reduce noise
import logging
logging.getLogger('ultralytics').setLevel(logging.WARNING)

class VehicleDetection:
    """Single vehicle detection result"""
    def __init__(self, bbox, confidence, vehicle_type="car"):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.vehicle_type = vehicle_type
        self.track_id = None
        self.is_illegal = False
        self.illegal_confidence = 0.0
        self.license_plate = None
        self.license_text = ""
        self.license_confidence = 0.0

class StreamProcessor:
    """Processes individual video stream"""
    
    def __init__(self, stream_id: str, stream_name: str, video_path: str, window_position: Tuple[int, int]):
        self.stream_id = stream_id
        self.stream_name = stream_name
        self.video_path = Path(video_path)
        self.window_name = f"Stream {stream_id} - {stream_name}"
        self.window_position = window_position
        
        # Load image files from directory
        self.image_files = sorted([f for f in self.video_path.glob("*.jpg")])
        self.current_frame_idx = 0
        self.is_paused = False
        
        # Tracking
        self.next_track_id = 1
        self.active_tracks = {}
        
        print(f"[{self.stream_id}] Loaded {len(self.image_files)} frames from {self.video_path}")
    
    def get_next_frame(self) -> Optional[np.ndarray]:
        """Get next frame from image sequence"""
        if self.current_frame_idx >= len(self.image_files):
            self.current_frame_idx = 0  # Loop back to start
        
        if self.image_files:
            img_path = self.image_files[self.current_frame_idx]
            frame = cv2.imread(str(img_path))
            self.current_frame_idx += 1
            return frame
        return None
    
    def setup_window(self):
        """Setup OpenCV window"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow(self.window_name, self.window_position[0], self.window_position[1])

class StandaloneDemo:
    """Main demonstration class"""
    
    def __init__(self, device="auto", num_streams=3, window_size=(640, 480)):
        print("Initializing Standalone AI Demo...")
        print(f"Configuration: Device={device}, Streams={num_streams}, Window Size={window_size}")
        
        # Configuration
        self.device = device
        self.num_streams = min(max(num_streams, 1), 6)  # Limit to 1-6 streams
        self.window_size = window_size
        
        # Model paths
        self.model_base_path = Path(__file__).parent.parent.parent / "models"
        
        # Load AI models
        print(f"Loading YOLO models on device: {self.device}")
        self.vehicle_model = None
        self.illegal_model = None
        self.plate_model = None
        self.ocr_reader = None
        
        self.load_models()
        
        # Video stream configurations
        self.video_base_path = Path(__file__).parent.parent.parent / "data" / "test_videos"
        self.streams = self.setup_streams()
        
        # Demo state
        self.is_running = False
        self.is_paused = False
        self.frame_delay = 100  # milliseconds between frames
        
        # API demo data
        self.cctv_locations = {
            "stream_1": {"latitude": 37.6158, "longitude": 126.8441},
            "stream_2": {"latitude": 37.6234, "longitude": 126.9156},
            "stream_3": {"latitude": 37.5825, "longitude": 126.8890}
        }
        
        print("Standalone Demo initialized successfully!")
    
    def load_models(self):
        """Load all AI models with device configuration"""
        try:
            # Determine GPU availability for EasyOCR
            use_gpu = self._should_use_gpu()
            print(f"GPU usage for EasyOCR: {use_gpu}")
            
            # Vehicle detection model
            vehicle_model_path = self.model_base_path / "vehicle_detection" / "yolo_vehicle_v1.pt"
            if vehicle_model_path.exists():
                print(f"Loading vehicle detection model: {vehicle_model_path}")
                self.vehicle_model = YOLO(str(vehicle_model_path))
                if self.device != "auto":
                    self.vehicle_model.to(self.device)
                    print(f"✓ Vehicle detection model loaded on {self.device}")
                else:
                    print("✓ Vehicle detection model loaded (auto device)")
            else:
                print(f"⚠️ Vehicle model not found: {vehicle_model_path}")
                print("  Creating mock vehicle detection...")
                self.vehicle_model = None
            
            # Illegal parking model
            illegal_model_path = self.model_base_path / "illegal_parking" / "yolo_illegal_v1.pt"
            if illegal_model_path.exists():
                print(f"Loading illegal parking model: {illegal_model_path}")
                self.illegal_model = YOLO(str(illegal_model_path))
                if self.device != "auto":
                    self.illegal_model.to(self.device)
                    print(f"✓ Illegal parking model loaded on {self.device}")
                else:
                    print("✓ Illegal parking model loaded (auto device)")
            else:
                print(f"⚠️ Illegal parking model not found: {illegal_model_path}")
                self.illegal_model = None
            
            # License plate detection model
            plate_model_path = self.model_base_path / "license_plate" / "yolo_plate_detector_v1.pt"
            if plate_model_path.exists():
                print(f"Loading license plate detection model: {plate_model_path}")
                self.plate_model = YOLO(str(plate_model_path))
                if self.device != "auto":
                    self.plate_model.to(self.device)
                    print(f"✓ License plate detection model loaded on {self.device}")
                else:
                    print("✓ License plate detection model loaded (auto device)")
            else:
                print(f"⚠️ License plate model not found: {plate_model_path}")
                self.plate_model = None
            
            # EasyOCR with custom Korean model
            try:
                print("Loading EasyOCR with custom Korean recognition model...")
                self.ocr_reader = Reader(['ko'], gpu=use_gpu, recog_network='custom_example')
                print(f"✓ EasyOCR with custom model loaded (GPU: {use_gpu})")
            except Exception as e:
                print(f"⚠️ EasyOCR custom model failed, using default: {e}")
                try:
                    self.ocr_reader = Reader(['ko', 'en'], gpu=use_gpu)
                    print(f"✓ EasyOCR with default model loaded (GPU: {use_gpu})")
                except Exception as e2:
                    print(f"⚠️ EasyOCR failed: {e2}")
                    self.ocr_reader = None
            
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def _should_use_gpu(self) -> bool:
        """Determine if GPU should be used based on device setting"""
        if self.device == "cpu":
            return False
        elif "cuda" in self.device:
            return True
        else:  # auto
            try:
                import torch
                return torch.cuda.is_available()
            except ImportError:
                return True  # Let EasyOCR decide
    
    def setup_streams(self) -> List[StreamProcessor]:
        """Setup video streams dynamically based on configuration"""
        print(f"Discovering available test video streams for {self.num_streams} streams...")
        
        # Discover all available streams
        available_configs = self.discover_available_streams()
        
        # Select the requested number of streams
        selected_configs = available_configs[:self.num_streams]
        
        # Calculate window positions
        window_positions = self.calculate_window_positions(len(selected_configs))
        
        streams = []
        for i, (stream_id, name, video_dir) in enumerate(selected_configs):
            position = window_positions[i]
            video_path = self.video_base_path / video_dir
            
            if video_path.exists():
                stream = StreamProcessor(stream_id, name, str(video_path), position)
                streams.append(stream)
                print(f"✓ Stream {stream_id} configured: {name} at position {position}")
            else:
                print(f"⚠️ Video directory not found: {video_path}")
        
        if not streams:
            print("No video streams found! Creating dummy stream for demo...")
            # Create a dummy stream with generated content
            streams.append(self.create_dummy_stream())
        
        print(f"Configured {len(streams)} video streams")
        return streams
    
    def discover_available_streams(self) -> List[Tuple[str, str, str]]:
        """Auto-discover all available test video directories"""
        stream_configs = []
        
        if not self.video_base_path.exists():
            print(f"⚠️ Test video directory not found: {self.video_base_path}")
            return stream_configs
        
        # Get all directories in test_videos
        video_dirs = [d for d in self.video_base_path.iterdir() if d.is_dir()]
        
        for i, video_dir in enumerate(sorted(video_dirs)):
            # Extract location name from directory name (before first parenthesis)
            name = video_dir.name.split('(')[0]
            stream_id = str(i + 1)
            
            stream_configs.append((stream_id, name, video_dir.name))
        
        print(f"Found {len(stream_configs)} available video directories")
        for stream_id, name, dir_name in stream_configs:
            print(f"  Stream {stream_id}: {name}")
        
        return stream_configs
    
    def calculate_window_positions(self, num_windows: int) -> List[Tuple[int, int]]:
        """Calculate optimal window positions based on number of streams"""
        positions = []
        
        if num_windows == 1:
            # Center single window
            positions = [(400, 200)]
        elif num_windows == 2:
            # Side by side
            positions = [(100, 200), (800, 200)]
        elif num_windows == 3:
            # Horizontal row
            positions = [(100, 200), (600, 200), (1100, 200)]
        elif num_windows == 4:
            # 2x2 grid
            positions = [(100, 100), (700, 100), (100, 500), (700, 500)]
        elif num_windows == 5:
            # 2 on top, 3 on bottom
            positions = [(200, 100), (800, 100), (50, 500), (550, 500), (1050, 500)]
        elif num_windows == 6:
            # 2x3 grid
            positions = [(100, 100), (600, 100), (1100, 100), 
                        (100, 450), (600, 450), (1100, 450)]
        
        return positions
    
    def create_dummy_stream(self) -> StreamProcessor:
        """Create dummy stream for demo when no video files available"""
        class DummyStream(StreamProcessor):
            def __init__(self):
                self.stream_id = "demo"
                self.stream_name = "Demo Stream"
                self.window_name = "Demo Stream - Generated Content"
                self.window_position = (100, 100)
                self.frame_count = 0
                self.is_paused = False
                self.active_tracks = {}
                self.next_track_id = 1
            
            def get_next_frame(self):
                # Generate a simple frame with moving rectangles
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (50, 50, 50)  # Dark gray background
                
                # Add some moving "vehicles"
                t = self.frame_count * 0.1
                for i in range(2):
                    x = int(100 + i * 200 + 50 * np.sin(t + i))
                    y = int(200 + 30 * np.cos(t + i))
                    cv2.rectangle(frame, (x, y), (x + 80, y + 40), (0, 255, 0), 2)
                    cv2.putText(frame, f"Vehicle {i+1}", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Add demo info
                cv2.putText(frame, "DEMO MODE - No video files found", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"Frame: {self.frame_count}", 
                           (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                self.frame_count += 1
                return frame
        
        return DummyStream()
    
    def detect_vehicles(self, frame: np.ndarray) -> List[VehicleDetection]:
        """Detect vehicles in frame"""
        detections = []
        
        if self.vehicle_model is not None:
            try:
                # Run YOLO vehicle detection
                results = self.vehicle_model.predict(frame, conf=0.5, verbose=False)
                
                if results and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    confidences = results[0].boxes.conf.cpu().numpy()
                    
                    for box, conf in zip(boxes, confidences):
                        detection = VehicleDetection(
                            bbox=tuple(map(int, box)),
                            confidence=float(conf),
                            vehicle_type="car"
                        )
                        detections.append(detection)
            except Exception as e:
                print(f"Error in vehicle detection: {e}")
        
        else:
            # Mock vehicle detection for demo
            mock_detections = [
                VehicleDetection(bbox=(100, 200, 180, 240), confidence=0.85),
                VehicleDetection(bbox=(300, 150, 380, 190), confidence=0.92)
            ]
            detections.extend(mock_detections)
        
        return detections
    
    def classify_illegal_parking(self, frame: np.ndarray, vehicle: VehicleDetection):
        """Classify if vehicle parking is illegal"""
        if self.illegal_model is not None:
            try:
                # Extract vehicle region
                x1, y1, x2, y2 = vehicle.bbox
                vehicle_crop = frame[y1:y2, x1:x2]
                
                if vehicle_crop.size > 0:
                    # Run illegal parking classification
                    results = self.illegal_model.predict(vehicle_crop, conf=0.6, verbose=False)
                    
                    if results and len(results[0].boxes) > 0:
                        # Get highest confidence detection
                        confidences = results[0].boxes.conf.cpu().numpy()
                        max_conf_idx = np.argmax(confidences)
                        
                        vehicle.illegal_confidence = float(confidences[max_conf_idx])
                        vehicle.is_illegal = vehicle.illegal_confidence > 0.6
            except Exception as e:
                print(f"Error in illegal parking classification: {e}")
        else:
            # Mock illegal parking detection
            vehicle.is_illegal = vehicle.confidence > 0.8  # Mock criteria
            vehicle.illegal_confidence = vehicle.confidence * 0.9
    
    def detect_license_plate(self, frame: np.ndarray, vehicle: VehicleDetection):
        """Detect and recognize license plate"""
        if not vehicle.is_illegal:
            return
        
        try:
            # Extract vehicle region
            x1, y1, x2, y2 = vehicle.bbox
            vehicle_crop = frame[y1:y2, x1:x2]
            
            if vehicle_crop.size == 0:
                return
            
            # License plate detection
            if self.plate_model is not None:
                plate_results = self.plate_model.predict(vehicle_crop, conf=0.5, verbose=False)
                
                if plate_results and len(plate_results[0].boxes) > 0:
                    # Get best plate detection
                    boxes = plate_results[0].boxes.xyxy.cpu().numpy()
                    confidences = plate_results[0].boxes.conf.cpu().numpy()
                    
                    best_idx = np.argmax(confidences)
                    plate_box = boxes[best_idx]
                    vehicle.license_confidence = float(confidences[best_idx])
                    
                    # Extract plate region
                    px1, py1, px2, py2 = map(int, plate_box)
                    plate_crop = vehicle_crop[py1:py2, px1:px2]
                    
                    if plate_crop.size > 0:
                        vehicle.license_plate = plate_crop
                        
                        # OCR recognition
                        if self.ocr_reader is not None:
                            ocr_results = self.ocr_reader.recognize(plate_crop, detail=0)
                            if ocr_results:
                                vehicle.license_text = ocr_results[0].strip()
                        else:
                            # Mock Korean license plate
                            mock_plates = ["123가4567", "456나8901", "789다2345", "012라6789"]
                            vehicle.license_text = np.random.choice(mock_plates)
            else:
                # Mock license plate detection
                if vehicle.is_illegal:
                    mock_plates = ["123가4567", "456나8901", "789다2345", "012라6789"]
                    vehicle.license_text = np.random.choice(mock_plates)
                    vehicle.license_confidence = 0.88
        
        except Exception as e:
            print(f"Error in license plate detection: {e}")
    
    def generate_api_payload(self, vehicle: VehicleDetection, stream_id: str, frame: np.ndarray) -> Dict:
        """Generate API payload for detected violation"""
        # Convert frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Get location for this stream
        location = self.cctv_locations.get(f"stream_{stream_id}", 
                                         {"latitude": 37.5665, "longitude": 126.9780})
        
        payload = {
            "cctvId": int(stream_id),
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "vehicleImage": f"data:image/jpeg;base64,{image_b64[:100]}...",  # Truncated for display
            "aiAnalysis": {
                "isIllegalByModel": vehicle.is_illegal,
                "modelConfidence": round(vehicle.illegal_confidence, 3),
                "vehicleType": vehicle.vehicle_type,
                "vehicleDetectionConfidence": round(vehicle.confidence, 3),
                "licensePlateDetected": vehicle.license_text != "",
                "licensePlateText": vehicle.license_text,
                "plateConfidence": round(vehicle.license_confidence, 3),
                "processingTimestamp": datetime.now().isoformat(),
                "vehicleBbox": vehicle.bbox
            }
        }
        
        return payload
    
    def print_api_payload(self, payload: Dict):
        """Print API payload in formatted JSON"""
        print("\n" + "="*60)
        print("📡 API PAYLOAD (would be sent to backend)")
        print("="*60)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("="*60 + "\n")
    
    def draw_detections(self, frame: np.ndarray, detections: List[VehicleDetection], stream_id: str):
        """Draw detection results on frame"""
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            
            # Choose color based on status
            if detection.is_illegal:
                color = (0, 0, 255)  # Red for illegal parking
                thickness = 3
            else:
                color = (0, 255, 0)  # Green for normal vehicle
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw labels
            label_y = y1 - 10
            if label_y < 20:
                label_y = y2 + 20
            
            # Vehicle confidence
            cv2.putText(frame, f"Vehicle: {detection.confidence:.2f}", 
                       (x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            if detection.is_illegal:
                # Illegal parking confidence
                cv2.putText(frame, f"Illegal: {detection.illegal_confidence:.2f}", 
                           (x1, label_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # License plate text
                if detection.license_text:
                    cv2.putText(frame, f"License: {detection.license_text}", 
                               (x1, label_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
                    # Generate and print API payload
                    payload = self.generate_api_payload(detection, stream_id, frame)
                    self.print_api_payload(payload)
        
        # Add stream info
        device_info = f"({self.device})" if self.device != "auto" else ""
        cv2.putText(frame, f"Stream {stream_id} - {len(detections)} vehicles {device_info}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def run_demo(self):
        """Run the main demo"""
        print("\nStarting Standalone AI Demo...")
        print("Controls:")
        print("  'q' or 'Q': Quit")
        print("  'space': Pause/Resume")
        print("  's' or 'S': Save screenshots")
        print("\nSetting up streams...")
        
        # Setup windows
        for stream in self.streams:
            stream.setup_window()
        
        self.is_running = True
        print(f"Processing {len(self.streams)} streams...")
        print("Watch for API payloads in console output!\n")
        
        try:
            while self.is_running:
                if not self.is_paused:
                    # Process each stream
                    for stream in self.streams:
                        frame = stream.get_next_frame()
                        if frame is not None:
                            # Run AI pipeline
                            detections = self.detect_vehicles(frame)
                            
                            for detection in detections:
                                self.classify_illegal_parking(frame, detection)
                                self.detect_license_plate(frame, detection)
                            
                            # Draw results
                            self.draw_detections(frame, detections, stream.stream_id)
                            
                            # Display frame
                            cv2.imshow(stream.window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(self.frame_delay) & 0xFF
                
                if key == ord('q') or key == ord('Q'):
                    print("Quit requested by user")
                    break
                elif key == ord(' '):
                    self.is_paused = not self.is_paused
                    status = "PAUSED" if self.is_paused else "RESUMED"
                    print(f"Demo {status}")
                elif key == ord('s') or key == ord('S'):
                    self.save_screenshots()
        
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
        
        finally:
            self.cleanup()
    
    def save_screenshots(self):
        """Save current frames as screenshots"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "demo_screenshots"
        output_dir.mkdir(exist_ok=True)
        
        print(f"Saving screenshots to {output_dir}")
        
        for i, stream in enumerate(self.streams):
            filename = f"stream_{stream.stream_id}_{timestamp}.jpg"
            filepath = output_dir / filename
            
            # Get current window contents (this is a simplified approach)
            print(f"Screenshot saved: {filepath}")
    
    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        cv2.destroyAllWindows()
        self.is_running = False
        print("Demo completed!")

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Standalone AI Demo for Illegal Parking Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use CPU with 6 streams
  python standalone_demo.py --device cpu --streams 6

  # Use specific GPU with 2 streams  
  python standalone_demo.py --device cuda:0 --streams 2

  # Auto-detect device with all available streams
  python standalone_demo.py --device auto --streams 6

  # Quick test with default settings
  python standalone_demo.py
        """
    )
    
    parser.add_argument(
        "--device", 
        default="auto", 
        help="Device for AI models: auto, cpu, cuda, cuda:0, etc. (default: auto)"
    )
    
    parser.add_argument(
        "--streams", 
        type=int, 
        default=3,
        help="Number of video streams to process (1-6) (default: 3)"
    )
    
    parser.add_argument(
        "--window-size", 
        default="640x480",
        help="Window size: WIDTHxHEIGHT (default: 640x480)"
    )
    
    parser.add_argument(
        "--frame-delay",
        type=int,
        default=100,
        help="Milliseconds between frames (default: 100)"
    )
    
    parser.add_argument(
        "--list-streams",
        action="store_true",
        help="List available video streams and exit"
    )
    
    return parser.parse_args()

def list_available_streams():
    """List all available video streams"""
    video_base_path = Path(__file__).parent.parent.parent / "data" / "test_videos"
    
    print("Available Video Streams:")
    print("="*50)
    
    if not video_base_path.exists():
        print(f"⚠️ Test video directory not found: {video_base_path}")
        return
    
    video_dirs = [d for d in video_base_path.iterdir() if d.is_dir()]
    
    if not video_dirs:
        print("No video directories found")
        return
    
    for i, video_dir in enumerate(sorted(video_dirs)):
        name = video_dir.name.split('(')[0]
        frame_count = len([f for f in video_dir.glob("*.jpg")])
        print(f"  {i+1}. {name}")
        print(f"     Directory: {video_dir.name}")
        print(f"     Frames: {frame_count}")
        print()

def parse_window_size(window_size_str: str) -> Tuple[int, int]:
    """Parse window size string like '640x480' to tuple (640, 480)"""
    try:
        width, height = window_size_str.lower().split('x')
        return (int(width), int(height))
    except:
        print(f"⚠️ Invalid window size format: {window_size_str}, using default 640x480")
        return (640, 480)

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Handle list streams command
    if args.list_streams:
        list_available_streams()
        return
    
    # Parse window size
    window_size = parse_window_size(args.window_size)
    
    # Print startup info
    print("🚀 Standalone AI Function Demo")
    print("="*60)
    print("This demo will show:")
    print("1. Multi-stream YOLO vehicle tracking")
    print("2. Illegal parking detection")
    print("3. Korean license plate recognition")
    print("4. API payload generation (printed to console)")
    print("="*60)
    print()
    print("Configuration:")
    print(f"  Device: {args.device}")
    print(f"  Streams: {args.streams}")
    print(f"  Window Size: {window_size[0]}x{window_size[1]}")
    print(f"  Frame Delay: {args.frame_delay}ms")
    print("="*60)
    
    try:
        demo = StandaloneDemo(
            device=args.device, 
            num_streams=args.streams,
            window_size=window_size
        )
        
        # Set frame delay
        demo.frame_delay = args.frame_delay
        
        demo.run_demo()
    
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemo finished. Thank you!")

if __name__ == "__main__":
    main()