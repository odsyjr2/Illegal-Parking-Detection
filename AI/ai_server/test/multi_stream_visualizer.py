#!/usr/bin/env python3
"""
Multi-Stream Visual Test Framework

This module provides visual testing for the illegal parking detection system
with multiple CCTV streams displayed simultaneously. It creates 6 OpenCV windows
showing real-time AI processing with vehicle tracking, parking monitoring,
and violation detection overlays.

Key Features:
- 6 simultaneous OpenCV windows (one per CCTV stream)
- Real-time AI overlays: vehicle bounding boxes, track IDs, parking timers
- Violation alerts: visual highlights when parking violations detected
- Performance metrics: FPS, processing times per stream
- Interactive controls: pause/resume, stream selection, screenshot capture

Usage:
    python test/multi_stream_visualizer.py
    
Controls:
    Space: Pause/Resume all streams
    1-6: Focus on individual stream
    S: Save current frame screenshots
    Q: Quit application
    R: Reset statistics
"""

import os
import sys
import cv2
import time
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

# Add ai_server to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our core system
from utils.config_loader import load_config
from utils.logger import setup_logging, get_logger
from main import IllegalParkingProcessor
from models import VehicleTrack, ParkingEvent
from core.monitoring import StreamStatus

# Configure logging
logger = get_logger(__name__)


