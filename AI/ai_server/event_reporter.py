"""
Event Reporter Module for Real-time Spring Backend Integration

This module implements real-time event reporting to the Spring backend via REST API.
It handles violation events, vehicle tracking updates, license plate recognition results,
and system status notifications with retry mechanisms and queue management.

Key Features:
- Real-time violation event reporting to Spring backend
- Vehicle tracking and license plate data transmission
- Asynchronous HTTP client with connection pooling
- Event queuing with retry mechanisms and exponential backoff
- Webhook-style event notifications for immediate alerts
- Batch reporting for performance optimization
- Authentication and security token management

Architecture:
- EventReporter: Main event reporting coordinator
- RestApiClient: HTTP client with retry and authentication
- EventQueue: Asynchronous event queue with persistence
- EventFormatter: Format analysis results for Spring backend
"""

import logging
import asyncio
import time
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import threading
from collections import deque
import aiohttp
import aiofiles
from pathlib import Path

from analysis_pipeline import AnalysisResult
from parking_monitor import ParkingEvent
from multi_vehicle_tracker import VehicleTrack
from license_plate_detector import PlateDetectionResult
from ocr_reader import OCRResult
from geocoding_service import get_geocoding_service, reverse_geocode_coordinates
# Note: response_models.py was removed as part of FastAPI cleanup
# These data structures are now handled directly in the event reporter

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Data Conversion Functions for Event Formatting
# =============================================================================

def convert_parking_event_to_model(parking_event: ParkingEvent) -> Dict[str, Any]:
    """Convert ParkingEvent to dictionary model for backend."""
    return {
        "event_id": parking_event.event_id,
        "stream_id": parking_event.stream_id,
        "start_time": parking_event.start_time,
        "duration": parking_event.duration,
        "violation_severity": getattr(parking_event, 'violation_severity', 0.0),
        "is_confirmed": getattr(parking_event, 'is_confirmed', True),
        "vehicle_type": parking_event.vehicle_class,
        "parking_zone_type": getattr(parking_event, 'parking_zone_type', 'no_parking')
    }


def convert_vehicle_track_to_model(vehicle_track: VehicleTrack) -> Dict[str, Any]:
    """Convert VehicleTrack to dictionary model for backend."""
    return {
        "track_id": str(vehicle_track.track_id),
        "vehicle_type": getattr(vehicle_track, 'vehicle_type', 'car'),
        "confidence": getattr(vehicle_track, 'confidence', 0.9),
        "bounding_box": getattr(vehicle_track, 'bounding_box', [100, 150, 300, 400]),
        "last_position": list(getattr(vehicle_track, 'last_position', vehicle_track.location if hasattr(vehicle_track, 'location') else [125.4, 37.5]))
    }


def convert_plate_detection_to_model(plate_detection: PlateDetectionResult) -> Dict[str, Any]:
    """Convert PlateDetectionResult to dictionary model for backend."""
    return {
        "plate_text": getattr(plate_detection, 'plate_text', ''),
        "confidence": getattr(plate_detection, 'confidence', 0.0),
        "bounding_box": getattr(plate_detection, 'bounding_box', [180, 320, 280, 350]),
        "is_valid_format": getattr(plate_detection, 'is_valid_format', False)
    }


def convert_ocr_result_to_model(ocr_result: OCRResult) -> Dict[str, Any]:
    """Convert OCRResult to dictionary model for backend."""
    return {
        "recognized_text": getattr(ocr_result, 'recognized_text', getattr(ocr_result, 'plate_number', '')),
        "confidence": getattr(ocr_result, 'confidence', 0.0),
        "is_valid_format": getattr(ocr_result, 'is_valid_format', getattr(ocr_result, 'is_successful', False))
    }


class EventType(str, Enum):
    """Types of events to report to Spring backend."""
    VIOLATION_DETECTED = "violation_detected"
    VIOLATION_ENDED = "violation_ended"
    VEHICLE_ENTERED = "vehicle_entered"
    VEHICLE_EXITED = "vehicle_exited"
    LICENSE_PLATE_DETECTED = "license_plate_detected"
    LICENSE_PLATE_RECOGNIZED = "license_plate_recognized"
    SYSTEM_STATUS_UPDATE = "system_status_update"
    ANALYSIS_SUMMARY = "analysis_summary"


