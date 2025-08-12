"""
Analysis Pipeline Module for Illegal Parking Detection System

This module orchestrates the complete multi-stream analysis pipeline, coordinating
all AI components including vehicle tracking, parking monitoring, license plate detection,
OCR recognition, and illegal parking classification across multiple CCTV streams.

Key Features:
- Multi-stream concurrent processing with thread management
- Complete AI pipeline orchestration from video input to violation detection
- Real-time analysis coordination across all components
- Event-driven architecture with callback systems
- Performance monitoring and resource management
- Integration with visualization and reporting systems

Architecture:
- StreamAnalyzer: Individual stream analysis pipeline
- AnalysisResult: Comprehensive analysis results structure
- AnalysisPipeline: Central coordinator for all streams
- EventHandler: Analysis event processing and callbacks
"""

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
import numpy as np
import cv2
from datetime import datetime

# Import all AI components
from cctv_manager import get_cctv_manager, CCTVManager
from multi_vehicle_tracker import get_vehicle_tracker, MultiVehicleTracker, VehicleTrack
from parking_monitor import get_parking_monitor, ParkingMonitorManager, ParkingEvent
from license_plate_detector import get_license_plate_detector, LicensePlateDetectionManager, PlateDetectionResult
from ocr_reader import get_ocr_reader, OCRManager, OCRResult
from illegal_classifier import get_violation_classifier, ViolationClassifier
# Note: visualization_manager.py was removed as part of FastAPI cleanup
# Visualization is now handled by the test framework in test/multi_stream_visualizer.py

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """
    Comprehensive analysis result for a single frame/timestamp.
    
    Contains all AI analysis outputs including tracking, parking monitoring,
    license plate detection, OCR, and violation classification results.
    """
    # Fields without default values
    stream_id: str
    frame_id: int
    timestamp: float
    original_frame: np.ndarray

    # Fields with default values
    processing_time: float = 0.0
    frame_shape: Tuple[int, int] = (0, 0)
    active_tracks: List[VehicleTrack] = field(default_factory=list)
    new_tracks: List[str] = field(default_factory=list)
    lost_tracks: List[str] = field(default_factory=list)
    parking_events: List[ParkingEvent] = field(default_factory=list)
    active_violations: List[ParkingEvent] = field(default_factory=list)
    new_violations: List[ParkingEvent] = field(default_factory=list)
    plate_detections: List[PlateDetectionResult] = field(default_factory=list)
    high_confidence_plates: List[PlateDetectionResult] = field(default_factory=list)
    ocr_results: List[OCRResult] = field(default_factory=list)
    recognized_plates: List[OCRResult] = field(default_factory=list)
    violation_classifications: List[Dict[str, Any]] = field(default_factory=list)
    component_timings: Dict[str, float] = field(default_factory=dict)
    fps: float = 0.0
    detection_quality: float = 0.0
    tracking_quality: float = 0.0
    overall_confidence: float = 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get concise summary of analysis results."""
        return {
            "stream_id": self.stream_id,
            "timestamp": self.timestamp,
            "processing_time": self.processing_time,
            "fps": self.fps,
            "vehicles": {
                "active_count": len(self.active_tracks),
                "new_count": len(self.new_tracks),
                "lost_count": len(self.lost_tracks),
                "parking_candidates": len([t for t in self.active_tracks if t.is_candidate_for_parking])
            },
            "parking": {
                "total_events": len(self.parking_events),
                "active_violations": len(self.active_violations),
                "new_violations": len(self.new_violations)
            },
            "plates": {
                "detected": len(self.plate_detections),
                "high_confidence": len(self.high_confidence_plates),
                "recognized": len(self.recognized_plates)
            },
            "quality": {
                "detection": self.detection_quality,
                "tracking": self.tracking_quality,
                "overall": self.overall_confidence
            }
        }


class StreamAnalyzer:
    """
    Individual CCTV stream analysis pipeline.
    
    Coordinates all AI components for processing a single video stream,
    from frame input through complete violation analysis and reporting.
    """
    
    def __init__(self, stream_id: str, config: Dict[str, Any]):
        self.stream_id = stream_id
        self.config = config
        self.is_running = False
        self.is_paused = False
        
        # Component references (will be set during initialization)
        self.cctv_manager: Optional[CCTVManager] = None
        self.vehicle_tracker: Optional[MultiVehicleTracker] = None
        self.parking_monitor: Optional[ParkingMonitorManager] = None
        self.plate_detector: Optional[LicensePlateDetectionManager] = None
        self.ocr_reader: Optional[OCRManager] = None
        self.violation_classifier: Optional[ViolationClassifier] = None
        # Visualization removed - handled by test framework
        # self.visualization_manager: Optional[VisualizationManager] = None
        
        # Processing state
        self.frame_count = 0
        self.last_analysis_result: Optional[AnalysisResult] = None
        self.processing_times = deque(maxlen=30)
        self.fps_history = deque(maxlen=30)
        
        # Threading
        self.analysis_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Analysis configuration
        self.analysis_interval = config.get('analysis_interval', 0.1)  # Process every 100ms
        self.plate_detection_interval = config.get('plate_detection_interval', 1.0)  # Detect plates every 1s
        self.classification_interval = config.get('classification_interval', 2.0)  # Classify every 2s
        
        # Timing control
        self.last_plate_detection_time = 0.0
        self.last_classification_time = 0.0
        
        logger.info(f"StreamAnalyzer created for {stream_id}")
    
    def initialize(self, cctv_manager: CCTVManager, vehicle_tracker: MultiVehicleTracker,
                  parking_monitor: ParkingMonitorManager, plate_detector: LicensePlateDetectionManager,
                  ocr_reader: OCRManager, violation_classifier: ViolationClassifier,
                  visualization_manager: Optional = None) -> bool:
        """
        Initialize stream analyzer with all required AI components.
        
        Args:
            cctv_manager: CCTV stream manager
            vehicle_tracker: Multi-vehicle tracker
            parking_monitor: Parking monitor manager
            plate_detector: License plate detector
            ocr_reader: OCR reader
            violation_classifier: Violation classifier
            visualization_manager: Optional visualization manager
            
        Returns:
            bool: True if initialization successful
        """
        try:
            self.cctv_manager = cctv_manager
            self.vehicle_tracker = vehicle_tracker
            self.parking_monitor = parking_monitor
            self.plate_detector = plate_detector
            self.ocr_reader = ocr_reader
            self.violation_classifier = violation_classifier
            # self.visualization_manager = visualization_manager  # Removed
            
            # Initialize stream-specific components
            success = True
            success &= self.vehicle_tracker.initialize_stream_tracker(self.stream_id)
            success &= self.parking_monitor.initialize_stream_monitor(self.stream_id)
            
            if success:
                logger.info(f"StreamAnalyzer initialized for {self.stream_id}")
            else:
                logger.error(f"Failed to initialize components for {self.stream_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing StreamAnalyzer for {self.stream_id}: {e}")
            return False
    
    def start_analysis(self) -> bool:
        """Start the analysis pipeline for this stream."""
        if self.is_running:
            logger.warning(f"Analysis already running for {self.stream_id}")
            return True
        
        try:
            self.is_running = True
            self.is_paused = False
            
            # Start analysis thread
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop, 
                name=f"Analysis-{self.stream_id}",
                daemon=True
            )
            self.analysis_thread.start()
            
            # Start visualization if enabled
            # Visualization removed - handled by test framework
            # if self.visualization_manager:
            #     self.visualization_manager.start_stream_visualization(self.stream_id)
            
            logger.info(f"Analysis started for stream {self.stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start analysis for {self.stream_id}: {e}")
            self.is_running = False
            return False
    
    def _analysis_loop(self):
        """Main analysis processing loop."""
        logger.info(f"Analysis loop started for {self.stream_id}")
        
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                # Get next frame from CCTV stream
                frame_data = self.cctv_manager.get_frame(self.stream_id)
                if frame_data is None:
                    time.sleep(0.01)  # Short delay if no frame available
                    continue
                
                frame, timestamp = frame_data
                
                # Process frame through analysis pipeline
                analysis_result = self._process_frame(frame, timestamp)
                
                if analysis_result:
                    # Update visualization
                    # Visualization removed - handled by test framework  
                    # if self.visualization_manager:
                    #     self.visualization_manager.update_stream_visualization(
                    #         self.stream_id, frame,
                    #         analysis_result.active_tracks,
                    #         analysis_result.parking_events,
                    #         analysis_result.plate_detections,
                    #         analysis_result.ocr_results
                    #     )
                    
                    # Store latest result
                    with self.lock:
                        self.last_analysis_result = analysis_result
                
                # Control processing rate
                time.sleep(self.analysis_interval)
                
            except Exception as e:
                logger.error(f"Error in analysis loop for {self.stream_id}: {e}")
                time.sleep(1.0)  # Longer delay on error
        
        logger.info(f"Analysis loop ended for {self.stream_id}")
    
    def _process_frame(self, frame: np.ndarray, timestamp: float) -> Optional[AnalysisResult]:
        """
        Process single frame through complete analysis pipeline.
        
        Args:
            frame: Input video frame
            timestamp: Frame timestamp
            
        Returns:
            AnalysisResult: Complete analysis results
        """
        start_time = time.time()
        self.frame_count += 1
        
        try:
            # Initialize analysis result
            result = AnalysisResult(
                stream_id=self.stream_id,
                frame_id=self.frame_count,
                timestamp=timestamp,
                original_frame=frame,
                frame_shape=(frame.shape[1], frame.shape[0])
            )
            
            # Step 1: Vehicle Detection and Tracking
            component_start = time.time()
            if self.vehicle_tracker:
                tracks = self.vehicle_tracker.process_stream_frame(self.stream_id, frame, timestamp)
                result.active_tracks = tracks
            result.component_timings['tracking'] = time.time() - component_start
            
            # Step 2: Parking Monitoring
            component_start = time.time()
            if self.parking_monitor and result.active_tracks:
                completed_events = self.parking_monitor.update_stream_monitoring(
                    self.stream_id, result.active_tracks, timestamp
                )
                
                # Get current parking events and violations
                all_violations = self.parking_monitor.get_all_active_violations()
                stream_violations = all_violations.get(self.stream_id, [])
                
                result.parking_events = completed_events
                result.active_violations = stream_violations
            result.component_timings['parking'] = time.time() - component_start
            
            # NOTE: Steps 3, 4, and 5 are disabled for Stage 1 implementation.
            # They will be enabled in subsequent stages.

            # # Step 3: License Plate Detection (periodic)
            # current_time = time.time()
            # if (current_time - self.last_plate_detection_time) >= self.plate_detection_interval:
            #     component_start = time.time()
            #     result.plate_detections = self._detect_license_plates(frame, tracks)
            #     result.component_timings['plate_detection'] = time.time() - component_start
            #     self.last_plate_detection_time = current_time
            
            # # Step 4: OCR Recognition (if plates detected)
            # if result.plate_detections:
            #     component_start = time.time()
            #     result.ocr_results = self._perform_ocr_recognition(result.plate_detections)
            #     result.component_timings['ocr'] = time.time() - component_start
            
            # # Step 5: Illegal Parking Classification (periodic)
            # if (current_time - self.last_classification_time) >= self.classification_interval:
            #     component_start = time.time()
            #     result.violation_classifications = self._classify_violations(
            #         frame, result.active_violations
            #     )
            #     result.component_timings['classification'] = time.time() - component_start
            #     self.last_classification_time = current_time
            
            # Calculate performance metrics
            result.processing_time = time.time() - start_time
            self.processing_times.append(result.processing_time)
            
            # Calculate FPS
            if len(self.processing_times) > 1:
                avg_processing_time = np.mean(self.processing_times)
                result.fps = 1.0 / max(avg_processing_time, 0.001)
                self.fps_history.append(result.fps)
            
            # Calculate quality metrics
            result.detection_quality = self._calculate_detection_quality(result)
            result.tracking_quality = self._calculate_tracking_quality(result)
            result.overall_confidence = (result.detection_quality + result.tracking_quality) / 2
            
            # Filter results for high-confidence items
            result.high_confidence_plates = [
                p for p in result.plate_detections if p.confidence > 0.8
            ]
            result.recognized_plates = [
                r for r in result.ocr_results if r.is_valid_format and r.confidence_score > 0.7
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing frame for {self.stream_id}: {e}")
            return None
    
    def _detect_license_plates(self, frame: np.ndarray, tracks: List[VehicleTrack]) -> List[PlateDetectionResult]:
        """Detect license plates for parking candidate vehicles."""
        if not self.plate_detector or not tracks:
            return []
        
        plate_results = []
        
        # Focus on parking candidates and stationary vehicles
        parking_candidates = [t for t in tracks if t.is_candidate_for_parking or t.state in ["stationary", "parked"]]
        
        for track in parking_candidates:
            if track.current_detection:
                # Detect plates within vehicle bounding box
                vehicle_bbox = track.current_detection.bbox
                track_plates = self.plate_detector.detect_vehicle_plates(frame, vehicle_bbox)
                
                # Associate plates with track
                for plate in track_plates:
                    plate.stream_id = self.stream_id
                    plate.associated_track_id = track.track_id
                
                plate_results.extend(track_plates)
        
        return plate_results
    
    def _perform_ocr_recognition(self, plate_detections: List[PlateDetectionResult]) -> List[OCRResult]:
        """Perform OCR recognition on detected license plates."""
        if not self.ocr_reader or not plate_detections:
            return []
        
        try:
            return self.ocr_reader.batch_process_plates(plate_detections)
        except Exception as e:
            logger.error(f"Error in OCR recognition: {e}")
            return []
    
    def _classify_violations(self, frame: np.ndarray, violations: List[ParkingEvent]) -> List[Dict[str, Any]]:
        """Classify parking violations using illegal parking classifier."""
        if not self.violation_classifier or not violations:
            return []
        
        classification_results = []
        
        for violation in violations:
            try:
                # Extract region around violation location
                x, y = int(violation.location[0]), int(violation.location[1])
                margin = 100  # pixels
                
                h, w = frame.shape[:2]
                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(w, x + margin)
                y2 = min(h, y + margin)
                
                violation_region = frame[y1:y2, x1:x2]
                
                # Classify violation
                classification = self.violation_classifier.classify_violation(
                    violation_region, violation
                )
                
                classification_results.append({
                    "event_id": violation.event_id,
                    "classification": classification,
                    "region_bbox": (x1, y1, x2, y2)
                })
                
            except Exception as e:
                logger.error(f"Error classifying violation {violation.event_id}: {e}")
        
        return classification_results
    
    def _calculate_detection_quality(self, result: AnalysisResult) -> float:
        """Calculate overall detection quality score."""
        if not result.active_tracks:
            return 0.0
        
        # Base on average tracking confidence
        confidences = [
            track.current_detection.confidence 
            for track in result.active_tracks 
            if track.current_detection
        ]
        
        if not confidences:
            return 0.0
        
        avg_confidence = np.mean(confidences)
        
        # Bonus for successful plate detections
        plate_bonus = min(len(result.plate_detections) * 0.1, 0.3)
        
        return min(avg_confidence + plate_bonus, 1.0)
    
    def _calculate_tracking_quality(self, result: AnalysisResult) -> float:
        """Calculate tracking quality score."""
        if not result.active_tracks:
            return 0.0
        
        # Base on average track quality
        track_qualities = [track.tracking_quality for track in result.active_tracks]
        avg_quality = np.mean(track_qualities)
        
        # Consider track stability (fewer new/lost tracks is better)
        stability_penalty = (len(result.new_tracks) + len(result.lost_tracks)) * 0.05
        
        return max(0.0, min(avg_quality - stability_penalty, 1.0))
    
    def pause_analysis(self):
        """Pause analysis processing."""
        self.is_paused = True
        logger.info(f"Analysis paused for {self.stream_id}")
    
    def resume_analysis(self):
        """Resume analysis processing."""
        self.is_paused = False
        logger.info(f"Analysis resumed for {self.stream_id}")
    
    def stop_analysis(self):
        """Stop analysis processing."""
        self.is_running = False
        
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5.0)
        
        # Stop visualization
        # Visualization removed - handled by test framework
        # if self.visualization_manager:
        #     self.visualization_manager.stop_stream_visualization(self.stream_id)
        
        logger.info(f"Analysis stopped for {self.stream_id}")
    
    def get_latest_result(self) -> Optional[AnalysisResult]:
        """Get the latest analysis result."""
        with self.lock:
            return self.last_analysis_result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this analyzer."""
        with self.lock:
            return {
                "stream_id": self.stream_id,
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "frames_processed": self.frame_count,
                "avg_processing_time": np.mean(self.processing_times) if self.processing_times else 0.0,
                "avg_fps": np.mean(self.fps_history) if self.fps_history else 0.0,
                "latest_result_time": self.last_analysis_result.timestamp if self.last_analysis_result else None
            }


