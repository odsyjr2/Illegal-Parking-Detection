"""
Parking Monitor Module for Illegal Parking Detection System

This module monitors vehicle parking duration and identifies potential violations
by analyzing vehicle tracks from the multi-vehicle tracker. It implements the
parking violation detection logic based on configurable time thresholds and
location-based rules.

Key Features:
- Real-time parking duration monitoring per vehicle track
- Configurable violation thresholds (stationary time, parking zones)
- Integration with vehicle tracker for state-based monitoring
- Historical parking event tracking and analysis
- Zone-based parking rules and restrictions
- Automatic violation candidate identification

Architecture:
- ParkingEvent: Individual parking event with timing and location data
- VehicleMonitor: Per-vehicle parking state and duration tracking
- StreamParkingMonitor: Parking monitor for individual CCTV stream
- ParkingMonitorManager: Central coordinator for all streams
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import deque
from enum import Enum
import threading
from datetime import datetime, timezone
import json

from multi_vehicle_tracker import VehicleTrack, MultiVehicleTracker

# Configure logging
logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """Types of parking violations that can be detected."""
    DURATION_EXCEEDED = "duration_exceeded"
    NO_PARKING_ZONE = "no_parking_zone"
    RESTRICTED_HOURS = "restricted_hours"
    BLOCKING_TRAFFIC = "blocking_traffic"
    CROSSWALK_PARKING = "crosswalk_parking"


@dataclass
class ParkingZone:
    """
    Definition of a parking zone with associated rules and restrictions.
    
    Defines geographic and temporal constraints for legal parking,
    including time-based restrictions and duration limits.
    """
    zone_id: str
    name: str
    zone_type: str  # "legal", "restricted", "no_parking"
    
    # Geographic boundaries (can be expanded to support polygons)
    center_point: Tuple[float, float]  # (latitude, longitude) or (x, y) in pixels
    radius: float  # Radius in meters or pixels
    
    # Time-based restrictions
    restricted_hours: Optional[List[Tuple[str, str]]] = None  # [("09:00", "17:00")]
    restricted_days: Optional[List[str]] = None  # ["monday", "tuesday"]
    
    # Duration limits
    max_parking_duration: Optional[float] = None  # Maximum parking time in seconds
    grace_period: float = 60.0  # Grace period before violation in seconds
    
    # Additional metadata
    description: str = ""
    enforcement_active: bool = True


@dataclass
class ParkingEvent:
    """
    Individual parking event with complete violation analysis data.
    
    Represents a single parking event from start to end, including
    violation analysis, timing information, and associated vehicle data.
    """
    event_id: str
    track_id: str
    stream_id: str
    vehicle_class: str
    
    # Timing information
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    
    # Location information  
    location: Tuple[float, float] = (0.0, 0.0)  # Center point of parking area
    parking_zone_id: Optional[str] = None
    
    # Violation analysis
    is_violation: bool = False
    violation_types: List[ViolationType] = field(default_factory=list)
    violation_severity: float = 0.0  # 0.0 to 1.0
    
    # Detection confidence and quality metrics
    confidence_score: float = 0.0
    tracking_quality: float = 0.0
    
    # Evidence data for reporting
    violation_start_time: Optional[float] = None
    evidence_images: List[str] = field(default_factory=list)  # Image file paths
    
    # Additional metadata
    weather_conditions: Optional[str] = None
    traffic_context: Optional[Dict[str, Any]] = None
    
    def get_violation_duration(self, current_time: Optional[float] = None) -> float:
        """
        Calculate duration of violation (time beyond legal parking limit).
        
        Args:
            current_time: Current timestamp, defaults to now
            
        Returns:
            float: Violation duration in seconds, 0 if no violation
        """
        if not self.is_violation or not self.violation_start_time:
            return 0.0
        
        end_time = current_time or self.end_time or time.time()
        return max(0.0, end_time - self.violation_start_time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parking event to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "track_id": self.track_id,
            "stream_id": self.stream_id,
            "vehicle_class": self.vehicle_class,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "location": self.location,
            "parking_zone_id": self.parking_zone_id,
            "is_violation": self.is_violation,
            "violation_types": [vt.value for vt in self.violation_types],
            "violation_severity": self.violation_severity,
            "violation_duration": self.get_violation_duration(),
            "confidence_score": self.confidence_score,
            "tracking_quality": self.tracking_quality,
            "evidence_images": self.evidence_images,
            "timestamp_iso": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat()
        }


class VehicleMonitor:
    """
    Per-vehicle parking state and duration monitoring.
    
    Tracks individual vehicle parking behavior, analyzes parking patterns,
    and determines violation status based on configured rules.
    """
    
    def __init__(self, track_id: str, stream_id: str, config: Dict[str, Any]):
        self.track_id = track_id
        self.stream_id = stream_id
        self.config = config
        
        # Current parking event
        self.current_event: Optional[ParkingEvent] = None
        self.is_currently_parked = False
        
        # Historical events
        self.parking_history: deque = deque(maxlen=50)
        
        # Monitoring parameters from config
        self.violation_threshold = config.get('violation_threshold', 300.0)  # 5 minutes
        self.stationary_threshold = config.get('stationary_threshold', 5.0)  # 5 seconds
        self.position_tolerance = config.get('position_tolerance', 20)  # 20 pixels
        
        # State tracking
        self.last_position: Optional[Tuple[float, float]] = None
        self.position_stable_since: Optional[float] = None
        self.violation_reported = False
        
        logger.debug(f"VehicleMonitor created for track {track_id}")
    
    def update_with_track(self, track: VehicleTrack, current_time: float, 
                         parking_zones: List[ParkingZone]) -> Optional[ParkingEvent]:
        """
        Update vehicle monitor with latest track information.
        
        Args:
            track: Current vehicle track data
            current_time: Current timestamp
            parking_zones: List of defined parking zones
            
        Returns:
            Optional[ParkingEvent]: Completed parking event if vehicle stopped parking
        """
        completed_event = None
        
        # Check if vehicle state indicates parking behavior
        if track.state in ["stationary", "parked"]:
            if not self.is_currently_parked:
                # Vehicle just started parking
                self._start_parking_event(track, current_time, parking_zones)
            else:
                # Update existing parking event
                self._update_current_event(track, current_time, parking_zones)
        
        else:
            # Vehicle is not parked
            if self.is_currently_parked:
                # Vehicle stopped parking - finalize event
                completed_event = self._end_parking_event(track, current_time)
        
        return completed_event
    
    def _start_parking_event(self, track: VehicleTrack, current_time: float, 
                           parking_zones: List[ParkingZone]):
        """Start new parking event when vehicle becomes stationary."""
        event_id = f"{self.track_id}_{int(current_time)}"
        
        # Determine location and parking zone
        location = track.current_detection.center_point if track.current_detection else (0.0, 0.0)
        parking_zone = self._find_parking_zone(location, parking_zones)
        
        self.current_event = ParkingEvent(
            event_id=event_id,
            track_id=self.track_id,
            stream_id=self.stream_id,
            vehicle_class=track.class_name,
            start_time=current_time,
            location=location,
            parking_zone_id=parking_zone.zone_id if parking_zone else None,
            confidence_score=track.confidence_history[-1] if track.confidence_history else 0.0,
            tracking_quality=track.tracking_quality
        )
        
        self.is_currently_parked = True
        self.violation_reported = False
        
        logger.info(f"Started parking event {event_id} for track {self.track_id}")
    
    def _update_current_event(self, track: VehicleTrack, current_time: float, 
                            parking_zones: List[ParkingZone]):
        """Update current parking event with latest information."""
        if not self.current_event:
            return
        
        # Update duration
        self.current_event.duration = current_time - self.current_event.start_time
        
        # Update location (use average position for stability)
        if track.current_detection:
            current_pos = track.current_detection.center_point
            if self.current_event.location == (0.0, 0.0):
                self.current_event.location = current_pos
            else:
                # Smooth location update
                alpha = 0.1
                old_x, old_y = self.current_event.location
                new_x, new_y = current_pos
                self.current_event.location = (
                    alpha * new_x + (1 - alpha) * old_x,
                    alpha * new_y + (1 - alpha) * old_y
                )
        
        # Check for violation conditions
        self._check_violation_conditions(track, current_time, parking_zones)
        
        # Update quality metrics
        if track.confidence_history:
            self.current_event.confidence_score = np.mean(track.confidence_history)
        self.current_event.tracking_quality = track.tracking_quality
    
    def _end_parking_event(self, track: VehicleTrack, current_time: float) -> ParkingEvent:
        """End current parking event and add to history."""
        if not self.current_event:
            return None
        
        # Finalize event data
        self.current_event.end_time = current_time
        self.current_event.duration = current_time - self.current_event.start_time
        
        # Add to history
        self.parking_history.append(self.current_event)
        
        logger.info(f"Ended parking event {self.current_event.event_id}, duration: {self.current_event.duration:.1f}s")
        
        # Return completed event and reset current state
        completed_event = self.current_event
        self.current_event = None
        self.is_currently_parked = False
        self.violation_reported = False
        
        return completed_event
    
    def _check_violation_conditions(self, track: VehicleTrack, current_time: float, 
                                  parking_zones: List[ParkingZone]):
        """Check if current parking situation constitutes a violation."""
        if not self.current_event:
            return
        
        parking_duration = self.current_event.duration
        violation_types = []
        
        # Check duration-based violation
        if parking_duration > self.violation_threshold:
            violation_types.append(ViolationType.DURATION_EXCEEDED)
            
            # Set violation start time if not already set
            if not self.current_event.violation_start_time:
                self.current_event.violation_start_time = (
                    self.current_event.start_time + self.violation_threshold
                )
        
        # Check zone-based violations
        if self.current_event.parking_zone_id:
            parking_zone = self._find_zone_by_id(self.current_event.parking_zone_id, parking_zones)
            if parking_zone:
                zone_violations = self._check_zone_violations(parking_zone, current_time)
                violation_types.extend(zone_violations)
        
        # Update violation status
        if violation_types:
            self.current_event.is_violation = True
            self.current_event.violation_types = violation_types
            
            # Calculate severity based on violation types and duration
            severity = self._calculate_violation_severity(parking_duration, violation_types)
            self.current_event.violation_severity = severity
            
            # Report new violation
            if not self.violation_reported:
                logger.warning(f"VIOLATION DETECTED: Track {self.track_id}, "
                             f"Duration: {parking_duration:.1f}s, "
                             f"Types: {[vt.value for vt in violation_types]}")
                self.violation_reported = True
    
    def _find_parking_zone(self, location: Tuple[float, float], 
                          zones: List[ParkingZone]) -> Optional[ParkingZone]:
        """Find parking zone containing the given location."""
        # Simple distance-based zone detection
        # In production, this could be replaced with proper geometric containment
        
        for zone in zones:
            distance = np.sqrt(
                (location[0] - zone.center_point[0])**2 + 
                (location[1] - zone.center_point[1])**2
            )
            
            if distance <= zone.radius:
                return zone
        
        return None
    
    def _find_zone_by_id(self, zone_id: str, zones: List[ParkingZone]) -> Optional[ParkingZone]:
        """Find parking zone by ID."""
        for zone in zones:
            if zone.zone_id == zone_id:
                return zone
        return None
    
    def _check_zone_violations(self, zone: ParkingZone, current_time: float) -> List[ViolationType]:
        """Check for zone-specific parking violations."""
        violations = []
        
        # Check if parking is allowed in this zone type
        if zone.zone_type == "no_parking":
            violations.append(ViolationType.NO_PARKING_ZONE)
        
        # Check time-based restrictions
        if zone.restricted_hours:
            current_hour = datetime.fromtimestamp(current_time).hour
            for start_time, end_time in zone.restricted_hours:
                start_hour = int(start_time.split(':')[0])
                end_hour = int(end_time.split(':')[0])
                
                if start_hour <= current_hour < end_hour:
                    violations.append(ViolationType.RESTRICTED_HOURS)
                    break
        
        # Check duration limits
        if zone.max_parking_duration and self.current_event:
            if self.current_event.duration > zone.max_parking_duration:
                violations.append(ViolationType.DURATION_EXCEEDED)
        
        return violations
    
    def _calculate_violation_severity(self, duration: float, 
                                    violation_types: List[ViolationType]) -> float:
        """Calculate violation severity score (0.0 to 1.0)."""
        base_severity = 0.0
        
        # Base severity on duration excess
        if duration > self.violation_threshold:
            excess_ratio = (duration - self.violation_threshold) / self.violation_threshold
            base_severity = min(0.5 + excess_ratio * 0.3, 0.8)  # Cap at 0.8 for duration
        
        # Add severity for violation types
        type_severity = {
            ViolationType.DURATION_EXCEEDED: 0.3,
            ViolationType.NO_PARKING_ZONE: 0.8,
            ViolationType.RESTRICTED_HOURS: 0.6,
            ViolationType.BLOCKING_TRAFFIC: 0.9,
            ViolationType.CROSSWALK_PARKING: 0.95
        }
        
        max_type_severity = max([type_severity.get(vt, 0.3) for vt in violation_types])
        
        # Combine base and type severity
        combined_severity = min(base_severity + max_type_severity, 1.0)
        
        return combined_severity
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status for the vehicle."""
        status = {
            "track_id": self.track_id,
            "stream_id": self.stream_id,
            "is_parked": self.is_currently_parked,
            "violation_reported": self.violation_reported,
            "historical_events": len(self.parking_history)
        }
        
        if self.current_event:
            status["current_event"] = {
                "duration": self.current_event.duration,
                "is_violation": self.current_event.is_violation,
                "violation_types": [vt.value for vt in self.current_event.violation_types],
                "severity": self.current_event.violation_severity,
                "location": self.current_event.location
            }
        
        return status