class EventPriority(str, Enum):
    """Event priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ReportingEvent:
    """Event data structure for backend reporting."""
    event_type: EventType
    priority: EventPriority
    timestamp: float
    stream_id: str
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    event_id: str = ""
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"{self.event_type}_{self.stream_id}_{int(self.timestamp)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON transmission."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "stream_id": self.stream_id,
            "correlation_id": self.correlation_id,
            "data": self.data
        }


class RestApiClient:
    """
    HTTP client for Spring backend communication.
    
    Handles authentication, connection pooling, retry logic,
    and error handling for REST API communications.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # API configuration
        self.base_url = config.get('base_url', 'http://localhost:8080')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 30.0)
        self.max_concurrent_requests = config.get('max_concurrent_requests', 10)
        
        # Retry configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        self.retry_backoff = config.get('retry_backoff', 2.0)
        
        # HTTP client
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        
        # Rate limiting
        self.request_semaphore: Optional[asyncio.Semaphore] = None
        self.last_request_time = 0.0
        self.min_request_interval = config.get('min_request_interval', 0.1)  # 10 requests per second max
        
        # Authentication
        self.auth_token: Optional[str] = None
        self.auth_expires: Optional[float] = None
        
        logger.info(f"RestApiClient initialized with base URL: {self.base_url}")
    
    async def initialize(self) -> bool:
        """
        Initialize HTTP client session.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Create connector with connection pooling
            self.connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_requests,
                limit_per_host=self.max_concurrent_requests,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            # Create session with timeout and headers
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'IllegalParkingDetection-AI/1.0'
            }
            
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers=headers
            )
            
            # Initialize rate limiting
            self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            # Test connection
            await self._test_connection()
            
            logger.info("RestApiClient initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RestApiClient: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test connection to Spring backend."""
        try:
            url = f"{self.base_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    logger.info("Successfully connected to Spring backend")
                    return True
                else:
                    logger.warning(f"Health check returned status {response.status}")
                    return False
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def post_event(self, endpoint: str, event: ReportingEvent) -> bool:
        """
        Post event to Spring backend endpoint.
        
        Args:
            endpoint: API endpoint path
            event: Event to send
            
        Returns:
            bool: True if request successful
        """
        if not self.session:
            logger.error("HTTP client not initialized")
            return False
        
        try:
            async with self.request_semaphore:
                # Rate limiting
                await self._apply_rate_limit()
                
                # Prepare request
                url = f"{self.base_url}{endpoint}"
                data = event.to_dict()
                
                # Add authentication if needed
                headers = await self._get_auth_headers()
                
                logger.debug(f"Sending event {event.event_id} to {url}")
                
                # Send request with retries
                for attempt in range(self.max_retries + 1):
                    try:
                        async with self.session.post(
                            url, 
                            json=data, 
                            headers=headers
                        ) as response:
                            
                            if response.status == 200:
                                logger.debug(f"Event {event.event_id} sent successfully")
                                return True
                            elif response.status == 401:
                                # Authentication error - refresh token and retry
                                await self._refresh_auth_token()
                                headers = await self._get_auth_headers()
                                continue
                            elif response.status >= 500:
                                # Server error - retry
                                if attempt < self.max_retries:
                                    await asyncio.sleep(self.retry_delay * (self.retry_backoff ** attempt))
                                    continue
                            else:
                                # Client error - don't retry
                                response_text = await response.text()
                                logger.error(f"Event {event.event_id} failed with status {response.status}: {response_text}")
                                return False
                    
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout sending event {event.event_id}, attempt {attempt + 1}")
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay * (self.retry_backoff ** attempt))
                    except Exception as e:
                        logger.warning(f"Error sending event {event.event_id}, attempt {attempt + 1}: {e}")
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay * (self.retry_backoff ** attempt))
                
                logger.error(f"Failed to send event {event.event_id} after {self.max_retries + 1} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error sending event {event.event_id}: {e}")
            return False
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        
        if self.auth_token and (not self.auth_expires or time.time() < self.auth_expires):
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        return headers
    
    async def _refresh_auth_token(self):
        """Refresh authentication token."""
        # Implementation depends on your authentication mechanism
        # This is a placeholder for token refresh logic
        logger.info("Token refresh requested (not implemented)")
    
    async def cleanup(self):
        """Cleanup HTTP client resources."""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.connector:
            await self.connector.close()
            self.connector = None
        
        logger.info("RestApiClient cleanup completed")


