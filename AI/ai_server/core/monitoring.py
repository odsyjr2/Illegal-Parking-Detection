"""
Monitoring Service Module - Phase 1: Continuous Stream Monitoring

This module implements the lightweight monitoring service that continuously watches
all CCTV streams for potential parking violations. It operates with minimal resource
usage and hands off violation candidates to the analysis service via task queue.

Key Features:
- Lightweight continuous monitoring across multiple CCTV streams
- Integration with existing AI modules for basic tracking and parking monitoring
- Task queue communication to Phase 2 analysis service
- Backend client integration for CCTV stream configuration
- Performance monitoring and health checks

Architecture:
- MonitoringService: Main coordinator for all stream monitoring
- StreamMonitor: Individual stream monitoring threads
- BackendClient: CCTV stream configuration fetching
- Task queue integration with AnalysisTask creation
"""

import logging
import time
import threading
import asyncio
import requests
from queue import Queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import cv2
import numpy as np

# Import existing AI components
from cctv_manager import get_cctv_manager, CCTVManager
from multi_vehicle_tracker import get_vehicle_tracker, MultiVehicleTracker
from parking_monitor import get_parking_monitor, ParkingMonitorManager
from models import AnalysisTask, ParkingEvent, VehicleTrack, create_analysis_task, TaskPriority
from utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)


@dataclass
class StreamStatus:
    """Status information for a monitored stream"""
    stream_id: str
    is_active: bool
    fps: float
    frames_processed: int
    violations_detected: int
    last_frame_time: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