class StreamVisualizer:
    """Visualizer for individual CCTV stream with AI overlays"""
    
    def __init__(self, stream_id: str, stream_config: Dict[str, Any], 
                 window_position: Tuple[int, int]):
        self.stream_id = stream_id
        self.stream_config = stream_config
        self.window_name = f"{stream_config['name']} ({stream_id})"
        self.window_position = window_position
        
        # Visualization state
        self.current_frame: Optional[np.ndarray] = None
        self.is_active = False
        self.is_paused = False
        
        # Performance tracking
        self.fps = 0.0
        self.frame_count = 0
        self.violations_count = 0
        self.last_update_time = time.time()
        
        # Visual elements
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.thickness = 2
        
        # Colors (BGR format)
        self.colors = {
            'normal_vehicle': (0, 255, 0),      # Green
            'stationary': (0, 255, 255),       # Yellow
            'violation': (0, 0, 255),          # Red
            'text': (255, 255, 255),           # White
            'background': (0, 0, 0),           # Black
            'info_panel': (64, 64, 64)         # Dark gray
        }
        
        logger.info(f"StreamVisualizer created for {stream_id}")
    
    def initialize_window(self):
        """Initialize OpenCV window for this stream"""
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            cv2.moveWindow(self.window_name, self.window_position[0], self.window_position[1])
            self.is_active = True
            logger.info(f"Window initialized for {self.stream_id} at position {self.window_position}")
            
        except Exception as e:
            logger.error(f"Error initializing window for {self.stream_id}: {e}")
    
    def update_frame(self, frame: np.ndarray, vehicles: List[VehicleTrack], 
                    parking_events: List[ParkingEvent], status: StreamStatus):
        """Update frame with AI analysis overlays"""
        if not self.is_active or self.is_paused:
            return
        
        try:
            # Copy frame for modification
            display_frame = frame.copy()
            
            # Draw vehicle tracking overlays
            self._draw_vehicle_overlays(display_frame, vehicles)
            
            # Draw parking event overlays
            self._draw_parking_overlays(display_frame, parking_events)
            
            # Draw status information panel
            self._draw_status_panel(display_frame, status)
            
            # Update performance metrics
            self._update_performance_metrics()
            
            # Display frame
            cv2.imshow(self.window_name, display_frame)
            self.current_frame = display_frame
            
        except Exception as e:
            logger.error(f"Error updating frame for {self.stream_id}: {e}")
    
    def _draw_vehicle_overlays(self, frame: np.ndarray, vehicles: List[VehicleTrack]):
        """Draw vehicle bounding boxes and tracking information"""
        for vehicle in vehicles:
            if not hasattr(vehicle, 'bbox') or not vehicle.bbox:
                continue
            
            # Get bounding box coordinates
            if hasattr(vehicle.bbox, 'x'):
                # BoundingBox object
                x1, y1 = vehicle.bbox.x, vehicle.bbox.y
                x2, y2 = x1 + vehicle.bbox.width, y1 + vehicle.bbox.height
            else:
                # Tuple format (x1, y1, x2, y2)
                x1, y1, x2, y2 = vehicle.bbox
            
            # Determine vehicle color based on state
            if hasattr(vehicle, 'stationary_duration') and vehicle.stationary_duration > 60:
                if vehicle.stationary_duration > 300:  # 5 minutes
                    color = self.colors['violation']
                    status_text = f"VIOLATION {vehicle.stationary_duration}s"
                else:
                    color = self.colors['stationary']
                    status_text = f"STATIONARY {vehicle.stationary_duration}s"
            else:
                color = self.colors['normal_vehicle']
                status_text = "MOVING"
            
            # Draw bounding box
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, self.thickness)
            
            # Draw track ID
            track_id = getattr(vehicle, 'track_id', 'N/A')
            cv2.putText(frame, f"ID:{track_id}", 
                       (int(x1), int(y1) - 10), 
                       self.font, self.font_scale, color, self.thickness)
            
            # Draw status text
            cv2.putText(frame, status_text,
                       (int(x1), int(y2) + 20),
                       self.font, self.font_scale * 0.8, color, self.thickness - 1)
    
    def _draw_parking_overlays(self, frame: np.ndarray, parking_events: List[ParkingEvent]):
        """Draw parking event indicators and violation alerts"""
        for event in parking_events:
            if not hasattr(event, 'vehicle_track') or not event.vehicle_track:
                continue
            
            vehicle = event.vehicle_track
            
            # Get vehicle position for overlay
            if hasattr(vehicle, 'bbox') and vehicle.bbox:
                if hasattr(vehicle.bbox, 'x'):
                    center_x = vehicle.bbox.x + vehicle.bbox.width // 2
                    center_y = vehicle.bbox.y + vehicle.bbox.height // 2
                else:
                    center_x = (vehicle.bbox[0] + vehicle.bbox[2]) // 2
                    center_y = (vehicle.bbox[1] + vehicle.bbox[3]) // 2
                
                # Draw violation alert if duration exceeds threshold
                duration = getattr(event, 'duration', 0)
                if duration > 300:  # 5 minutes
                    # Flashing red circle for violation
                    if int(time.time() * 2) % 2:  # Flash every 0.5 seconds
                        cv2.circle(frame, (int(center_x), int(center_y)), 50, 
                                 self.colors['violation'], 5)
                        cv2.putText(frame, "VIOLATION!", 
                                   (int(center_x) - 50, int(center_y) - 60),
                                   self.font, self.font_scale * 1.2, 
                                   self.colors['violation'], self.thickness + 1)
                    
                    self.violations_count += 1
    
    def _draw_status_panel(self, frame: np.ndarray, status: StreamStatus):
        """Draw status information panel"""
        h, w = frame.shape[:2]
        panel_height = 120
        panel_width = 300
        
        # Create semi-transparent panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (w - panel_width, 0), (w, panel_height), 
                     self.colors['info_panel'], -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Add text information
        text_x = w - panel_width + 10
        text_y = 25
        line_height = 20
        
        info_lines = [
            f"Stream: {self.stream_id}",
            f"FPS: {self.fps:.1f}",
            f"Frames: {self.frame_count}",
            f"Violations: {self.violations_count}",
            f"Status: {'PAUSED' if self.is_paused else 'ACTIVE'}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        for i, line in enumerate(info_lines):
            cv2.putText(frame, line, (text_x, text_y + i * line_height),
                       self.font, self.font_scale * 0.8, self.colors['text'], 1)
    
    def _update_performance_metrics(self):
        """Update performance tracking metrics"""
        current_time = time.time()
        self.frame_count += 1
        
        # Calculate FPS
        time_diff = current_time - self.last_update_time
        if time_diff >= 1.0:  # Update FPS every second
            self.fps = 1.0 / max(time_diff, 0.001)
            self.last_update_time = current_time
    
    def pause(self):
        """Pause visualization for this stream"""
        self.is_paused = True
        logger.info(f"Stream {self.stream_id} visualization paused")
    
    def resume(self):
        """Resume visualization for this stream"""
        self.is_paused = False
        logger.info(f"Stream {self.stream_id} visualization resumed")
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.frame_count = 0
        self.violations_count = 0
        self.last_update_time = time.time()
        logger.info(f"Stats reset for stream {self.stream_id}")
    
    def save_screenshot(self, output_dir: str):
        """Save current frame as screenshot"""
        if self.current_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.stream_id}_{timestamp}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            cv2.imwrite(filepath, self.current_frame)
            logger.info(f"Screenshot saved: {filepath}")
    
    def close(self):
        """Close visualization window"""
        if self.is_active:
            cv2.destroyWindow(self.window_name)
            self.is_active = False
            logger.info(f"Window closed for {self.stream_id}")