class StreamParkingMonitor:
    """
    Parking monitor for individual CCTV stream.
    
    Coordinates parking monitoring for all vehicles in a single stream,
    manages parking zones, and maintains violation history.
    """
    
    def __init__(self, stream_id: str, config: Dict[str, Any]):
        self.stream_id = stream_id
        self.config = config
        self.vehicle_monitors: Dict[str, VehicleMonitor] = {}
        self.parking_zones: List[ParkingZone] = []
        self.active_violations: List[ParkingEvent] = []
        self.completed_events: deque = deque(maxlen=1000)
        self.lock = threading.Lock()
        
        # Load parking zones from configuration
        self._load_parking_zones()
        
        logger.info(f"StreamParkingMonitor initialized for stream {stream_id}")
    
    def _load_parking_zones(self):
        """Load parking zones from configuration."""
        # TODO: Implement parking zone loading from config
        # For now, create default zones based on stream configuration
        
        # Example default zone (no parking anywhere)
        default_zone = ParkingZone(
            zone_id=f"{self.stream_id}_default",
            name="Default Zone",
            zone_type="restricted",
            center_point=(640.0, 360.0),  # Center of typical video frame
            radius=1000.0,  # Cover entire frame
            max_parking_duration=300.0,  # 5 minutes
            description="Default monitoring zone"
        )
        
        self.parking_zones = [default_zone]
        logger.debug(f"Loaded {len(self.parking_zones)} parking zones for stream {self.stream_id}")
    
    def update_with_tracks(self, tracks: List[VehicleTrack], current_time: float) -> List[ParkingEvent]:
        """
        Update monitoring with latest vehicle tracks.
        
        Args:
            tracks: List of active vehicle tracks
            current_time: Current timestamp
            
        Returns:
            List[ParkingEvent]: List of newly completed parking events
        """
        with self.lock:
            completed_events = []
            active_track_ids = {track.track_id for track in tracks}
            
            # Update existing monitors
            for track in tracks:
                if track.track_id not in self.vehicle_monitors:
                    # Create new monitor for new track
                    self.vehicle_monitors[track.track_id] = VehicleMonitor(
                        track.track_id, self.stream_id, self.config
                    )
                
                # Update monitor with track data
                monitor = self.vehicle_monitors[track.track_id]
                completed_event = monitor.update_with_track(track, current_time, self.parking_zones)
                
                if completed_event:
                    completed_events.append(completed_event)
                    self.completed_events.append(completed_event)
            
            # Clean up monitors for inactive tracks
            inactive_monitors = []
            for track_id, monitor in self.vehicle_monitors.items():
                if track_id not in active_track_ids:
                    # Finalize any active parking event
                    if monitor.is_currently_parked:
                        # Create a dummy track for finalization
                        dummy_track = type('DummyTrack', (), {
                            'track_id': track_id,
                            'class_name': 'vehicle',
                            'state': 'lost',
                            'confidence_history': [0.5],
                            'tracking_quality': 0.5,
                            'current_detection': None
                        })()
                        
                        completed_event = monitor._end_parking_event(dummy_track, current_time)
                        if completed_event:
                            completed_events.append(completed_event)
                            self.completed_events.append(completed_event)
                    
                    inactive_monitors.append(track_id)
            
            # Remove inactive monitors
            for track_id in inactive_monitors:
                del self.vehicle_monitors[track_id]
                logger.debug(f"Removed inactive vehicle monitor: {track_id}")
            
            # Update active violations list
            self._update_active_violations(current_time)
            
            return completed_events
    
    def _update_active_violations(self, current_time: float):
        """Update list of currently active violations."""
        self.active_violations.clear()
        
        for monitor in self.vehicle_monitors.values():
            if monitor.current_event and monitor.current_event.is_violation:
                self.active_violations.append(monitor.current_event)
        
        logger.debug(f"Stream {self.stream_id}: {len(self.active_violations)} active violations")
    
    def get_active_violations(self) -> List[ParkingEvent]:
        """Get list of currently active parking violations."""
        with self.lock:
            return self.active_violations.copy()
    
    def get_stream_statistics(self) -> Dict[str, Any]:
        """Get comprehensive parking monitoring statistics."""
        with self.lock:
            stats = {
                "stream_id": self.stream_id,
                "active_monitors": len(self.vehicle_monitors),
                "active_violations": len(self.active_violations),
                "total_completed_events": len(self.completed_events),
                "parking_zones": len(self.parking_zones)
            }
            
            # Calculate violation statistics
            if self.completed_events:
                total_violations = sum(1 for event in self.completed_events if event.is_violation)
                stats["violation_rate"] = total_violations / len(self.completed_events)
                
                # Average violation duration
                violation_events = [e for e in self.completed_events if e.is_violation]
                if violation_events:
                    avg_violation_duration = np.mean([e.get_violation_duration() for e in violation_events])
                    stats["avg_violation_duration"] = avg_violation_duration
            
            return stats