class EventQueue:
    """
    Asynchronous event queue with persistence and retry handling.
    
    Manages queuing, persistence, and retry logic for events
    that need to be sent to the Spring backend.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Queue configuration
        self.max_queue_size = config.get('max_queue_size', 10000)
        self.batch_size = config.get('batch_size', 10)
        self.flush_interval = config.get('flush_interval', 5.0)  # seconds
        
        # Persistence configuration
        self.persist_events = config.get('persist_events', True)
        self.persistence_file = config.get('persistence_file', 'event_queue.json')
        
        # Event queues by priority
        self.urgent_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.high_queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self.normal_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.low_queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        
        # Failed events for retry
        self.retry_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Processing control
        self.is_running = False
        self.processor_task: Optional[asyncio.Task] = None
        self.retry_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.events_queued = 0
        self.events_sent = 0
        self.events_failed = 0
        
        logger.info("EventQueue initialized")
    
    async def start(self):
        """Start event queue processing."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Load persisted events
        await self._load_persisted_events()
        
        # Start processor tasks
        self.processor_task = asyncio.create_task(self._process_events())
        self.retry_task = asyncio.create_task(self._process_retries())
        
        logger.info("EventQueue processing started")
    
    async def stop(self):
        """Stop event queue processing and persist remaining events."""
        self.is_running = False
        
        # Cancel tasks
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        # Persist remaining events
        await self._persist_events()
        
        logger.info("EventQueue processing stopped")
    
    async def enqueue(self, event: ReportingEvent) -> bool:
        """
        Add event to appropriate priority queue.
        
        Args:
            event: Event to queue
            
        Returns:
            bool: True if event was queued successfully
        """
        try:
            # Select queue based on priority
            if event.priority == EventPriority.URGENT:
                queue = self.urgent_queue
            elif event.priority == EventPriority.HIGH:
                queue = self.high_queue
            elif event.priority == EventPriority.NORMAL:
                queue = self.normal_queue
            else:
                queue = self.low_queue
            
            # Try to enqueue without blocking
            try:
                queue.put_nowait(event)
                self.events_queued += 1
                logger.debug(f"Queued event {event.event_id} (priority: {event.priority})")
                return True
            except asyncio.QueueFull:
                logger.warning(f"Queue full for priority {event.priority}, dropping event {event.event_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error queuing event {event.event_id}: {e}")
            return False
    
    async def _process_events(self):
        """Main event processing loop."""
        logger.info("Event processor started")
        
        while self.is_running:
            try:
                # Process events by priority order
                event = await self._get_next_event()
                
                if event:
                    await self._send_event(event)
                else:
                    # No events available, wait a bit
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(1.0)
        
        logger.info("Event processor stopped")
    
    async def _get_next_event(self) -> Optional[ReportingEvent]:
        """Get next event to process based on priority."""
        queues = [
            self.urgent_queue,
            self.high_queue, 
            self.normal_queue,
            self.low_queue
        ]
        
        for queue in queues:
            try:
                return queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    async def _send_event(self, event: ReportingEvent):
        """Send individual event."""
        # This will be implemented by the EventReporter
        # For now, just mark as processed
        logger.debug(f"Processing event {event.event_id}")
    
    async def _process_retries(self):
        """Process retry queue for failed events."""
        logger.info("Retry processor started")
        
        while self.is_running:
            try:
                # Wait for retry events
                try:
                    event = await asyncio.wait_for(self.retry_queue.get(), timeout=5.0)
                    
                    # Apply exponential backoff
                    delay = self.config.get('retry_delay', 1.0) * (2 ** event.retry_count)
                    await asyncio.sleep(min(delay, 60.0))  # Cap at 60 seconds
                    
                    # Re-queue for processing
                    await self.enqueue(event)
                    
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in retry processor: {e}")
                await asyncio.sleep(1.0)
        
        logger.info("Retry processor stopped")
    
    async def _load_persisted_events(self):
        """Load persisted events from file."""
        if not self.persist_events:
            return
        
        try:
            if Path(self.persistence_file).exists():
                async with aiofiles.open(self.persistence_file, 'r') as f:
                    content = await f.read()
                    events_data = json.loads(content)
                    
                    for event_data in events_data:
                        event = ReportingEvent(
                            event_type=EventType(event_data['event_type']),
                            priority=EventPriority(event_data['priority']),
                            timestamp=event_data['timestamp'],
                            stream_id=event_data['stream_id'],
                            data=event_data['data'],
                            event_id=event_data['event_id'],
                            correlation_id=event_data.get('correlation_id'),
                            retry_count=event_data.get('retry_count', 0)
                        )
                        await self.enqueue(event)
                    
                    logger.info(f"Loaded {len(events_data)} persisted events")
                    
                # Remove persistence file after loading
                Path(self.persistence_file).unlink()
                
        except Exception as e:
            logger.error(f"Error loading persisted events: {e}")
    
    async def _persist_events(self):
        """Persist remaining events to file."""
        if not self.persist_events:
            return
        
        try:
            events_to_persist = []
            
            # Collect events from all queues
            queues = [self.urgent_queue, self.high_queue, self.normal_queue, self.low_queue, self.retry_queue]
            
            for queue in queues:
                while not queue.empty():
                    try:
                        event = queue.get_nowait()
                        events_to_persist.append(event.to_dict())
                    except asyncio.QueueEmpty:
                        break
            
            if events_to_persist:
                async with aiofiles.open(self.persistence_file, 'w') as f:
                    await f.write(json.dumps(events_to_persist, indent=2))
                
                logger.info(f"Persisted {len(events_to_persist)} events")
                
        except Exception as e:
            logger.error(f"Error persisting events: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "events_queued": self.events_queued,
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "queue_sizes": {
                "urgent": self.urgent_queue.qsize(),
                "high": self.high_queue.qsize(),
                "normal": self.normal_queue.qsize(),
                "low": self.low_queue.qsize(),
                "retry": self.retry_queue.qsize()
            }
        }