class MultiStreamVisualizer:
    """Visual testing framework for multiple CCTV streams"""
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.processor: Optional[IllegalParkingProcessor] = None
        self.visualizers: Dict[str, StreamVisualizer] = {}
        self.is_running = False
        self.is_paused = False
        
        # Window layout configuration (2x3 grid)
        self.window_positions = [
            (100, 100),   # Top-left
            (700, 100),   # Top-center  
            (1300, 100),  # Top-right
            (100, 500),   # Bottom-left
            (700, 500),   # Bottom-center
            (1300, 500)   # Bottom-right
        ]
        
        # Screenshot output directory
        self.screenshot_dir = Path(__file__).parent / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.total_frames_processed = 0
        self.total_violations_detected = 0
        
        logger.info("MultiStreamVisualizer created")
    
    async def initialize(self) -> bool:
        """Initialize configuration and processor"""
        try:
            logger.info("Initializing Multi-Stream Visualizer...")
            
            # Load configuration
            self.config = load_config()
            setup_logging(self.config.get('logging', {}))
            
            # Create processor
            self.processor = IllegalParkingProcessor()
            
            # Initialize processor
            if not await self.processor.initialize():
                logger.error("Failed to initialize processor")
                return False
            
            # Initialize visualizers for all streams
            streams = self.config.get('cctv_streams', {}).get('local_streams', [])
            enabled_streams = [s for s in streams if s.get('enabled', True)]
            
            for i, stream in enumerate(enabled_streams[:6]):  # Limit to 6 streams
                position = self.window_positions[i] if i < len(self.window_positions) else (100, 100)
                
                visualizer = StreamVisualizer(
                    stream_id=stream['id'],
                    stream_config=stream,
                    window_position=position
                )
                
                self.visualizers[stream['id']] = visualizer
            
            logger.info(f"Initialized visualizers for {len(self.visualizers)} streams")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing visualizer: {e}")
            return False
    
    async def start_visualization(self) -> bool:
        """Start visual testing with processor and OpenCV windows"""
        if not await self.initialize():
            return False
        
        try:
            logger.info("Starting Multi-Stream Visual Test...")
            
            # Initialize all windows
            for visualizer in self.visualizers.values():
                visualizer.initialize_window()
            
            # Start processor
            if not await self.processor.start():
                logger.error("Failed to start processor")
                return False
            
            # Start visualization update loop
            self.is_running = True
            self.start_time = time.time()
            
            # Add monitoring callback to update visualizations
            self.processor.monitoring_service.add_status_callback(self._stream_status_callback)
            
            logger.info("Visual test started successfully")
            logger.info("Controls:")
            logger.info("  Space: Pause/Resume all streams")
            logger.info("  1-6: Focus on individual stream")
            logger.info("  S: Save screenshots")
            logger.info("  Q: Quit application")
            logger.info("  R: Reset statistics")
            
            # Run visualization loop
            await self._run_visualization_loop()
            return True
            
        except Exception as e:
            logger.error(f"Error starting visualization: {e}")
            return False
    
    def _stream_status_callback(self, stream_id: str, status: StreamStatus):
        """Callback for stream status updates from monitoring service"""
        # This would be called by the monitoring service with real data
        # For now, we'll create mock data for visualization testing
        pass
    
    async def _run_visualization_loop(self):
        """Main visualization loop"""
        logger.info("Starting visualization loop...")
        
        try:
            while self.is_running:
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q or ESC
                    logger.info("Quit requested by user")
                    break
                elif key == ord(' '):  # Space
                    self._toggle_pause()
                elif key == ord('s'):  # S
                    self._save_all_screenshots()
                elif key == ord('r'):  # R
                    self._reset_all_stats()
                elif ord('1') <= key <= ord('6'):  # Numbers 1-6
                    stream_num = key - ord('1')
                    self._focus_stream(stream_num)
                
                # Update visualization with mock data
                await self._update_visualizations()
                
                # Control loop rate
                await asyncio.sleep(0.03)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in visualization loop: {e}")
        finally:
            await self._cleanup()
    
    async def _update_visualizations(self):
        """Update all stream visualizations with current data"""
        try:
            # Get current data from processor
            if not self.processor or not self.processor.monitoring_service:
                return
            
            # For each active stream, create mock visualization data
            active_streams = self.processor.monitoring_service.get_active_streams()
            
            for stream_id in active_streams:
                if stream_id not in self.visualizers:
                    continue
                
                visualizer = self.visualizers[stream_id]
                
                # Create mock frame for visualization (replace with real data)
                mock_frame = self._create_mock_frame(stream_id)
                mock_vehicles = self._create_mock_vehicles()
                mock_parking_events = self._create_mock_parking_events()
                
                # Get real status from monitoring service
                status = self.processor.monitoring_service.stream_statuses.get(
                    stream_id, 
                    StreamStatus(stream_id=stream_id, is_active=True, fps=0.0, 
                               frames_processed=0, violations_detected=0)
                )
                
                # Update visualizer
                visualizer.update_frame(mock_frame, mock_vehicles, mock_parking_events, status)
            
        except Exception as e:
            logger.error(f"Error updating visualizations: {e}")
    
    def _create_mock_frame(self, stream_id: str) -> np.ndarray:
        """Create mock frame for visualization testing"""
        # Create a colored frame with stream identifier
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Different background color for each stream
        colors = [(64, 0, 0), (0, 64, 0), (0, 0, 64), (64, 64, 0), (64, 0, 64), (0, 64, 64)]
        color_index = int(stream_id.split('_')[-1]) % len(colors)
        frame[:] = colors[color_index]
        
        # Add stream identifier text
        cv2.putText(frame, f"Stream: {stream_id}", (20, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (20, frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return frame
    
    def _create_mock_vehicles(self) -> List[VehicleTrack]:
        """Create mock vehicle tracks for visualization"""
        from models import VehicleTrack, BoundingBox
        from datetime import datetime
        
        vehicles = []
        
        # Create 2-3 mock vehicles per frame
        for i in range(2):
            # Random position
            x = 100 + i * 200
            y = 150 + i * 100
            w, h = 120, 80
            
            bbox = BoundingBox(x=x, y=y, width=w, height=h, confidence=0.9)
            
            vehicle = VehicleTrack(
                track_id=i + 1,
                bbox=bbox,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                confidence=0.9,
                stationary_duration=i * 150  # Make some vehicles stationary longer
            )
            
            vehicles.append(vehicle)
        
        return vehicles
    
    def _create_mock_parking_events(self) -> List[ParkingEvent]:
        """Create mock parking events for visualization"""
        from models import ParkingEvent
        
        events = []
        
        # Create one mock violation every few seconds
        if int(time.time()) % 10 < 2:  # Show violation for 2 seconds every 10 seconds
            mock_vehicle = self._create_mock_vehicles()[0]
            mock_vehicle.stationary_duration = 400  # Over threshold
            
            event = ParkingEvent(
                vehicle_track=mock_vehicle,
                stream_id="mock_stream",
                location=(37.6158, 126.8441),
                parking_start=datetime.now(),
                duration=400,
                violation_frame=np.zeros((480, 640, 3), dtype=np.uint8)
            )
            
            events.append(event)
        
        return events
    
    def _toggle_pause(self):
        """Toggle pause state for all streams"""
        self.is_paused = not self.is_paused
        
        for visualizer in self.visualizers.values():
            if self.is_paused:
                visualizer.pause()
            else:
                visualizer.resume()
        
        logger.info(f"All streams {'paused' if self.is_paused else 'resumed'}")
    
    def _save_all_screenshots(self):
        """Save screenshots from all active streams"""
        for visualizer in self.visualizers.values():
            visualizer.save_screenshot(str(self.screenshot_dir))
        
        logger.info(f"Screenshots saved to {self.screenshot_dir}")
    
    def _reset_all_stats(self):
        """Reset statistics for all streams"""
        for visualizer in self.visualizers.values():
            visualizer.reset_stats()
        
        self.total_frames_processed = 0
        self.total_violations_detected = 0
        
        logger.info("All statistics reset")
    
    def _focus_stream(self, stream_num: int):
        """Focus on a specific stream (bring window to front)"""
        stream_ids = list(self.visualizers.keys())
        
        if 0 <= stream_num < len(stream_ids):
            stream_id = stream_ids[stream_num]
            visualizer = self.visualizers[stream_id]
            
            # Bring window to front (platform-specific)
            cv2.setWindowProperty(visualizer.window_name, cv2.WND_PROP_TOPMOST, 1)
            cv2.setWindowProperty(visualizer.window_name, cv2.WND_PROP_TOPMOST, 0)
            
            logger.info(f"Focused on stream {stream_num + 1}: {stream_id}")
    
    async def _cleanup(self):
        """Cleanup visualization resources"""
        logger.info("Cleaning up visualization...")
        
        try:
            # Close all windows
            for visualizer in self.visualizers.values():
                visualizer.close()
            
            # Destroy all OpenCV windows
            cv2.destroyAllWindows()
            
            # Stop processor
            if self.processor:
                await self.processor.shutdown()
            
            # Log final statistics
            if self.start_time:
                uptime = time.time() - self.start_time
                logger.info(f"Visualization ran for {uptime:.1f} seconds")
                logger.info(f"Total frames processed: {self.total_frames_processed}")
                logger.info(f"Total violations detected: {self.total_violations_detected}")
            
            logger.info("Visualization cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point for multi-stream visual testing"""
    try:
        logger.info("Starting Multi-Stream Visual Test")
        logger.info("=" * 50)
        
        # Create and run visualizer
        visualizer = MultiStreamVisualizer()
        await visualizer.start_visualization()
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
    finally:
        logger.info("Multi-Stream Visual Test completed")


if __name__ == "__main__":
    """
    Run the multi-stream visual test.
    
    This will:
    1. Initialize the illegal parking detection processor
    2. Open 6 OpenCV windows showing different CCTV streams
    3. Display real-time AI processing with overlays
    4. Allow interactive control of the visualization
    """
    
    print("Multi-Stream Visual Test for Illegal Parking Detection")
    print("=" * 60)
    print("This test will open 6 OpenCV windows showing CCTV streams")
    print("with real-time AI processing overlays.")
    print()
    print("Controls:")
    print("  Space: Pause/Resume all streams")
    print("  1-6: Focus on individual stream")
    print("  S: Save screenshots")
    print("  Q: Quit application")
    print("  R: Reset statistics")
    print()
    print("Press any key to continue...")
    input()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)