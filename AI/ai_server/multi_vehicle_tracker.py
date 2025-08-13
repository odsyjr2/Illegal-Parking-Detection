"""
Multi-Vehicle Tracker Module for Illegal Parking Detection System

This module implements comprehensive vehicle detection and tracking across multiple CCTV streams
using the fine-tuned YOLOv11-seg model. It provides persistent vehicle tracking with unique IDs,
trajectory analysis, and state management for parking detection.

Key Features:
- YOLOv11-seg integration with fine-tuned vehicle detection model
- Multi-object tracking with persistent IDs across frames
- Vehicle state management (moving, stationary, parked)
- Cross-stream vehicle correlation and tracking
- Trajectory analysis and speed estimation
- Robust tracking through occlusions and temporary disappearances
- Integration with parking monitor for violation detection

Architecture:
- VehicleDetection: Individual vehicle detection result from YOLO
- VehicleTrack: Persistent vehicle track with history and state
- StreamTracker: Tracker for individual CCTV stream
- MultiVehicleTracker: Central coordinator for all streams
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import deque
import threading
import numpy as np
import cv2
from ultralytics import YOLO
from scipy.spatial.distance import euclidean
from scipy.optimize import linear_sum_assignment

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class VehicleDetection:
    """
    Single vehicle detection result from YOLO model.
    
    Contains all information about a detected vehicle in a single frame,
    including bounding box, confidence, class information, and optional
    segmentation mask from YOLOv11-seg.
    """
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int
    class_name: str
    center_point: Tuple[float, float]  # (cx, cy)
    area: float
    timestamp: float
    frame_id: int
    stream_id: str
    
    # Optional segmentation mask from YOLOv11-seg
    mask: Optional[np.ndarray] = None
    
    # Additional YOLO-specific information
    yolo_track_id: Optional[int] = None  # YOLO's internal tracking ID
    
    def __post_init__(self):
        """Calculate derived properties after initialization."""
        if not hasattr(self, 'center_point') or self.center_point is None:
            x1, y1, x2, y2 = self.bbox
            self.center_point = ((x1 + x2) / 2, (y1 + y2) / 2)
        
        if not hasattr(self, 'area') or self.area is None:
            x1, y1, x2, y2 = self.bbox
            self.area = (x2 - x1) * (y2 - y1)


@dataclass
class VehicleTrack:
    """
    Persistent vehicle track with complete history and state management.
    
    Maintains vehicle tracking information across multiple frames, including
    trajectory history, state transitions, and parking analysis data.
    """
    track_id: str  # Unique global tracking ID
    stream_id: str
    class_name: str
    
    # Current state
    current_detection: Optional[VehicleDetection] = None
    last_update_time: float = 0.0
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # Position and movement tracking
    position_history: deque = field(default_factory=lambda: deque(maxlen=50))
    velocity_history: deque = field(default_factory=lambda: deque(maxlen=10))
    current_velocity: Tuple[float, float] = (0.0, 0.0)
    
    # State management
    state: str = "detected"  # detected, tracking, stationary, parked, lost
    state_change_time: float = 0.0
    stationary_start_time: Optional[float] = None
    
    # Tracking quality metrics
    consecutive_detections: int = 0
    consecutive_misses: int = 0
    total_detections: int = 0
    tracking_quality: float = 1.0  # 0.0 to 1.0
    
    # Parking-related data
    is_candidate_for_parking: bool = False
    parking_zone_entry_time: Optional[float] = None
    last_significant_movement_time: Optional[float] = None
    
    # Visual tracking data
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    color: Tuple[int, int, int] = field(default_factory=lambda: (
        np.random.randint(0, 255),
        np.random.randint(0, 255), 
        np.random.randint(0, 255)
    ))
    
    def update(self, detection: VehicleDetection):
        """
        Update track with new detection data.
        
        Args:
            detection: New vehicle detection to incorporate into track
        """
        # Update basic information
        self.current_detection = detection
        self.last_update_time = detection.timestamp
        self.total_detections += 1
        self.consecutive_detections += 1
        self.consecutive_misses = 0
        
        # Update confidence history
        self.confidence_history.append(detection.confidence)
        
        # Update position and calculate velocity
        self._update_position_and_velocity(detection)
        
        # Update tracking quality
        self._update_tracking_quality()
        
        # Update vehicle state
        self._update_state(detection)
        
        # Update bounding box
        self.last_bbox = detection.bbox
    
    def _update_position_and_velocity(self, detection: VehicleDetection):
        """Update position history and calculate velocity."""
        current_pos = detection.center_point
        current_time = detection.timestamp
        
        # Add to position history
        self.position_history.append((current_pos, current_time))
        
        # Calculate velocity if we have previous position
        if len(self.position_history) >= 2:
            prev_pos, prev_time = self.position_history[-2]
            
            # Calculate time difference
            dt = current_time - prev_time
            
            if dt > 0:
                # Calculate velocity (pixels per second)
                dx = current_pos[0] - prev_pos[0]
                dy = current_pos[1] - prev_pos[1]
                vx = dx / dt
                vy = dy / dt
                
                self.current_velocity = (vx, vy)
                self.velocity_history.append((vx, vy, current_time))
    
    def _update_tracking_quality(self):
        """Update tracking quality score based on detection consistency."""
        # Base quality on consecutive detections vs misses
        recent_detections = self.consecutive_detections
        recent_misses = self.consecutive_misses
        
        # Calculate quality score
        if recent_detections + recent_misses > 0:
            quality = recent_detections / (recent_detections + recent_misses)
        else:
            quality = 1.0
        
        # Consider confidence history
        if self.confidence_history:
            avg_confidence = np.mean(self.confidence_history)
            quality = (quality + avg_confidence) / 2
        
        # Smooth the quality update
        alpha = 0.3  # Smoothing factor
        self.tracking_quality = alpha * quality + (1 - alpha) * self.tracking_quality
    
    def _update_state(self, detection: VehicleDetection):
        """Update vehicle state based on movement and time."""
        current_time = detection.timestamp
        
        # Calculate movement magnitude
        speed = np.sqrt(self.current_velocity[0]**2 + self.current_velocity[1]**2)
        
        # Define thresholds (configurable in production)
        stationary_threshold = 5.0  # pixels per second
        movement_threshold = 10.0   # pixels per second
        
        # State transition logic
        if speed < stationary_threshold:
            if self.state == "tracking" or self.state == "detected":
                # Vehicle has become stationary
                self.state = "stationary"
                self.state_change_time = current_time
                self.stationary_start_time = current_time
                logger.debug(f"Vehicle {self.track_id} became stationary")
            
            elif self.state == "stationary":
                # Check if stationary long enough to be considered parked
                stationary_duration = current_time - self.stationary_start_time
                if stationary_duration > 30.0:  # 30 seconds threshold
                    self.state = "parked"
                    self.state_change_time = current_time
                    self.is_candidate_for_parking = True
                    logger.info(f"Vehicle {self.track_id} is now parked (stationary for {stationary_duration:.1f}s)")
        
        else:
            # Vehicle is moving
            if self.state in ["stationary", "parked"]:
                # Vehicle started moving again
                self.state = "tracking"
                self.state_change_time = current_time
                self.stationary_start_time = None
                self.is_candidate_for_parking = False
                self.last_significant_movement_time = current_time
                logger.debug(f"Vehicle {self.track_id} started moving again")
            
            elif self.state == "detected":
                self.state = "tracking"
                self.state_change_time = current_time
    
    def mark_as_missed(self, current_time: float):
        """Mark track as missed in current frame."""
        self.consecutive_misses += 1
        self.consecutive_detections = 0
        
        # Update tracking quality
        self._update_tracking_quality()
        
        # Check if track should be marked as lost
        if self.consecutive_misses > 30:  # 30 frames without detection
            self.state = "lost"
            self.state_change_time = current_time
            logger.debug(f"Vehicle {self.track_id} marked as lost after {self.consecutive_misses} consecutive misses")
    
    def get_predicted_position(self, target_time: float) -> Tuple[float, float]:
        """
        Predict vehicle position at target time based on current velocity.
        
        Args:
            target_time: Time for which to predict position
            
        Returns:
            Tuple[float, float]: Predicted (x, y) position
        """
        if not self.current_detection:
            return (0.0, 0.0)
        
        # Time difference
        dt = target_time - self.last_update_time
        
        # Predict based on current velocity
        current_pos = self.current_detection.center_point
        predicted_x = current_pos[0] + self.current_velocity[0] * dt
        predicted_y = current_pos[1] + self.current_velocity[1] * dt
        
        return (predicted_x, predicted_y)
    
    def is_active(self, current_time: float, max_age: float = 30.0) -> bool:
        """
        Check if track is still active (not too old).
        
        Args:
            current_time: Current timestamp
            max_age: Maximum age in seconds before track is considered inactive
            
        Returns:
            bool: True if track is still active
        """
        age = current_time - self.last_update_time
        return age < max_age and self.state != "lost"
    
    def get_stationary_duration(self, current_time: float) -> float:
        """
        Get duration for which vehicle has been stationary.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            float: Duration in seconds, or 0 if not stationary
        """
        if self.state in ["stationary", "parked"] and self.stationary_start_time:
            return current_time - self.stationary_start_time
        return 0.0
    
    def get_track_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of track information."""
        return {
            "track_id": self.track_id,
            "stream_id": self.stream_id,
            "class_name": self.class_name,
            "state": self.state,
            "stationary_duration": self.get_stationary_duration(time.time()),
            "tracking_quality": self.tracking_quality,
            "total_detections": self.total_detections,
            "is_parking_candidate": self.is_candidate_for_parking,
            "current_position": self.current_detection.center_point if self.current_detection else None,
            "current_velocity": self.current_velocity,
            "last_update": self.last_update_time,
            "color": self.color
        }