class EventFormatter:
    """
    Formats analysis results into events for Spring backend reporting.
    
    Converts AI analysis data into structured events that the Spring
    backend can process and store.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.include_raw_data = config.get('include_raw_data', False)
        self.max_data_size = config.get('max_data_size', 10000)  # bytes
    
    def format_violation_event(self, parking_event: ParkingEvent, 
                              vehicle_track: Optional[VehicleTrack] = None,
                              plate_detection: Optional[PlateDetectionResult] = None,
                              ocr_result: Optional[OCRResult] = None) -> ReportingEvent:
        """Format parking violation into reporting event."""
        
        # Phase 2: AI 역지오코딩 연동 - GPS 좌표를 한국 주소로 변환
        location_info = {
            "latitude": parking_event.location[0] if parking_event.location else 0.0,
            "longitude": parking_event.location[1] if parking_event.location else 0.0,
            "address": None,
            "formatted_address": None
        }
        
        # 역지오코딩 수행 (AI → Backend 전송 시 주소 정보 포함)
        if parking_event.location and parking_event.location != (0.0, 0.0):
            try:
                geocoding_result = reverse_geocode_coordinates(
                    parking_event.location[0], 
                    parking_event.location[1]
                )
                
                if geocoding_result.is_geocoded:
                    location_info["address"] = geocoding_result.address
                    location_info["formatted_address"] = geocoding_result.formatted_address
                    logger.debug(f"Geocoding successful for event {parking_event.event_id}: {geocoding_result.formatted_address}")
                else:
                    location_info["formatted_address"] = geocoding_result.formatted_address  # 좌표 형태 fallback
                    logger.debug(f"Geocoding fallback for event {parking_event.event_id}: {geocoding_result.error_message}")
            except Exception as e:
                logger.warning(f"Geocoding failed for event {parking_event.event_id}: {e}")
                location_info["formatted_address"] = f"좌표: {location_info['latitude']:.6f}, {location_info['longitude']:.6f}"
        
        event_data = {
            "violation": convert_parking_event_to_model(parking_event),
            "stream_info": {
                "stream_id": parking_event.stream_id,
                "location_name": self._get_stream_name(parking_event.stream_id),
                # Phase 2: 역지오코딩된 위치 정보 추가
                "latitude": location_info["latitude"],
                "longitude": location_info["longitude"],
                "address": location_info["address"],
                "formatted_address": location_info["formatted_address"]
            }
        }
        
        # Add vehicle information
        if vehicle_track:
            event_data["vehicle"] = convert_vehicle_track_to_model(vehicle_track)
        
        # Add license plate information
        if plate_detection:
            event_data["license_plate"] = convert_plate_detection_to_model(plate_detection)
        
        # Add OCR results
        if ocr_result:
            event_data["ocr_result"] = convert_ocr_result_to_model(ocr_result)
        
        # AI INTEGRATION - Add Base64 encoded violation image
        if hasattr(parking_event, 'violation_frame') and parking_event.violation_frame is not None:
            import cv2
            import base64
            try:
                # Encode violation frame as Base64 JPEG (85% quality for optimal size)
                _, buffer = cv2.imencode('.jpg', parking_event.violation_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                event_data["vehicle_image"] = f"data:image/jpeg;base64,{image_base64}"
                logger.debug(f"Added violation image to event {parking_event.event_id} ({len(image_base64)} chars)")
            except Exception as e:
                logger.error(f"Failed to encode violation image for event {parking_event.event_id}: {e}")
                # Continue without image - don't fail the entire event
        else:
            logger.debug(f"No violation frame available for event {parking_event.event_id}")
        
        # Determine priority based on violation severity
        if parking_event.violation_severity > 0.8:
            priority = EventPriority.URGENT
        elif parking_event.violation_severity > 0.6:
            priority = EventPriority.HIGH
        else:
            priority = EventPriority.NORMAL
        
        return ReportingEvent(
            event_type=EventType.VIOLATION_DETECTED,
            priority=priority,
            timestamp=parking_event.start_time,
            stream_id=parking_event.stream_id,
            data=event_data,
            correlation_id=parking_event.event_id
        )
    
    def format_vehicle_entry_event(self, vehicle_track: VehicleTrack) -> ReportingEvent:
        """Format vehicle entry event."""
        
        event_data = {
            "vehicle": convert_vehicle_track_to_model(vehicle_track),
            "stream_info": {
                "stream_id": vehicle_track.stream_id,
                "location_name": self._get_stream_name(vehicle_track.stream_id)
            }
        }
        
        return ReportingEvent(
            event_type=EventType.VEHICLE_ENTERED,
            priority=EventPriority.LOW,
            timestamp=vehicle_track.last_update_time,
            stream_id=vehicle_track.stream_id,
            data=event_data,
            correlation_id=vehicle_track.track_id
        )
    
    def format_license_plate_event(self, plate_detection: PlateDetectionResult,
                                  ocr_result: Optional[OCRResult] = None,
                                  vehicle_track: Optional[VehicleTrack] = None) -> ReportingEvent:
        """Format license plate detection/recognition event."""
        
        event_data = {
            "license_plate": convert_plate_detection_to_model(plate_detection),
            "stream_info": {
                "stream_id": getattr(plate_detection, 'stream_id', ''),
                "location_name": self._get_stream_name(getattr(plate_detection, 'stream_id', ''))
            }
        }
        
        # Add OCR results if available
        if ocr_result:
            event_data["ocr_result"] = convert_ocr_result_to_model(ocr_result)
            event_type = EventType.LICENSE_PLATE_RECOGNIZED
        else:
            event_type = EventType.LICENSE_PLATE_DETECTED
        
        # Add vehicle information
        if vehicle_track:
            event_data["vehicle"] = convert_vehicle_track_to_model(vehicle_track)
        
        # Higher priority for recognized plates
        priority = EventPriority.NORMAL if ocr_result and ocr_result.is_valid_format else EventPriority.LOW
        
        return ReportingEvent(
            event_type=event_type,
            priority=priority,
            timestamp=time.time(),
            stream_id=getattr(plate_detection, 'stream_id', ''),
            data=event_data
        )
    
    def format_analysis_summary_event(self, analysis_result: AnalysisResult) -> ReportingEvent:
        """Format analysis summary for periodic reporting."""
        
        event_data = {
            "summary": analysis_result.get_summary(),
            "performance": {
                "processing_time": analysis_result.processing_time,
                "fps": analysis_result.fps,
                "component_timings": analysis_result.component_timings
            },
            "stream_info": {
                "stream_id": analysis_result.stream_id,
                "location_name": self._get_stream_name(analysis_result.stream_id)
            }
        }
        
        return ReportingEvent(
            event_type=EventType.ANALYSIS_SUMMARY,
            priority=EventPriority.LOW,
            timestamp=analysis_result.timestamp,
            stream_id=analysis_result.stream_id,
            data=event_data
        )
    
    def _get_stream_name(self, stream_id: str) -> str:
        """Get human-readable stream name."""
        # This could be loaded from configuration
        stream_names = self.config.get('stream_names', {})
        return stream_names.get(stream_id, stream_id)
    
    def _truncate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate data if it exceeds size limit."""
        serialized = json.dumps(data)
        if len(serialized.encode('utf-8')) > self.max_data_size:
            # Remove raw image data or other large fields
            if 'raw_detection' in data:
                del data['raw_detection']
            if 'original_frame' in data:
                del data['original_frame']
        
        return data


