"""
Data Models and Structures for AI Processor

This module defines data classes and structures for:
- Configuration validation schemas
- Internal processing data structures
- Task queue message formats
- Violation report structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from enum import Enum


# =============================================================================
# Configuration Data Structures
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for AI models"""
    path: str
    confidence_threshold: float
    iou_threshold: float = 0.45
    device: str = "auto"
    
    def __post_init__(self):
        """Validate configuration values"""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0.0 and 1.0")


@dataclass
class LicensePlateConfig:
    """Configuration for license plate detection and OCR"""
    detector_path: str
    detector_confidence: float
    detector_iou: float
    ocr_model_path: str
    ocr_languages: List[str]
    ocr_gpu: bool
    ocr_confidence: float
    
    def __post_init__(self):
        """Validate configuration values"""
        if not 0.0 <= self.detector_confidence <= 1.0:
            raise ValueError("detector_confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.ocr_confidence <= 1.0:
            raise ValueError("ocr_confidence must be between 0.0 and 1.0")


@dataclass
class ProcessingConfig:
    """Configuration for processing parameters"""
    parking_duration_threshold: int  # seconds
    worker_pool_size: int
    queue_max_size: int
    retry_attempts: int
    retry_delay: int
    
    def __post_init__(self):
        """Validate configuration values"""
        if self.worker_pool_size < 1:
            raise ValueError("worker_pool_size must be at least 1")
        if self.queue_max_size < 1:
            raise ValueError("queue_max_size must be at least 1")


@dataclass 
class StreamConfig:
    """Configuration for CCTV streams"""
    id: str
    name: str
    source_type: str  # "image_sequence", "rtsp", "http"
    path: str
    fps: int
    enabled: bool
    location: Dict[str, Union[float, str]]
    
    def __post_init__(self):
        """Validate configuration values"""
        if self.fps < 1:
            raise ValueError("fps must be at least 1")
        if "latitude" not in self.location or "longitude" not in self.location:
            raise ValueError("location must contain latitude and longitude")


# =============================================================================
# Processing Data Structures  
# =============================================================================

@dataclass
class BoundingBox:
    """Bounding box coordinates"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of bounding box"""
        return (self.x + self.width // 2, self.y + self.height // 2)
        
    @property
    def area(self) -> int:
        """Get area of bounding box"""
        return self.width * self.height
        
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union with another bounding box"""
        # Calculate intersection
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
            
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        
        return intersection / union if union > 0 else 0.0


@dataclass
class VehicleTrack:
    """Vehicle tracking data structure"""
    track_id: int
    bbox: BoundingBox
    first_seen: datetime
    last_seen: datetime
    confidence: float
    positions: List[Tuple[int, int]] = field(default_factory=list)
    stationary_duration: float = 0.0
    vehicle_type: str = "unknown"
    
    def __post_init__(self):
        """Initialize position history with current center"""
        if not self.positions:
            self.positions = [self.bbox.center]
            
    def update_position(self, bbox: BoundingBox, timestamp: datetime) -> None:
        """Update vehicle position and tracking data"""
        self.bbox = bbox
        self.last_seen = timestamp
        self.positions.append(bbox.center)
        
        # Limit position history
        if len(self.positions) > 50:
            self.positions = self.positions[-50:]
            
    def is_stationary(self, threshold_pixels: int = 20) -> bool:
        """Check if vehicle has been stationary"""
        if len(self.positions) < 2:
            return False
            
        # Check recent positions
        recent_positions = self.positions[-10:] if len(self.positions) >= 10 else self.positions
        
        if len(recent_positions) < 2:
            return False
            
        # Calculate maximum distance from first position
        first_pos = recent_positions[0]
        max_distance = max(
            abs(pos[0] - first_pos[0]) + abs(pos[1] - first_pos[1])
            for pos in recent_positions
        )
        
        return max_distance <= threshold_pixels
        
    @property
    def duration_seconds(self) -> float:
        """Get total tracking duration in seconds"""
        return (self.last_seen - self.first_seen).total_seconds()


@dataclass
class ParkingEvent:
    """Parking violation candidate"""
    vehicle_track: VehicleTrack
    stream_id: str
    location: Tuple[float, float]  # lat, lng
    parking_start: datetime
    duration: int  # seconds
    violation_frame: np.ndarray  # captured image
    frame_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_violation(self) -> bool:
        """Check if parking duration exceeds threshold"""
        return self.duration >= 300  # 5 minutes default
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "vehicle_track_id": self.vehicle_track.track_id,
            "stream_id": self.stream_id,
            "location": {
                "latitude": self.location[0],
                "longitude": self.location[1]
            },
            "parking_start": self.parking_start.isoformat(),
            "duration": self.duration,
            "vehicle_type": self.vehicle_track.vehicle_type,
            "metadata": self.frame_metadata
        }


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """Task processing status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AnalysisTask:
    """Task for Phase 2 processing queue"""
    task_id: str
    parking_event: ParkingEvent
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    
    def start_processing(self, worker_id: str) -> None:
        """Mark task as started"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.worker_id = worker_id
        
    def complete_processing(self) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        
    def fail_processing(self, error: str) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now()
        
    def retry_processing(self) -> bool:
        """Attempt to retry the task"""
        if self.retry_count >= self.max_retries:
            return False
            
        self.retry_count += 1
        self.status = TaskStatus.RETRYING
        self.started_at = None
        self.worker_id = None
        return True
        
    @property
    def processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
        
    @property
    def queue_wait_time(self) -> float:
        """Get time spent waiting in queue"""
        start_time = self.started_at or datetime.now()
        return (start_time - self.created_at).total_seconds()


# =============================================================================
# Analysis Results
# =============================================================================

@dataclass
class DetectionResult:
    """Results from AI model detection"""
    bbox: BoundingBox
    class_name: str
    confidence: float
    model_name: str
    processing_time: float = 0.0


@dataclass
class OCRResult:
    """Results from OCR processing"""
    is_successful: bool
    plate_number: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            "isSuccessful": self.is_successful,
            "processingTime": self.processing_time
        }
        
        if self.is_successful and self.plate_number:
            result.update({
                "plateNumber": self.plate_number,
                "ocrConfidence": self.confidence
            })
        elif self.error_message:
            result["errorMessage"] = self.error_message
            
        return result


@dataclass
class AnalysisResult:
    """Complete analysis results for a parking event"""
    task_id: str
    parking_event: ParkingEvent
    is_illegal_by_model: bool
    model_confidence: float
    vehicle_type: str
    ocr_result: OCRResult
    processing_time: float
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_violation_report(self, cctv_id: int) -> 'ViolationReport':
        """Convert to violation report for backend"""
        return ViolationReport(
            cctv_id=cctv_id,
            timestamp=self.analysis_timestamp.isoformat(),
            location={
                "latitude": self.parking_event.location[0],
                "longitude": self.parking_event.location[1]
            },
            vehicle_image="",  # Will be filled with base64 encoded image
            ai_analysis={
                "isIllegalByModel": self.is_illegal_by_model,
                "modelConfidence": self.model_confidence,
                "vehicleType": self.vehicle_type,
                "ocrResult": self.ocr_result.to_dict(),
                "processingTime": self.processing_time,
                "trackingDuration": self.parking_event.duration
            }
        )


# =============================================================================
# Backend Communication
# =============================================================================

@dataclass
class ViolationReport:
    """Final report structure for backend API"""
    cctv_id: int
    timestamp: str  # ISO format
    location: Dict[str, float]  # {"latitude": ..., "longitude": ...}
    vehicle_image: str  # Base64 encoded
    ai_analysis: Dict[str, Any]  # Full AI results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "cctvId": self.cctv_id,
            "timestamp": self.timestamp,
            "location": self.location,
            "vehicleImage": self.vehicle_image,
            "aiAnalysis": self.ai_analysis
        }


@dataclass
class BackendResponse:
    """Response from backend API"""
    success: bool
    status_code: int
    message: str
    event_id: Optional[str] = None
    error_details: Optional[str] = None
    
    @classmethod
    def from_response(cls, response) -> 'BackendResponse':
        """Create from HTTP response object"""
        try:
            data = response.json()
            return cls(
                success=response.status_code == 200,
                status_code=response.status_code,
                message=data.get("message", ""),
                event_id=data.get("eventId"),
                error_details=data.get("error")
            )
        except Exception:
            return cls(
                success=False,
                status_code=response.status_code,
                message="Failed to parse response",
                error_details=response.text if hasattr(response, 'text') else str(response)
            )


# =============================================================================
# Performance Monitoring
# =============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    component: str
    operation: str
    duration: float
    timestamp: datetime = field(default_factory=datetime.now)
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        result = {
            "component": self.component,
            "operation": self.operation,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.memory_usage_mb is not None:
            result["memoryUsageMb"] = self.memory_usage_mb
        if self.cpu_usage_percent is not None:
            result["cpuUsagePercent"] = self.cpu_usage_percent
        if self.additional_data:
            result["additionalData"] = self.additional_data
            
        return result


@dataclass
class SystemHealth:
    """System health status"""
    component: str
    status: str  # "healthy", "warning", "critical", "unknown"
    message: str
    last_check: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == "healthy"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "component": self.component,
            "status": self.status,
            "message": self.message,
            "lastCheck": self.last_check.isoformat(),
            "metrics": self.metrics
        }


# =============================================================================
# Utility Functions
# =============================================================================

def create_analysis_task(parking_event: ParkingEvent, priority: TaskPriority = TaskPriority.NORMAL) -> AnalysisTask:
    """
    Create an analysis task from a parking event.
    
    Args:
        parking_event: The parking event to analyze
        priority: Task priority level
        
    Returns:
        AnalysisTask instance
    """
    task_id = f"{parking_event.stream_id}_{parking_event.vehicle_track.track_id}_{int(datetime.now().timestamp())}"
    
    return AnalysisTask(
        task_id=task_id,
        parking_event=parking_event,
        priority=priority
    )


def validate_config_data(config_dict: Dict[str, Any], schema_class) -> Any:
    """
    Validate configuration data against a dataclass schema.
    
    Args:
        config_dict: Configuration dictionary
        schema_class: Dataclass to validate against
        
    Returns:
        Validated dataclass instance
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return schema_class(**config_dict)
    except TypeError as e:
        raise ValueError(f"Configuration validation failed: {e}")


def estimate_image_size(image: np.ndarray, format: str = "jpg", quality: int = 85) -> int:
    """
    Estimate the size of an image when encoded.
    
    Args:
        image: Image array
        format: Image format ("jpg", "png")
        quality: JPEG quality (1-100)
        
    Returns:
        Estimated size in bytes
    """
    height, width = image.shape[:2]
    pixels = height * width
    
    if format.lower() == "jpg":
        # Rough estimation based on quality and pixel count
        compression_ratio = (100 - quality) / 100 * 0.8 + 0.05
        return int(pixels * 3 * compression_ratio)
    elif format.lower() == "png":
        # PNG is typically larger than JPEG
        return int(pixels * 3 * 0.7)
    else:
        # Default to uncompressed size
        return pixels * 3