class AnalysisPipeline:
    """
    Central coordinator for multi-stream illegal parking analysis.
    
    Manages analysis across all CCTV streams, coordinates AI components,
    and provides unified interface for system-wide analysis control.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stream_analyzers: Dict[str, StreamAnalyzer] = {}
        self.is_system_running = False
        
        # AI Component references
        self.cctv_manager: Optional[CCTVManager] = None
        self.vehicle_tracker: Optional[MultiVehicleTracker] = None
        self.parking_monitor: Optional[ParkingMonitorManager] = None
        self.plate_detector: Optional[LicensePlateDetectionManager] = None
        self.ocr_reader: Optional[OCRManager] = None
        self.violation_classifier: Optional[ViolationClassifier] = None
        # Visualization removed - handled by test framework
        # self.visualization_manager: Optional[VisualizationManager] = None
        
        # Event handling
        self.event_callbacks: Dict[str, List[Callable]] = {
            'new_violation': [],
            'new_track': [],
            'plate_detected': [],
            'plate_recognized': []
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="AnalysisPipeline")
        self.lock = threading.Lock()
        
        # System statistics
        self.system_start_time: Optional[float] = None
        self.total_frames_processed = 0
        self.total_violations_detected = 0
        
        logger.info("AnalysisPipeline initialized")
    
    def initialize_components(self) -> bool:
        """Initialize all AI components and check their readiness."""
        try:
            # Get global component instances
            self.cctv_manager = get_cctv_manager()
            self.vehicle_tracker = get_vehicle_tracker()
            self.parking_monitor = get_parking_monitor()
            self.plate_detector = get_license_plate_detector()
            self.ocr_reader = get_ocr_reader()
            self.violation_classifier = get_violation_classifier()
            # self.visualization_manager = get_visualization_manager()  # Removed
            
            # Check component readiness
            components_ready = []
            components_ready.append(("CCTV Manager", self.cctv_manager is not None))
            components_ready.append(("Vehicle Tracker", self.vehicle_tracker is not None))
            components_ready.append(("Parking Monitor", self.parking_monitor is not None))
            components_ready.append(("Plate Detector", self.plate_detector and self.plate_detector.is_ready()))
            components_ready.append(("OCR Reader", self.ocr_reader and self.ocr_reader.is_ready()))
            components_ready.append(("Violation Classifier", self.violation_classifier and self.violation_classifier.is_ready()))
            components_ready.append(("Visualization Manager", True))  # Optional component
            
            # Log component status
            all_ready = True
            for name, ready in components_ready:
                status = "✓ Ready" if ready else "✗ Not Ready"
                logger.info(f"{name}: {status}")
                if not ready and name != "Visualization Manager":  # Visualization is optional
                    all_ready = False
            
            if all_ready:
                logger.info("All required AI components initialized successfully")
            else:
                logger.error("Some required AI components failed to initialize")
            
            return all_ready
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            return False
    
    def start_analysis(self, stream_ids: Optional[List[str]] = None) -> bool:
        """
        Start analysis pipeline for specified streams.
        
        Args:
            stream_ids: List of stream IDs to analyze, or None for all configured streams
            
        Returns:
            bool: True if analysis started successfully
        """
        if self.is_system_running:
            logger.warning("Analysis system is already running")
            return True
        
        try:
            # Get stream IDs from CCTV manager if not specified
            if stream_ids is None:
                if not self.cctv_manager:
                    logger.error("CCTV manager not available")
                    return False
                stream_ids = list(self.cctv_manager.get_active_streams().keys())
            
            if not stream_ids:
                logger.error("No streams available for analysis")
                return False
            
            # Create and initialize stream analyzers
            initialization_success = True
            
            for stream_id in stream_ids:
                try:
                    # Create stream analyzer
                    analyzer = StreamAnalyzer(stream_id, self.config)
                    
                    # Initialize with AI components
                    if analyzer.initialize(
                        self.cctv_manager, self.vehicle_tracker, self.parking_monitor,
                        self.plate_detector, self.ocr_reader, self.violation_classifier,
                        None  # self.visualization_manager removed
                    ):
                        self.stream_analyzers[stream_id] = analyzer
                        logger.info(f"Stream analyzer created for {stream_id}")
                    else:
                        logger.error(f"Failed to initialize analyzer for {stream_id}")
                        initialization_success = False
                        
                except Exception as e:
                    logger.error(f"Error creating analyzer for {stream_id}: {e}")
                    initialization_success = False
            
            if not initialization_success:
                logger.error("Failed to initialize some stream analyzers")
                return False
            
            # Start all stream analyzers
            start_success = True
            for stream_id, analyzer in self.stream_analyzers.items():
                if not analyzer.start_analysis():
                    logger.error(f"Failed to start analysis for {stream_id}")
                    start_success = False
            
            if start_success:
                self.is_system_running = True
                self.system_start_time = time.time()
                logger.info(f"Analysis pipeline started for {len(self.stream_analyzers)} streams")
            else:
                logger.error("Failed to start some stream analyzers")
                self.stop_analysis()  # Cleanup partial start
            
            return start_success
            
        except Exception as e:
            logger.error(f"Error starting analysis pipeline: {e}")
            return False
    
    def stop_analysis(self):
        """Stop analysis pipeline for all streams."""
        if not self.is_system_running:
            return
        
        logger.info("Stopping analysis pipeline...")
        
        # Stop all stream analyzers
        for stream_id, analyzer in list(self.stream_analyzers.items()):
            try:
                analyzer.stop_analysis()
            except Exception as e:
                logger.error(f"Error stopping analyzer for {stream_id}: {e}")
        
        # Clear analyzers
        self.stream_analyzers.clear()
        
        # Stop visualization
        # Visualization removed - handled by test framework
        # if self.visualization_manager:
        #     self.visualization_manager.stop_all_visualizations()
        
        self.is_system_running = False
        logger.info("Analysis pipeline stopped")
    
    def pause_analysis(self, stream_ids: Optional[List[str]] = None):
        """Pause analysis for specified streams or all streams."""
        target_streams = stream_ids or list(self.stream_analyzers.keys())
        
        for stream_id in target_streams:
            analyzer = self.stream_analyzers.get(stream_id)
            if analyzer:
                analyzer.pause_analysis()
    
    def resume_analysis(self, stream_ids: Optional[List[str]] = None):
        """Resume analysis for specified streams or all streams."""
        target_streams = stream_ids or list(self.stream_analyzers.keys())
        
        for stream_id in target_streams:
            analyzer = self.stream_analyzers.get(stream_id)
            if analyzer:
                analyzer.resume_analysis()
    
    def get_latest_results(self, stream_ids: Optional[List[str]] = None) -> Dict[str, AnalysisResult]:
        """Get latest analysis results for specified streams."""
        target_streams = stream_ids or list(self.stream_analyzers.keys())
        results = {}
        
        for stream_id in target_streams:
            analyzer = self.stream_analyzers.get(stream_id)
            if analyzer:
                result = analyzer.get_latest_result()
                if result:
                    results[stream_id] = result
        
        return results
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        with self.lock:
            stats = {
                "system_running": self.is_system_running,
                "active_streams": len(self.stream_analyzers),
                "uptime": time.time() - self.system_start_time if self.system_start_time else 0,
                "total_frames_processed": self.total_frames_processed,
                "total_violations_detected": self.total_violations_detected,
                "streams": {}
            }
            
            # Get per-stream statistics
            total_fps = 0
            total_processing_time = 0
            
            for stream_id, analyzer in self.stream_analyzers.items():
                stream_stats = analyzer.get_performance_stats()
                stats["streams"][stream_id] = stream_stats
                
                total_fps += stream_stats.get("avg_fps", 0)
                total_processing_time += stream_stats.get("avg_processing_time", 0)
            
            if self.stream_analyzers:
                stats["avg_system_fps"] = total_fps / len(self.stream_analyzers)
                stats["avg_processing_time"] = total_processing_time / len(self.stream_analyzers)
            
            return stats
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """Add callback for specific analysis events."""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: str, callback: Callable):
        """Remove callback for specific analysis events."""
        if event_type in self.event_callbacks and callback in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].remove(callback)
    
    def get_active_violations(self) -> Dict[str, List[ParkingEvent]]:
        """Get all currently active parking violations across all streams."""
        all_violations = {}
        
        for stream_id, analyzer in self.stream_analyzers.items():
            latest_result = analyzer.get_latest_result()
            if latest_result and latest_result.active_violations:
                all_violations[stream_id] = latest_result.active_violations
        
        return all_violations
    
    def cleanup(self):
        """Cleanup analysis pipeline and all resources."""
        logger.info("Cleaning up AnalysisPipeline")
        
        # Stop analysis
        self.stop_analysis()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clear callbacks
        self.event_callbacks.clear()


# Global instance - will be initialized by main application
analysis_pipeline: Optional[AnalysisPipeline] = None


def initialize_analysis_pipeline(config: Dict[str, Any]) -> bool:
    """
    Initialize the global analysis pipeline instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global analysis_pipeline
    
    try:
        analysis_pipeline = AnalysisPipeline(config)
        
        # Initialize AI components
        success = analysis_pipeline.initialize_components()
        
        if success:
            logger.info("Analysis pipeline initialized successfully")
        else:
            logger.error("Analysis pipeline initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize analysis pipeline: {e}")
        return False


def get_analysis_pipeline() -> Optional[AnalysisPipeline]:
    """
    Get the global analysis pipeline instance.
    
    Returns:
        Optional[AnalysisPipeline]: Pipeline instance or None if not initialized
    """
    return analysis_pipeline