class EventReporter:
    """
    Main event reporting coordinator for Spring backend integration.
    
    Manages the complete event reporting pipeline from analysis results
    to Spring backend delivery with queuing, retry, and formatting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.rest_client = RestApiClient(config.get('rest_api', {}))
        self.event_queue = EventQueue(config.get('event_queue', {}))
        self.event_formatter = EventFormatter(config.get('event_formatting', {}))
        
        # API endpoints - Updated to match actual backend endpoints
        self.endpoints = config.get('endpoints', {
            'violation_detected': '/api/ai/v1/report-detection',  # Main violation reporting endpoint
            'stream_sync': '/api/cctvs/sync',                      # CCTV stream synchronization endpoint
            'vehicle_entered': '/api/vehicles/enter',
            'vehicle_exited': '/api/vehicles/exit',
            'license_plate_detected': '/api/license-plates',
            'system_status': '/api/system/status',
            'analysis_summary': '/api/analysis/summary'
        })
        
        # Reporting configuration
        self.enable_violation_reporting = config.get('enable_violation_reporting', True)
        self.enable_vehicle_tracking = config.get('enable_vehicle_tracking', False)
        self.enable_license_plate_reporting = config.get('enable_license_plate_reporting', True)
        self.enable_summary_reporting = config.get('enable_summary_reporting', True)
        self.summary_interval = config.get('summary_interval', 60.0)  # seconds
        
        # Event callbacks
        self.violation_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # Statistics
        self.total_events_reported = 0
        self.last_summary_time = 0.0
        
        logger.info("EventReporter initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize event reporter and all components.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize REST client
            if not await self.rest_client.initialize():
                logger.error("Failed to initialize REST client")
                return False
            
            # Start event queue
            await self.event_queue.start()
            
            # Override queue event sender
            self.event_queue._send_event = self._send_event_to_backend
            
            logger.info("EventReporter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize EventReporter: {e}")
            return False
    
    async def report_violation(self, parking_event: ParkingEvent,
                             vehicle_track: Optional[VehicleTrack] = None,
                             plate_detection: Optional[PlateDetectionResult] = None,
                             ocr_result: Optional[OCRResult] = None) -> bool:
        """
        Report parking violation to Spring backend.
        
        Args:
            parking_event: Parking violation event
            vehicle_track: Associated vehicle track
            plate_detection: License plate detection
            ocr_result: OCR recognition result
            
        Returns:
            bool: True if event was queued successfully
        """
        if not self.enable_violation_reporting:
            return True
        
        try:
            # Format violation event
            event = self.event_formatter.format_violation_event(
                parking_event, vehicle_track, plate_detection, ocr_result
            )
            
            # Queue for sending
            success = await self.event_queue.enqueue(event)
            
            if success:
                logger.info(f"Queued violation event: {parking_event.event_id}")
                
                # Trigger callbacks
                for callback in self.violation_callbacks:
                    try:
                        await callback(parking_event, vehicle_track, plate_detection, ocr_result)
                    except Exception as e:
                        logger.error(f"Error in violation callback: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error reporting violation: {e}")
            return False
    
    async def report_vehicle_tracking(self, vehicle_track: VehicleTrack, 
                                    event_type: EventType) -> bool:
        """
        Report vehicle tracking events.
        
        Args:
            vehicle_track: Vehicle track data
            event_type: Type of vehicle event
            
        Returns:
            bool: True if event was queued successfully
        """
        if not self.enable_vehicle_tracking:
            return True
        
        try:
            if event_type == EventType.VEHICLE_ENTERED:
                event = self.event_formatter.format_vehicle_entry_event(vehicle_track)
            else:
                # For now, only handle vehicle entry
                return True
            
            return await self.event_queue.enqueue(event)
            
        except Exception as e:
            logger.error(f"Error reporting vehicle tracking: {e}")
            return False
    
    async def report_license_plate(self, plate_detection: PlateDetectionResult,
                                 ocr_result: Optional[OCRResult] = None,
                                 vehicle_track: Optional[VehicleTrack] = None) -> bool:
        """
        Report license plate detection/recognition.
        
        Args:
            plate_detection: License plate detection
            ocr_result: OCR recognition result
            vehicle_track: Associated vehicle track
            
        Returns:
            bool: True if event was queued successfully
        """
        if not self.enable_license_plate_reporting:
            return True
        
        try:
            event = self.event_formatter.format_license_plate_event(
                plate_detection, ocr_result, vehicle_track
            )
            
            return await self.event_queue.enqueue(event)
            
        except Exception as e:
            logger.error(f"Error reporting license plate: {e}")
            return False
    
    async def report_analysis_summary(self, analysis_result: AnalysisResult) -> bool:
        """
        Report periodic analysis summary.
        
        Args:
            analysis_result: Analysis pipeline result
            
        Returns:
            bool: True if event was queued successfully
        """
        if not self.enable_summary_reporting:
            return True
        
        # Check if it's time for summary report
        current_time = time.time()
        if current_time - self.last_summary_time < self.summary_interval:
            return True
        
        try:
            event = self.event_formatter.format_analysis_summary_event(analysis_result)
            success = await self.event_queue.enqueue(event)
            
            if success:
                self.last_summary_time = current_time
            
            return success
            
        except Exception as e:
            logger.error(f"Error reporting analysis summary: {e}")
            return False
    
    async def _send_event_to_backend(self, event: ReportingEvent):
        """Send event to Spring backend via REST API."""
        try:
            # Get appropriate endpoint
            endpoint = self.endpoints.get(event.event_type.value)
            if not endpoint:
                logger.error(f"No endpoint configured for event type: {event.event_type}")
                self.event_queue.events_failed += 1
                return
            
            # Send event
            success = await self.rest_client.post_event(endpoint, event)
            
            if success:
                self.event_queue.events_sent += 1
                self.total_events_reported += 1
                logger.debug(f"Successfully sent event {event.event_id}")
            else:
                # Handle retry logic
                event.retry_count += 1
                if event.retry_count <= event.max_retries:
                    await self.event_queue.retry_queue.put(event)
                    logger.info(f"Queued event {event.event_id} for retry ({event.retry_count}/{event.max_retries})")
                else:
                    self.event_queue.events_failed += 1
                    logger.error(f"Event {event.event_id} failed permanently after {event.retry_count} retries")
                    
                    # Trigger error callbacks
                    for callback in self.error_callbacks:
                        try:
                            await callback(event, "Max retries exceeded")
                        except Exception as e:
                            logger.error(f"Error in error callback: {e}")
        
        except Exception as e:
            logger.error(f"Error sending event {event.event_id}: {e}")
            self.event_queue.events_failed += 1
    
    def add_violation_callback(self, callback: Callable):
        """Add callback for violation events."""
        self.violation_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable):
        """Add callback for error events."""
        self.error_callbacks.append(callback)
    
    async def sync_cctv_streams(self, stream_list: List[Dict[str, Any]]) -> bool:
        """
        Synchronize CCTV stream information to backend database.
        Called during AI system initialization to register available streams.
        
        Args:
            stream_list: List of stream information dictionaries containing:
                - streamId: Stream identifier (e.g., "cctv_001") 
                - streamName: Human-readable name
                - streamUrl: Stream URL for frontend playback
                - location: Address/location description (optional)
                - latitude: GPS latitude coordinate (optional)
                - longitude: GPS longitude coordinate (optional)
                - active: Stream availability status
                
        Returns:
            bool: True if synchronization successful
        """
        try:
            logger.info(f"Synchronizing {len(stream_list)} CCTV streams to backend...")
            
            # Format stream data for backend API
            formatted_streams = []
            for stream_info in stream_list:
                # Extract coordinates
                latitude = stream_info.get("latitude", 0.0)
                longitude = stream_info.get("longitude", 0.0)
                location = stream_info.get("location", "")
                
                # Perform reverse geocoding if coordinates are available but location is empty
                if latitude != 0.0 and longitude != 0.0 and not location:
                    try:
                        geocoding_result = reverse_geocode_coordinates(latitude, longitude)
                        if geocoding_result.is_geocoded:
                            location = geocoding_result.formatted_address
                            logger.debug(f"Enhanced stream {stream_info['streamId']} with geocoded address: {location}")
                    except Exception as e:
                        logger.warning(f"Geocoding failed for stream {stream_info['streamId']}: {e}")
                        location = f"좌표: {latitude:.6f}, {longitude:.6f}"
                
                formatted_stream = {
                    "streamId": stream_info["streamId"],
                    "streamName": stream_info.get("streamName", stream_info["streamId"]),
                    "streamUrl": stream_info["streamUrl"],
                    "location": location,
                    "latitude": latitude,
                    "longitude": longitude,
                    "streamSource": stream_info.get("streamSource", "korean_its_api"),
                    "active": stream_info.get("active", True),
                    "discoveredAt": datetime.now().isoformat()
                }
                formatted_streams.append(formatted_stream)
            
            # Send to backend via REST API
            endpoint = self.endpoints.get('stream_sync')
            if not endpoint:
                logger.error("Stream sync endpoint not configured")
                return False
            
            # Prepare request payload
            url = f"{self.rest_client.base_url}{endpoint}"
            
            try:
                # Use direct HTTP request for stream sync
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        json=formatted_streams,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Successfully synchronized {len(formatted_streams)} streams to backend: {result}")
                            return True
                        else:
                            error_text = await response.text()
                            logger.error(f"Backend sync failed with status {response.status}: {error_text}")
                            return False
                            
            except Exception as e:
                logger.error(f"HTTP request failed for stream sync: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error synchronizing CCTV streams: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive reporting statistics."""
        return {
            "total_events_reported": self.total_events_reported,
            "queue_stats": self.event_queue.get_statistics(),
            "configuration": {
                "violation_reporting": self.enable_violation_reporting,
                "vehicle_tracking": self.enable_vehicle_tracking,
                "license_plate_reporting": self.enable_license_plate_reporting,
                "summary_reporting": self.enable_summary_reporting
            }
        }
    
    async def cleanup(self):
        """Cleanup event reporter and all components."""
        logger.info("Cleaning up EventReporter")
        
        # Stop event queue
        await self.event_queue.stop()
        
        # Cleanup REST client
        await self.rest_client.cleanup()
        
        logger.info("EventReporter cleanup completed")


# Global instance - will be initialized by main application
event_reporter: Optional[EventReporter] = None


async def initialize_event_reporter(config: Dict[str, Any]) -> bool:
    """
    Initialize the global event reporter instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global event_reporter
    
    try:
        event_reporter = EventReporter(config)
        success = await event_reporter.initialize()
        
        if success:
            logger.info("Event reporter initialized successfully")
        else:
            logger.error("Event reporter initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize event reporter: {e}")
        return False


def get_event_reporter() -> Optional[EventReporter]:
    """
    Get the global event reporter instance.
    
    Returns:
        Optional[EventReporter]: Reporter instance or None if not initialized
    """
    return event_reporter