class ParkingMonitorManager:
    """
    Central coordinator for parking monitoring across all CCTV streams.
    
    Manages individual stream monitors, aggregates violation data,
    and provides system-wide parking monitoring coordination.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stream_monitors: Dict[str, StreamParkingMonitor] = {}
        self.lock = threading.Lock()
        
        # Load monitoring configuration
        self.monitoring_config = config.get('processing', {}).get('parking', {})
        
        logger.info("ParkingMonitorManager initialized")
    
    def initialize_stream_monitor(self, stream_id: str) -> bool:
        """
        Initialize parking monitor for a specific stream.
        
        Args:
            stream_id: ID of the CCTV stream
            
        Returns:
            bool: True if initialization successful
        """
        try:
            with self.lock:
                if stream_id in self.stream_monitors:
                    logger.warning(f"Stream monitor already exists for {stream_id}")
                    return True
                
                monitor = StreamParkingMonitor(stream_id, self.monitoring_config)
                self.stream_monitors[stream_id] = monitor
                
                logger.info(f"Parking monitor initialized for stream {stream_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize parking monitor for {stream_id}: {e}")
            return False
    
    def update_stream_monitoring(self, stream_id: str, tracks: List[VehicleTrack], 
                               current_time: float) -> List[ParkingEvent]:
        """
        Update parking monitoring for specific stream.
        
        Args:
            stream_id: ID of the CCTV stream
            tracks: List of active vehicle tracks
            current_time: Current timestamp
            
        Returns:
            List[ParkingEvent]: List of newly completed parking events
        """
        if stream_id not in self.stream_monitors:
            logger.error(f"No parking monitor for stream {stream_id}")
            return []
        
        try:
            monitor = self.stream_monitors[stream_id]
            return monitor.update_with_tracks(tracks, current_time)
            
        except Exception as e:
            logger.error(f"Error updating parking monitoring for {stream_id}: {e}")
            return []
    
    def get_all_active_violations(self) -> Dict[str, List[ParkingEvent]]:
        """Get active violations from all streams."""
        all_violations = {}
        
        with self.lock:
            for stream_id, monitor in self.stream_monitors.items():
                violations = monitor.get_active_violations()
                if violations:
                    all_violations[stream_id] = violations
        
        return all_violations
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide parking monitoring statistics."""
        with self.lock:
            stats = {
                "total_streams": len(self.stream_monitors),
                "streams": {}
            }
            
            total_violations = 0
            total_monitors = 0
            
            for stream_id, monitor in self.stream_monitors.items():
                stream_stats = monitor.get_stream_statistics()
                stats["streams"][stream_id] = stream_stats
                
                total_violations += stream_stats.get("active_violations", 0)
                total_monitors += stream_stats.get("active_monitors", 0)
            
            stats["total_active_violations"] = total_violations
            stats["total_active_monitors"] = total_monitors
            
            return stats
    
    def cleanup_stream_monitor(self, stream_id: str):
        """Remove and cleanup monitor for specific stream."""
        with self.lock:
            if stream_id in self.stream_monitors:
                del self.stream_monitors[stream_id]
                logger.info(f"Cleaned up parking monitor for stream {stream_id}")


# Global instance - will be initialized by main application
parking_monitor_manager: Optional[ParkingMonitorManager] = None


def initialize_parking_monitor(config: Dict[str, Any]) -> bool:
    """
    Initialize the global parking monitor manager instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global parking_monitor_manager
    
    try:
        parking_monitor_manager = ParkingMonitorManager(config)
        logger.info("Parking monitor manager initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize parking monitor manager: {e}")
        return False


def get_parking_monitor() -> Optional[ParkingMonitorManager]:
    """
    Get the global parking monitor manager instance.
    
    Returns:
        Optional[ParkingMonitorManager]: Manager instance or None if not initialized
    """
    return parking_monitor_manager