class BackendClient:
    """Client for communicating with Spring Backend"""
    
    def __init__(self, backend_url: str, timeout: int = 30):
        self.backend_url = backend_url
        self.timeout = timeout
        self.session = requests.Session()
        
    async def fetch_cctv_streams(self) -> List[Dict[str, Any]]:
        """Fetch CCTV stream configurations from backend"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/cctvs",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                streams = response.json()
                logger.info(f"Fetched {len(streams)} CCTV streams from backend")
                return streams
            else:
                logger.warning(f"Backend returned status {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch CCTV streams from backend: {e}")
            return []
    
    def report_stream_status(self, stream_id: str, status: StreamStatus) -> bool:
        """Report stream status to backend"""
        try:
            payload = {
                "streamId": stream_id,
                "isActive": status.is_active,
                "fps": status.fps,
                "framesProcessed": status.frames_processed,
                "violationsDetected": status.violations_detected,
                "lastFrameTime": status.last_frame_time.isoformat() if status.last_frame_time else None,
                "errorCount": status.error_count,
                "lastError": status.last_error
            }
            
            response = self.session.post(
                f"{self.backend_url}/api/monitoring/stream-status",
                json=payload,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            logger.error(f"Failed to report stream status: {e}")
            return False


class StreamMonitor(threading.Thread):
    """Individual stream monitoring thread - runs continuously with lightweight processing"""
    
    def __init__(self, stream_id: str, stream_config: Dict[str, Any], 
                 monitoring_service: 'MonitoringService'):
        super().__init__(name=f"StreamMonitor-{stream_id}", daemon=True)
        
        self.stream_id = stream_id
        self.stream_config = stream_config
        self.monitoring_service = monitoring_service
        self.config = monitoring_service.config
        
        # Component references
        self.cctv_manager = monitoring_service.cctv_manager
        self.vehicle_tracker = monitoring_service.vehicle_tracker
        self.parking_monitor = monitoring_service.parking_monitor
        
        # Monitoring state
        self.is_running = False
        self.is_paused = False
        self.status = StreamStatus(
            stream_id=stream_id,
            is_active=False,
            fps=0.0,
            frames_processed=0,
            violations_detected=0
        )
        
        # Performance tracking
        self.frame_times = []
        self.last_status_report = 0.0
        
        # Configuration
        self.monitoring_config = self.config.get('monitoring', {})
        self.update_interval = self.monitoring_config.get('update_interval', 0.1)
        self.status_report_interval = self.monitoring_config.get('status_report_interval', 60.0)
        
        logger.info(f"StreamMonitor created for {stream_id}")
    
    def start_monitoring(self) -> bool:
        """Start monitoring this stream"""
        if self.is_running:
            logger.warning(f"Monitoring already active for {self.stream_id}")
            return True
            
        try:
            # Initialize stream-specific components
            if not self._initialize_stream():
                return False
                
            self.is_running = True
            self.is_paused = False
            self.status.is_active = True
            
            self.start()  # Start thread
            logger.info(f"Started monitoring for stream {self.stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring for {self.stream_id}: {e}")
            return False
    
    def _initialize_stream(self) -> bool:
        """Initialize stream-specific tracking components"""
        try:
            # Initialize stream in vehicle tracker
            success = self.vehicle_tracker.initialize_stream_tracker(self.stream_id)
            if not success:
                logger.error(f"Failed to initialize vehicle tracker for {self.stream_id}")
                return False
            
            # Initialize stream in parking monitor
            success = self.parking_monitor.initialize_stream_monitor(self.stream_id)
            if not success:
                logger.error(f"Failed to initialize parking monitor for {self.stream_id}")
                return False
            
            logger.info(f"Stream components initialized for {self.stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing stream {self.stream_id}: {e}")
            return False
    
    def run(self):
        """Main monitoring loop - lightweight processing only"""
        logger.info(f"Monitoring loop started for {self.stream_id}")
        
        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                frame_start_time = time.time()
                
                # 1. Get frame from CCTV stream
                frame_data = self.cctv_manager.get_frame(self.stream_id)
                if frame_data is None:
                    time.sleep(0.01)  # Short delay if no frame available
                    continue
                
                frame, timestamp = frame_data
                
                # 2. Perform lightweight vehicle detection and tracking
                vehicles = self._process_vehicles(frame, timestamp)
                
                # 3. Update parking monitoring (duration tracking only)
                parking_events = self._update_parking_monitoring(vehicles, timestamp)
                
                # 4. Check for violation candidates and create analysis tasks
                self._process_violation_candidates(parking_events, frame, timestamp)
                
                # 5. Update performance metrics
                self._update_performance_metrics(frame_start_time)
                
                # 6. Report status periodically
                self._report_status_if_needed()
                
                # 7. Control processing rate
                time.sleep(max(0, self.update_interval - (time.time() - frame_start_time)))
                
        except Exception as e:
            logger.error(f"Error in monitoring loop for {self.stream_id}: {e}")
            self.status.error_count += 1
            self.status.last_error = str(e)
        finally:
            self.status.is_active = False
            logger.info(f"Monitoring loop ended for {self.stream_id}")
    
    def _process_vehicles(self, frame: np.ndarray, timestamp: float) -> List[VehicleTrack]:
        """Perform lightweight vehicle detection and tracking"""
        try:
            # Use existing vehicle tracker for lightweight detection
            vehicles = self.vehicle_tracker.process_stream_frame(
                self.stream_id, frame, timestamp
            )
            return vehicles
            
        except Exception as e:
            logger.error(f"Error processing vehicles for {self.stream_id}: {e}")
            return []
    
    def _update_parking_monitoring(self, vehicles: List[VehicleTrack], 
                                 timestamp: float) -> List[ParkingEvent]:
        """Update parking duration monitoring"""
        try:
            # Use existing parking monitor for duration tracking
            parking_events = self.parking_monitor.update_stream_monitoring(
                self.stream_id, vehicles, timestamp
            )
            return parking_events
            
        except Exception as e:
            logger.error(f"Error updating parking monitoring for {self.stream_id}: {e}")
            return []
    
    def _process_violation_candidates(self, parking_events: List[ParkingEvent],
                                    frame: np.ndarray, timestamp: float):
        """Check for violation candidates and create analysis tasks"""
        try:
            violation_threshold = self.config.get('processing', {}).get(
                'parking_duration_threshold', 300
            )
            
            for event in parking_events:
                # Check if parking duration exceeds threshold
                if event.duration >= violation_threshold:
                    # Create analysis task for Phase 2
                    event.violation_frame = frame.copy()  # Capture current frame
                    
                    task = create_analysis_task(event, TaskPriority.NORMAL)
                    self.monitoring_service.task_queue.put(task)
                    
                    self.status.violations_detected += 1
                    logger.info(f"Created analysis task for violation in {self.stream_id}: "
                              f"vehicle {event.vehicle_track.track_id}, duration {event.duration}s")
                    
        except Exception as e:
            logger.error(f"Error processing violation candidates for {self.stream_id}: {e}")
    
    def _update_performance_metrics(self, frame_start_time: float):
        """Update performance tracking metrics"""
        frame_time = time.time() - frame_start_time
        self.frame_times.append(frame_time)
        
        # Keep only recent frame times for FPS calculation
        if len(self.frame_times) > 30:
            self.frame_times = self.frame_times[-30:]
        
        # Calculate FPS
        if len(self.frame_times) > 1:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.status.fps = 1.0 / max(avg_frame_time, 0.001)
        
        self.status.frames_processed += 1
        self.status.last_frame_time = datetime.now()
    
    def _report_status_if_needed(self):
        """Report status to monitoring service periodically"""
        current_time = time.time()
        
        if current_time - self.last_status_report >= self.status_report_interval:
            self.monitoring_service.update_stream_status(self.stream_id, self.status)
            self.last_status_report = current_time
    
    def pause_monitoring(self):
        """Pause monitoring for this stream"""
        self.is_paused = True
        logger.info(f"Monitoring paused for {self.stream_id}")
    
    def resume_monitoring(self):
        """Resume monitoring for this stream"""
        self.is_paused = False
        logger.info(f"Monitoring resumed for {self.stream_id}")
    
    def stop_monitoring(self):
        """Stop monitoring for this stream"""
        self.is_running = False
        logger.info(f"Stopping monitoring for {self.stream_id}")


class MonitoringService:
    """Phase 1: Continuous multi-stream monitoring with minimal resource usage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.streams_config = config.get('cctv_streams', {})
        self.monitoring_config = config.get('monitoring', {})
        
        # AI Components (lightweight versions for monitoring)
        self.cctv_manager: Optional[CCTVManager] = None
        self.vehicle_tracker: Optional[MultiVehicleTracker] = None
        self.parking_monitor: Optional[ParkingMonitorManager] = None
        
        # Phase 1 → Phase 2 communication
        self.task_queue: Optional[Queue] = None
        
        # Backend integration
        self.backend_client = BackendClient(config.get('backend', {}).get('url', ''))
        
        # Monitoring state
        self.active_streams: Dict[str, StreamMonitor] = {}
        self.stream_statuses: Dict[str, StreamStatus] = {}
        self.is_monitoring = False
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.total_violations_detected = 0
        
        # Event callbacks
        self.status_callbacks: List[Callable[[str, StreamStatus], None]] = []
        
        logger.info("MonitoringService initialized")
    
    def initialize_components(self, task_queue: Queue) -> bool:
        """Initialize AI components and task queue"""
        try:
            # Get AI component instances
            self.cctv_manager = get_cctv_manager()
            self.vehicle_tracker = get_vehicle_tracker()
            self.parking_monitor = get_parking_monitor()
            
            # Set task queue for Phase 2 communication
            self.task_queue = task_queue
            
            # Validate components
            components_ready = [
                ("CCTV Manager", self.cctv_manager is not None),
                ("Vehicle Tracker", self.vehicle_tracker is not None),
                ("Parking Monitor", self.parking_monitor is not None),
                ("Task Queue", self.task_queue is not None)
            ]
            
            all_ready = True
            for name, ready in components_ready:
                status = "✓ Ready" if ready else "✗ Not Ready"
                logger.info(f"Monitoring Component {name}: {status}")
                if not ready:
                    all_ready = False
            
            if all_ready:
                logger.info("All monitoring components initialized successfully")
            else:
                logger.error("Some monitoring components failed to initialize")
            
            return all_ready
            
        except Exception as e:
            logger.error(f"Error initializing monitoring components: {e}")
            return False
    
    async def start_monitoring(self, stream_ids: Optional[List[str]] = None) -> bool:
        """Start continuous monitoring for specified streams or all configured streams"""
        if self.is_monitoring:
            logger.warning("Monitoring service is already running")
            return True
        
        try:
            # Get stream configurations
            streams = await self._get_stream_configurations(stream_ids)
            if not streams:
                logger.error("No streams available for monitoring")
                return False
            
            # Create and start stream monitors
            success = True
            for stream_config in streams:
                stream_id = stream_config['id']
                
                try:
                    # Create stream monitor
                    monitor = StreamMonitor(stream_id, stream_config, self)
                    
                    # Start monitoring
                    if monitor.start_monitoring():
                        self.active_streams[stream_id] = monitor
                        self.stream_statuses[stream_id] = monitor.status
                        logger.info(f"Started monitoring for stream {stream_id}")
                    else:
                        logger.error(f"Failed to start monitoring for stream {stream_id}")
                        success = False
                        
                except Exception as e:
                    logger.error(f"Error creating monitor for stream {stream_id}: {e}")
                    success = False
            
            if success:
                self.is_monitoring = True
                self.start_time = time.time()
                logger.info(f"Monitoring service started for {len(self.active_streams)} streams")
            else:
                logger.error("Failed to start some stream monitors")
                await self.stop_monitoring()  # Cleanup partial start
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting monitoring service: {e}")
            return False
    
    async def _get_stream_configurations(self, stream_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get stream configurations from backend or local config"""
        streams = []
        
        try:
            # Try to fetch from backend first
            if self.streams_config.get('fetch_from_backend', False):
                backend_streams = await self.backend_client.fetch_cctv_streams()
                if backend_streams:
                    streams = backend_streams
                    logger.info(f"Using {len(streams)} streams from backend")
            
            # Fallback to local configuration
            if not streams and self.streams_config.get('fallback_enabled', True):
                local_streams = self.streams_config.get('local_streams', [])
                streams = [s for s in local_streams if s.get('enabled', True)]
                logger.info(f"Using {len(streams)} local streams as fallback")
            
            # Filter by stream IDs if specified
            if stream_ids:
                streams = [s for s in streams if s['id'] in stream_ids]
                logger.info(f"Filtered to {len(streams)} specified streams")
            
            return streams
            
        except Exception as e:
            logger.error(f"Error getting stream configurations: {e}")
            return []
    
    async def stop_monitoring(self):
        """Stop monitoring all streams"""
        if not self.is_monitoring:
            return
        
        logger.info("Stopping monitoring service...")
        
        # Stop all stream monitors
        for stream_id, monitor in list(self.active_streams.items()):
            try:
                monitor.stop_monitoring()
                if monitor.is_alive():
                    monitor.join(timeout=5.0)
            except Exception as e:
                logger.error(f"Error stopping monitor for {stream_id}: {e}")
        
        # Clear state
        self.active_streams.clear()
        self.stream_statuses.clear()
        self.is_monitoring = False
        
        logger.info("Monitoring service stopped")
    
    def pause_monitoring(self, stream_ids: Optional[List[str]] = None):
        """Pause monitoring for specified streams or all streams"""
        target_streams = stream_ids or list(self.active_streams.keys())
        
        for stream_id in target_streams:
            monitor = self.active_streams.get(stream_id)
            if monitor:
                monitor.pause_monitoring()
    
    def resume_monitoring(self, stream_ids: Optional[List[str]] = None):
        """Resume monitoring for specified streams or all streams"""
        target_streams = stream_ids or list(self.active_streams.keys())
        
        for stream_id in target_streams:
            monitor = self.active_streams.get(stream_id)
            if monitor:
                monitor.resume_monitoring()
    
    def update_stream_status(self, stream_id: str, status: StreamStatus):
        """Update status for a stream and trigger callbacks"""
        self.stream_statuses[stream_id] = status
        
        # Update total violations count
        total_violations = sum(s.violations_detected for s in self.stream_statuses.values())
        self.total_violations_detected = total_violations
        
        # Trigger status callbacks
        for callback in self.status_callbacks:
            try:
                callback(stream_id, status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
        
        # Report to backend periodically
        if time.time() % 60 < 1:  # Once per minute
            self.backend_client.report_stream_status(stream_id, status)
    
    def add_status_callback(self, callback: Callable[[str, StreamStatus], None]):
        """Add callback for stream status updates"""
        self.status_callbacks.append(callback)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics"""
        stats = {
            "is_monitoring": self.is_monitoring,
            "active_streams": len(self.active_streams),
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "total_violations_detected": self.total_violations_detected,
            "queue_size": self.task_queue.qsize() if self.task_queue else 0,
            "streams": {}
        }
        
        # Per-stream statistics
        total_fps = 0
        total_frames = 0
        
        for stream_id, status in self.stream_statuses.items():
            stream_stats = {
                "is_active": status.is_active,
                "fps": status.fps,
                "frames_processed": status.frames_processed,
                "violations_detected": status.violations_detected,
                "error_count": status.error_count,
                "last_frame_time": status.last_frame_time.isoformat() if status.last_frame_time else None
            }
            stats["streams"][stream_id] = stream_stats
            
            total_fps += status.fps
            total_frames += status.frames_processed
        
        if self.active_streams:
            stats["average_fps"] = total_fps / len(self.active_streams)
            stats["total_frames_processed"] = total_frames
        
        return stats
    
    def get_active_streams(self) -> List[str]:
        """Get list of currently active stream IDs"""
        return [
            stream_id for stream_id, status in self.stream_statuses.items()
            if status.is_active
        ]
    
    def is_stream_active(self, stream_id: str) -> bool:
        """Check if a specific stream is active"""
        status = self.stream_statuses.get(stream_id)
        return status.is_active if status else False