class StreamTracker:
    """
    Vehicle tracker for individual CCTV stream.
    
    Handles YOLO model inference, detection processing, and track management
    for a single video stream. Integrates with the global multi-stream tracker
    for cross-stream vehicle correlation.
    """
    
    def __init__(self, stream_id: str, model_path: str, config: Dict[str, Any]):
        self.stream_id = stream_id
        self.config = config
        self.tracks: Dict[str, VehicleTrack] = {}
        self.next_track_id = 1
        self.frame_count = 0
        self.lock = threading.Lock()
        
        # Initialize YOLO model
        self.model = None
        self.model_path = model_path
        self._load_model()
        
        # Tracking parameters from config
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        self.iou_threshold = config.get('iou_threshold', 0.45)
        self.max_tracking_distance = config.get('max_tracking_distance', 100)
        
        logger.info(f"StreamTracker initialized for stream {stream_id}")
    
    def _load_model(self) -> bool:
        """
        Load the fine-tuned YOLOv11-seg model.
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            logger.info(f"Loading YOLO model from: {self.model_path}")
            
            # Load the fine-tuned YOLOv11-seg model
            self.model = YOLO(self.model_path)
            
            # Configure model parameters
            self.model.conf = self.confidence_threshold
            self.model.iou = self.iou_threshold
            
            # Test model with dummy input
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.model(dummy_frame, verbose=False)
            
            logger.info(f"YOLO model loaded successfully for stream {self.stream_id}")
            logger.info(f"Model classes: {self.model.names}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False
    
    def process_frame(self, frame: np.ndarray, timestamp: float) -> List[VehicleDetection]:
        """
        Process single frame through YOLO model and extract vehicle detections.
        
        Args:
            frame: Input frame from CCTV stream
            timestamp: Frame timestamp
            
        Returns:
            List[VehicleDetection]: List of detected vehicles in frame
        """
        if self.model is None:
            logger.error("YOLO model not loaded")
            return []
        
        try:
            self.frame_count += 1
            
            # Run YOLO inference
            results = self.model(frame, verbose=False)
            
            detections = []
            
            # Process YOLO results
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes
                    
                    for i, box in enumerate(boxes):
                        # Extract bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # Get class name
                        class_name = self.model.names.get(class_id, f"class_{class_id}")
                        
                        # Filter for vehicle classes (adjust based on your model's classes)
                        if self._is_vehicle_class(class_name):
                            # Extract segmentation mask if available
                            mask = None
                            if hasattr(result, 'masks') and result.masks is not None:
                                if i < len(result.masks.data):
                                    mask = result.masks.data[i].cpu().numpy()
                            
                            # Get YOLO tracking ID if available
                            yolo_track_id = None
                            if hasattr(box, 'id') and box.id is not None:
                                yolo_track_id = int(box.id[0].cpu().numpy())
                            
                            # Create detection object
                            detection = VehicleDetection(
                                bbox=(int(x1), int(y1), int(x2), int(y2)),
                                confidence=float(confidence),
                                class_id=class_id,
                                class_name=class_name,
                                center_point=((x1 + x2) / 2, (y1 + y2) / 2),
                                area=(x2 - x1) * (y2 - y1),
                                timestamp=timestamp,
                                frame_id=self.frame_count,
                                stream_id=self.stream_id,
                                mask=mask,
                                yolo_track_id=yolo_track_id
                            )
                            
                            detections.append(detection)
            
            logger.debug(f"Stream {self.stream_id}: Detected {len(detections)} vehicles in frame {self.frame_count}")
            return detections
            
        except Exception as e:
            logger.error(f"Error processing frame in stream {self.stream_id}: {e}")
            return []
    
    def _is_vehicle_class(self, class_name: str) -> bool:
        """
        Check if detected class is a vehicle type.
        
        Args:
            class_name: Class name from YOLO model
            
        Returns:
            bool: True if class represents a vehicle
        """
        # Define vehicle classes based on your fine-tuned model
        # Adjust these based on your specific model's class names
        vehicle_classes = [
            'car', 'truck', 'bus', 'motorcycle', 'bicycle',
            'vehicle', 'auto', 'sedan', 'suv', 'van',
            # Add Korean class names if your model uses them
            '자동차', '트럭', '버스', '오토바이', '자전거'
        ]
        
        return class_name.lower() in [vc.lower() for vc in vehicle_classes]
    
    def update_tracks(self, detections: List[VehicleDetection], timestamp: float):
        """
        Update vehicle tracks with new detections using Hungarian algorithm.
        
        Args:
            detections: List of vehicle detections from current frame
            timestamp: Current frame timestamp
        """
        with self.lock:
            active_tracks = {tid: track for tid, track in self.tracks.items() 
                           if track.is_active(timestamp)}
            
            if not detections:
                # No detections - mark all tracks as missed
                for track in active_tracks.values():
                    track.mark_as_missed(timestamp)
                return
            
            if not active_tracks:
                # No active tracks - create new tracks for all detections
                for detection in detections:
                    self._create_new_track(detection)
                return
            
            # Perform track-detection assignment using Hungarian algorithm
            assignments = self._assign_detections_to_tracks(
                list(active_tracks.values()), detections, timestamp
            )
            
            # Update assigned tracks
            assigned_detections = set()
            assigned_tracks = set()
            
            for track_idx, detection_idx in assignments:
                if track_idx < len(active_tracks) and detection_idx < len(detections):
                    track = list(active_tracks.values())[track_idx]
                    detection = detections[detection_idx]
                    
                    track.update(detection)
                    assigned_detections.add(detection_idx)
                    assigned_tracks.add(track.track_id)
            
            # Mark unassigned tracks as missed
            for track_id, track in active_tracks.items():
                if track_id not in assigned_tracks:
                    track.mark_as_missed(timestamp)
            
            # Create new tracks for unassigned detections
            for i, detection in enumerate(detections):
                if i not in assigned_detections:
                    self._create_new_track(detection)
            
            # Clean up old/lost tracks
            self._cleanup_old_tracks(timestamp)
    
    def _assign_detections_to_tracks(self, tracks: List[VehicleTrack], 
                                   detections: List[VehicleDetection], 
                                   timestamp: float) -> List[Tuple[int, int]]:
        """
        Assign detections to existing tracks using Hungarian algorithm.
        
        Args:
            tracks: List of active vehicle tracks
            detections: List of current frame detections
            timestamp: Current timestamp
            
        Returns:
            List[Tuple[int, int]]: List of (track_index, detection_index) assignments
        """
        if not tracks or not detections:
            return []
        
        # Create cost matrix based on distances
        cost_matrix = np.zeros((len(tracks), len(detections)))
        
        for i, track in enumerate(tracks):
            # Predict track position at current time
            predicted_pos = track.get_predicted_position(timestamp)
            
            for j, detection in enumerate(detections):
                # Calculate distance between predicted position and detection
                distance = euclidean(predicted_pos, detection.center_point)
                
                # Add penalty for class mismatch
                class_penalty = 0 if track.class_name == detection.class_name else 50
                
                # Add penalty for confidence difference
                conf_penalty = abs(track.confidence_history[-1] - detection.confidence) * 20 if track.confidence_history else 0
                
                total_cost = distance + class_penalty + conf_penalty
                
                # Set very high cost if distance is too large
                if distance > self.max_tracking_distance:
                    total_cost = 1e6
                
                cost_matrix[i, j] = total_cost
        
        # Solve assignment problem
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        
        # Filter out assignments with too high cost
        valid_assignments = []
        for row, col in zip(row_indices, col_indices):
            if cost_matrix[row, col] < self.max_tracking_distance * 2:
                valid_assignments.append((row, col))
        
        return valid_assignments
    
    def _create_new_track(self, detection: VehicleDetection):
        """Create new vehicle track from detection."""
        track_id = f"{self.stream_id}_{self.next_track_id:04d}"
        self.next_track_id += 1
        
        track = VehicleTrack(
            track_id=track_id,
            stream_id=self.stream_id,
            class_name=detection.class_name,
            current_detection=detection,
            last_update_time=detection.timestamp
        )
        
        track.update(detection)
        self.tracks[track_id] = track
        
        logger.debug(f"Created new track {track_id} for {detection.class_name}")
    
    def _cleanup_old_tracks(self, current_time: float):
        """Remove old and lost tracks."""
        max_age = 60.0  # Keep tracks for 60 seconds
        
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if not track.is_active(current_time, max_age):
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
            logger.debug(f"Removed old track {track_id}")
    
    def get_active_tracks(self, current_time: float) -> Dict[str, VehicleTrack]:
        """Get all active vehicle tracks."""
        with self.lock:
            return {tid: track for tid, track in self.tracks.items() 
                   if track.is_active(current_time)}
    
    def get_parking_candidates(self, current_time: float) -> List[VehicleTrack]:
        """Get vehicles that are candidates for parking violations."""
        with self.lock:
            candidates = []
            for track in self.tracks.values():
                if (track.is_candidate_for_parking and 
                    track.is_active(current_time) and
                    track.state in ["stationary", "parked"]):
                    candidates.append(track)
            return candidates
    
    def get_stream_stats(self) -> Dict[str, Any]:
        """Get stream tracking statistics."""
        with self.lock:
            current_time = time.time()
            active_tracks = self.get_active_tracks(current_time)
            parking_candidates = self.get_parking_candidates(current_time)
            
            return {
                "stream_id": self.stream_id,
                "total_tracks": len(self.tracks),
                "active_tracks": len(active_tracks),
                "parking_candidates": len(parking_candidates),
                "frames_processed": self.frame_count,
                "model_loaded": self.model is not None
            }


class MultiVehicleTracker:
    """
    Central coordinator for vehicle tracking across multiple CCTV streams.
    
    Manages individual stream trackers, provides cross-stream vehicle correlation,
    and coordinates with parking monitor for violation detection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stream_trackers: Dict[str, StreamTracker] = {}
        self.global_tracks: Dict[str, VehicleTrack] = {}
        self.lock = threading.Lock()
        
        # Load model configuration
        self.model_config = config.get('models', {}).get('vehicle_tracker', {})
        self.model_path = self.model_config.get('path', '')
        
        logger.info("MultiVehicleTracker initialized")
    
    def initialize_stream_tracker(self, stream_id: str) -> bool:
        """
        Initialize tracker for a specific stream.
        
        Args:
            stream_id: ID of the CCTV stream
            
        Returns:
            bool: True if initialization successful
        """
        try:
            with self.lock:
                if stream_id in self.stream_trackers:
                    logger.warning(f"Stream tracker already exists for {stream_id}")
                    return True
                
                # Create stream tracker with model configuration
                tracker = StreamTracker(stream_id, self.model_path, self.model_config)
                
                if tracker.model is not None:
                    self.stream_trackers[stream_id] = tracker
                    logger.info(f"Stream tracker initialized for {stream_id}")
                    return True
                else:
                    logger.error(f"Failed to load model for stream {stream_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to initialize stream tracker for {stream_id}: {e}")
            return False
    
    def process_stream_frame(self, stream_id: str, frame: np.ndarray, 
                           timestamp: float) -> List[VehicleTrack]:
        """
        Process frame from specific stream through vehicle tracking pipeline.
        
        Args:
            stream_id: ID of the CCTV stream
            frame: Input frame
            timestamp: Frame timestamp
            
        Returns:
            List[VehicleTrack]: Active vehicle tracks in the stream
        """
        if stream_id not in self.stream_trackers:
            logger.error(f"No tracker initialized for stream {stream_id}")
            return []
        
        try:
            tracker = self.stream_trackers[stream_id]
            
            # Detect vehicles in frame
            detections = tracker.process_frame(frame, timestamp)
            
            # Update tracks with detections
            tracker.update_tracks(detections, timestamp)
            
            # Get active tracks
            active_tracks = tracker.get_active_tracks(timestamp)
            
            # Update global tracking information
            self._update_global_tracks(stream_id, active_tracks)
            
            return list(active_tracks.values())
            
        except Exception as e:
            logger.error(f"Error processing frame for stream {stream_id}: {e}")
            return []
    
    def _update_global_tracks(self, stream_id: str, stream_tracks: Dict[str, VehicleTrack]):
        """Update global track registry with stream-specific tracks."""
        with self.lock:
            # Update global tracks with current stream tracks
            for track_id, track in stream_tracks.items():
                self.global_tracks[track_id] = track
            
            # TODO: Implement cross-stream vehicle correlation
            # This would involve:
            # 1. Matching vehicles across different camera views
            # 2. Maintaining global vehicle identities
            # 3. Handling vehicle handoffs between cameras
    
    def get_stream_tracker(self, stream_id: str) -> Optional[StreamTracker]:
        """Get tracker for specific stream."""
        return self.stream_trackers.get(stream_id)
    
    def get_all_parking_candidates(self) -> Dict[str, List[VehicleTrack]]:
        """Get parking candidates from all streams."""
        candidates = {}
        current_time = time.time()
        
        for stream_id, tracker in self.stream_trackers.items():
            stream_candidates = tracker.get_parking_candidates(current_time)
            if stream_candidates:
                candidates[stream_id] = stream_candidates
        
        return candidates
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get comprehensive tracking statistics for all streams."""
        stats = {
            "total_streams": len(self.stream_trackers),
            "streams": {}
        }
        
        total_active_tracks = 0
        total_parking_candidates = 0
        
        for stream_id, tracker in self.stream_trackers.items():
            stream_stats = tracker.get_stream_stats()
            stats["streams"][stream_id] = stream_stats
            
            total_active_tracks += stream_stats["active_tracks"]
            total_parking_candidates += stream_stats["parking_candidates"]
        
        stats["total_active_tracks"] = total_active_tracks
        stats["total_parking_candidates"] = total_parking_candidates
        
        return stats
    
    def cleanup_stream_tracker(self, stream_id: str):
        """Remove and cleanup tracker for specific stream."""
        with self.lock:
            if stream_id in self.stream_trackers:
                del self.stream_trackers[stream_id]
                
                # Remove global tracks from this stream
                tracks_to_remove = [tid for tid in self.global_tracks 
                                  if self.global_tracks[tid].stream_id == stream_id]
                for tid in tracks_to_remove:
                    del self.global_tracks[tid]
                
                logger.info(f"Cleaned up tracker for stream {stream_id}")


# Global instance - will be initialized by main application
multi_vehicle_tracker: Optional[MultiVehicleTracker] = None


def initialize_vehicle_tracker(config: Dict[str, Any]) -> bool:
    """
    Initialize the global multi-vehicle tracker instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global multi_vehicle_tracker
    
    try:
        multi_vehicle_tracker = MultiVehicleTracker(config)
        logger.info("Multi-vehicle tracker initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize multi-vehicle tracker: {e}")
        return False


def get_vehicle_tracker() -> Optional[MultiVehicleTracker]:
    """
    Get the global multi-vehicle tracker instance.
    
    Returns:
        Optional[MultiVehicleTracker]: Tracker instance or None if not initialized
    """
    return multi_vehicle_tracker