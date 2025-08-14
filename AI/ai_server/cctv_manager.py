"""
CCTV Manager Module for Illegal Parking Detection System

This module handles the management and coordination of multiple CCTV streams,
supporting both local testing mode (frame sequences) and live API streaming.
It provides a unified interface for accessing video data regardless of source type.

Key Features:
- Multi-stream management with concurrent processing
- Dual mode support: local frame sequences vs live API streams
- Thread-safe stream access and resource management
- Korean filename support with proper UTF-8 encoding
- Frame rate control and buffering mechanisms
- Automatic reconnection for live streams

Architecture:
- CCTVStream: Individual stream handler (local or live)
- CCTVManager: Central coordinator for all streams
- Frame providers: Abstract interface for different source types
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
import requests
from urllib.parse import urljoin
import glob

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class StreamMetadata:
    """
    Metadata container for CCTV stream information.
    
    Contains all the necessary information to identify and process a CCTV stream,
    including location data, processing parameters, and stream configuration.
    """
    stream_id: str
    name: str
    location: Dict[str, Any]  # Contains latitude, longitude, address
    fps: int
    stream_type: str  # "local" or "live"
    source_path: str  # File path or API endpoint
    enabled: bool = True
    last_frame_time: float = 0.0
    frame_count: int = 0
    error_count: int = 0


class FrameProvider(ABC):
    """
    Abstract base class for different types of frame providers.
    
    This allows the CCTV manager to handle different video sources
    (local files, live streams, API endpoints) through a common interface.
    Supports both synchronous and asynchronous frame retrieval patterns.
    """
    
    def __init__(self, metadata: StreamMetadata):
        self.metadata = metadata
        self.is_active = False
        self.lock = threading.Lock()
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the frame provider. Returns True if successful."""
        pass
    
    @abstractmethod
    def get_next_frame(self) -> Optional[np.ndarray]:
        """Get the next frame. Returns None if no frame available or stream ended."""
        pass
    
    @abstractmethod
    def release(self):
        """Clean up resources when stream is no longer needed."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if more frames are available."""
        pass
    
    def get_current_timestamp(self) -> float:
        """Get current timestamp for frame timing."""
        return time.time()


class LocalFrameProvider(FrameProvider):
    """
    Frame provider for local video files or image sequences.
    
    Handles Korean filenames and supports both individual video files
    and directories containing frame sequences. Provides frame rate
    control to simulate real-time streaming from recorded data.
    """
    
    def __init__(self, metadata: StreamMetadata, base_path: str):
        super().__init__(metadata)
        self.base_path = Path(base_path)
        self.provider_mode: str = ""  # "video" or "images"
        
        # For image sequences
        self.frame_files: List[Path] = []
        self.current_frame_index = 0
        
        # For video files
        self.video_capture: Optional[cv2.VideoCapture] = None
        
        # Timing
        self.last_frame_time = 0.0
        self.frame_interval = 1.0 / metadata.fps if metadata.fps > 0 else 0.04
    
    def initialize(self) -> bool:
        """
        Initialize local frame provider by scanning for frame files.
        
        Supports Korean filenames and various image formats.
        Automatically detects if source is a video file or image sequence.
        
        Returns:
            bool: True if frames are found and accessible
        """
        try:
            source_path = self.base_path / self.metadata.source_path
            logger.info(f"Initializing local provider for: {source_path}")
            
            if source_path.is_file():
                # Single video file
                if source_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    self.video_capture = cv2.VideoCapture(str(source_path))
                    if not self.video_capture.isOpened():
                        logger.error(f"Failed to open video file: {source_path}")
                        return False
                    self.provider_mode = "video"
                    self.is_active = True
                    logger.info(f"Video file opened successfully: {source_path}")
                    return True
                else:
                    logger.error(f"Unsupported file format: {source_path}")
                    return False
            
            elif source_path.is_dir():
                # Image sequence directory
                self.provider_mode = "images"
                image_patterns = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
                self.frame_files = []
                
                for pattern in image_patterns:
                    matching_files = list(source_path.glob(pattern))
                    self.frame_files.extend(matching_files)
                
                self.frame_files.sort(key=lambda x: x.name)
                
                if not self.frame_files:
                    logger.error(f"No frame files found in directory: {source_path}")
                    return False
                
                logger.info(f"Found {len(self.frame_files)} frame files in {source_path}")
                
                if not self._test_frame_read():
                    return False
                
                self.is_active = True
                return True
            
            else:
                logger.error(f"Source path does not exist: {source_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize local provider: {e}")
            return False
    
    def _test_frame_read(self) -> bool:
        """
        Test reading the first frame to ensure file accessibility.
        """
        if not self.frame_files:
            return False
        
        try:
            first_frame_path = str(self.frame_files[0])
            test_frame = cv2.imread(first_frame_path, cv2.IMREAD_COLOR)
            
            if test_frame is None:
                logger.error(f"Cannot read frame file: {first_frame_path}")
                return False
            
            logger.info(f"Successfully tested frame reading. Frame shape: {test_frame.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Frame read test failed: {e}")
            return False
    
    def get_next_frame(self) -> Optional[np.ndarray]:
        """
        Get the next frame from the source with proper timing control.
        """
        if not self.is_active:
            return None

        # Frame rate control
        current_time = time.time()
        if (current_time - self.last_frame_time) < self.frame_interval:
            return None

        try:
            with self.lock:
                frame = None
                if self.provider_mode == "video":
                    if self.video_capture and self.video_capture.isOpened():
                        ret, frame = self.video_capture.read()
                        if not ret:
                            self.is_active = False
                            return None
                elif self.provider_mode == "images":
                    if self.current_frame_index < len(self.frame_files):
                        frame_path = str(self.frame_files[self.current_frame_index])
                        frame = cv2.imread(frame_path, cv2.IMREAD_COLOR)
                        if frame is None:
                            logger.warning(f"Failed to read frame: {frame_path}")
                            self.metadata.error_count += 1
                        self.current_frame_index += 1
                    else:
                        self.is_active = False
                        return None
                
                if frame is not None:
                    self.metadata.frame_count += 1
                    self.last_frame_time = current_time
                    self.metadata.last_frame_time = current_time
                    return frame
                else:
                    return None

        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            self.metadata.error_count += 1
            return None
    
    def is_available(self) -> bool:
        """Check if more frames are available."""
        if self.provider_mode == "video":
            return self.is_active and self.video_capture and self.video_capture.isOpened()
        elif self.provider_mode == "images":
            return self.is_active and self.current_frame_index < len(self.frame_files)
        return False
    
    def reset_sequence(self):
        """Reset to the beginning of the sequence."""
        with self.lock:
            self.last_frame_time = 0.0
            if self.provider_mode == "video" and self.video_capture:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.is_active = True
                logger.info(f"Reset video stream {self.metadata.stream_id}")
            elif self.provider_mode == "images":
                self.current_frame_index = 0
                self.is_active = True
                logger.info(f"Reset frame sequence for stream {self.metadata.stream_id}")
    
    def release(self):
        """Clean up local frame provider resources."""
        with self.lock:
            self.is_active = False
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
            self.frame_files.clear()
            logger.info(f"Released local frame provider for stream {self.metadata.stream_id}")


class LiveStreamProvider(FrameProvider):
    """
    Frame provider for live API streams or RTSP/HTTP video streams.
    
    Handles network connectivity, automatic reconnection, and buffering
    for real-time video streams. Supports Korean ITS API HLS/HTTP streams.
    """
    
    def __init__(self, metadata: StreamMetadata, api_config: Dict[str, Any] = None):
        super().__init__(metadata)
        self.api_config = api_config or {}
        
        # For Korean ITS API live streams - using OpenCV VideoCapture
        self.video_capture: Optional[cv2.VideoCapture] = None
        self.stream_url = metadata.source_path if hasattr(metadata, 'source_path') else ""
        
        # Legacy API session support (commented out for Korean ITS)
        # self.session: Optional[requests.Session] = None
        # self.stream_response: Optional[requests.Response] = None
        
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5.0  # seconds
        self.last_frame_time = 0.0
        self.frame_interval = 1.0 / metadata.fps if metadata.fps > 0 else 0.067  # ~15 FPS default
    
    def initialize(self) -> bool:
        """
        Initialize live stream connection using OpenCV for Korean ITS API streams.
        
        Sets up VideoCapture for HLS/HTTP streams from Korean ITS API.
        
        Returns:
            bool: True if connection established successfully
        """
        try:
            logger.info(f"Initializing live stream for: {self.metadata.stream_id}")
            
            # Get stream URL - for Korean ITS API, it's already the full stream URL
            if hasattr(self.metadata, 'stream_url'):
                stream_url = self.metadata.stream_url
            else:
                stream_url = self.metadata.source_path
            
            if not stream_url:
                logger.error(f"No stream URL provided for {self.metadata.stream_id}")
                return False
            
            logger.info(f"Opening live stream: {stream_url}")
            
            # Initialize OpenCV VideoCapture for live stream
            self.video_capture = cv2.VideoCapture(stream_url)
            
            # Set buffer size to reduce latency
            self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Set timeout for network streams (milliseconds)
            self.video_capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            self.video_capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
            if not self.video_capture.isOpened():
                logger.error(f"Failed to open live stream: {stream_url}")
                return False
            
            # Test frame read
            if not self._test_frame_read():
                return False
            
            self.is_active = True
            logger.info(f"Live stream initialized successfully: {stream_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize live stream: {e}")
            return False
    
    def _test_frame_read(self) -> bool:
        """
        Test reading a frame from the live stream to ensure it's working.
        
        Returns:
            bool: True if frame read successful
        """
        try:
            if not self.video_capture or not self.video_capture.isOpened():
                return False
            
            ret, frame = self.video_capture.read()
            if ret and frame is not None:
                logger.info(f"Live stream frame test successful. Frame shape: {frame.shape}")
                return True
            else:
                logger.error(f"Failed to read test frame from live stream")
                return False
                
        except Exception as e:
            logger.error(f"Live stream frame test error: {e}")
            return False
    
    def get_next_frame(self) -> Optional[np.ndarray]:
        """
        Get next frame from live stream.
        
        Handles network errors, buffering, and automatic reconnection.
        Decodes video frames from the live stream data.
        
        Returns:
            Optional[np.ndarray]: Next frame or None if unavailable
        """
        if not self.is_active or not self.video_capture:
            return None

        # Frame rate control
        current_time = time.time()
        if (current_time - self.last_frame_time) < self.frame_interval:
            return None

        try:
            with self.lock:
                if not self.video_capture.isOpened():
                    # Try to reconnect
                    if self._attempt_reconnect():
                        logger.info(f"Reconnected to live stream: {self.metadata.stream_id}")
                    else:
                        return None
                
                ret, frame = self.video_capture.read()
                if ret and frame is not None:
                    self.metadata.frame_count += 1
                    self.last_frame_time = current_time
                    self.metadata.last_frame_time = current_time
                    self.reconnect_attempts = 0  # Reset on successful read
                    return frame
                else:
                    # Failed to read frame, might be temporary network issue
                    logger.warning(f"Failed to read frame from live stream: {self.metadata.stream_id}")
                    if self._attempt_reconnect():
                        # Try reading again after reconnect
                        ret, frame = self.video_capture.read()
                        if ret and frame is not None:
                            return frame
                    return None

        except Exception as e:
            logger.error(f"Error reading frame from live stream {self.metadata.stream_id}: {e}")
            self.metadata.error_count += 1
            return None
    
    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to the live stream.
        
        Returns:
            bool: True if reconnection successful
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts reached for {self.metadata.stream_id}")
            self.is_active = False
            return False
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnect {self.reconnect_attempts}/{self.max_reconnect_attempts} for {self.metadata.stream_id}")
        
        # Release current capture
        if self.video_capture:
            self.video_capture.release()
        
        # Wait before reconnecting
        time.sleep(self.reconnect_delay)
        
        # Try to reinitialize
        return self.initialize()
    
    def is_available(self) -> bool:
        """Check if live stream is still available."""
        return self.is_active and self.video_capture is not None and self.video_capture.isOpened()
    
    def release(self):
        """Clean up live stream resources."""
        with self.lock:
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
            
            # Legacy API cleanup (commented out)
            # if self.stream_response:
            #     self.stream_response.close()
            #     self.stream_response = None
            # 
            # if self.session:
            #     self.session.close()
            #     self.session = None
            
            self.is_active = False
            logger.info(f"Released live stream provider for {self.metadata.stream_id}")


class CCTVStream:
    """
    Individual CCTV stream handler with unified interface.
    
    Wraps different frame providers (local/live) and provides a consistent
    interface for frame access, metadata management, and error handling.
    Handles threading and synchronization for concurrent access.
    """
    
    def __init__(self, metadata: StreamMetadata, provider: FrameProvider):
        self.metadata = metadata
        self.provider = provider
        self.lock = threading.Lock()
        self._initialized = False
        self._last_error: Optional[str] = None
    
    def initialize(self) -> bool:
        """
        Initialize the CCTV stream and its frame provider.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            with self.lock:
                if self._initialized:
                    return True
                
                logger.info(f"Initializing CCTV stream: {self.metadata.stream_id}")
                
                if self.provider.initialize():
                    self._initialized = True
                    self._last_error = None
                    logger.info(f"CCTV stream initialized: {self.metadata.stream_id}")
                    return True
                else:
                    self._last_error = "Provider initialization failed"
                    logger.error(f"Failed to initialize CCTV stream: {self.metadata.stream_id}")
                    return False
                    
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Exception during CCTV stream initialization: {e}")
            return False
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get next frame from the stream.
        
        Thread-safe frame retrieval with error handling and status reporting.
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: (success, frame)
        """
        if not self._initialized:
            return False, None
        
        try:
            frame = self.provider.get_next_frame()
            if frame is not None:
                return True, frame
            else:
                # Check if stream ended or just no frame available right now
                if not self.provider.is_available():
                    logger.info(f"Stream ended: {self.metadata.stream_id}")
                return False, None
                
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error getting frame from stream {self.metadata.stream_id}: {e}")
            return False, None
    
    def is_active(self) -> bool:
        """Check if stream is active and available."""
        return self._initialized and self.provider.is_available()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get stream statistics and status information.
        
        Returns:
            Dict containing stream stats, error counts, timing info
        """
        return {
            "stream_id": self.metadata.stream_id,
            "name": self.metadata.name,
            "type": self.metadata.stream_type,
            "initialized": self._initialized,
            "active": self.is_active(),
            "frame_count": self.metadata.frame_count,
            "error_count": self.metadata.error_count,
            "last_frame_time": self.metadata.last_frame_time,
            "last_error": self._last_error,
            "fps": self.metadata.fps,
            "location": self.metadata.location
        }
    
    def release(self):
        """Clean up stream resources."""
        with self.lock:
            if self.provider:
                self.provider.release()
            self._initialized = False
            logger.info(f"Released CCTV stream: {self.metadata.stream_id}")


class CCTVManager:
    """
    Central manager for all CCTV streams in the system.
    
    Coordinates multiple CCTV streams, handles configuration loading,
    and provides a unified interface for stream access and management.
    Supports concurrent stream processing and resource management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.streams: Dict[str, CCTVStream] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.lock = threading.Lock()
        logger.info("CCTV Manager initialized")
    
    def load_streams(self) -> bool:
        """
        Load and initialize all CCTV streams from configuration.
        
        Processes both local and live stream configurations,
        creates appropriate providers, and initializes all streams.
        
        Returns:
            bool: True if at least one stream was loaded successfully
        """
        try:
            streams_loaded = 0
            
            # Load local mode streams (commented out for Korean ITS API)
            # if self.config.get('cctv_streams', {}).get('local_mode', {}).get('enabled', False):
            #     local_config = self.config['cctv_streams']['local_mode']
            #     base_path = local_config['base_path']
            #     
            #     for stream_config in local_config['streams']:
            #         if self._load_local_stream(stream_config, base_path):
            #             streams_loaded += 1
            
            # Load live mode streams (commented out for Korean ITS API)
            # if self.config.get('cctv_streams', {}).get('live_mode', {}).get('enabled', False):
            #     live_config = self.config['cctv_streams']['live_mode']
            #     
            #     for stream_config in live_config['streams']:
            #         if self._load_live_stream(stream_config, live_config):
            #             streams_loaded += 1
            
            logger.info(f"CCTV Manager initialized for dynamic stream loading (Korean ITS API)")
            logger.info(f"Call load_streams_from_list() with stream configurations from monitoring service")
            return True  # Always return True for dynamic loading mode
            
        except Exception as e:
            logger.error(f"Failed to load CCTV streams: {e}")
            return False
    
    def load_streams_from_list(self, stream_configs: List[Dict[str, Any]]) -> bool:
        """
        Load streams from a list of stream configurations (Korean ITS API format).
        
        Args:
            stream_configs: List of stream configuration dictionaries from monitoring service
            
        Returns:
            bool: True if at least one stream was loaded successfully
        """
        try:
            streams_loaded = 0
            
            for stream_config in stream_configs:
                if self._load_dynamic_stream(stream_config):
                    streams_loaded += 1
            
            logger.info(f"Dynamically loaded {streams_loaded} CCTV streams successfully")
            return streams_loaded > 0
            
        except Exception as e:
            logger.error(f"Failed to load dynamic CCTV streams: {e}")
            return False
    
    def _load_local_stream(self, stream_config: Dict[str, Any], base_path: str) -> bool:
        """Load a single local stream configuration."""
        try:
            metadata = StreamMetadata(
                stream_id=stream_config['id'],
                name=stream_config['name'],
                location=stream_config['location'],
                fps=stream_config.get('fps', 10),
                stream_type='local',
                source_path=stream_config['path']
            )
            
            provider = LocalFrameProvider(metadata, base_path)
            stream = CCTVStream(metadata, provider)
            
            if stream.initialize():
                with self.lock:
                    self.streams[metadata.stream_id] = stream
                logger.info(f"Loaded local stream: {metadata.stream_id}")
                return True
            else:
                logger.error(f"Failed to initialize local stream: {metadata.stream_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading local stream: {e}")
            return False
    
    def _load_dynamic_stream(self, stream_config: Dict[str, Any]) -> bool:
        """Load a single stream configuration from Korean ITS API format."""
        try:
            # Create metadata from Korean ITS API format
            metadata = StreamMetadata(
                stream_id=stream_config['id'],
                name=stream_config['name'],
                location=stream_config['location'],
                fps=stream_config.get('fps', 15),
                stream_type=stream_config.get('source_type', 'live'),
                source_path=stream_config.get('stream_url', '')
            )
            
            # Add stream_url attribute for LiveStreamProvider
            metadata.stream_url = stream_config.get('stream_url', '')
            
            # Determine provider type based on source_type
            source_type = stream_config.get('source_type', 'live')
            
            if source_type in ['hls', 'http', 'rtsp', 'live']:
                # Live stream provider for Korean ITS API
                provider = LiveStreamProvider(metadata)
                stream = CCTVStream(metadata, provider)
            elif source_type == 'image_sequence':
                # Local frame provider (commented out streams)
                base_path = self.config.get('base_path', '')
                provider = LocalFrameProvider(metadata, base_path)
                stream = CCTVStream(metadata, provider)
            else:
                logger.error(f"Unsupported source type: {source_type}")
                return False
            
            if stream.initialize():
                with self.lock:
                    self.streams[metadata.stream_id] = stream
                logger.info(f"Loaded dynamic stream: {metadata.stream_id} ({source_type})")
                return True
            else:
                logger.error(f"Failed to initialize dynamic stream: {metadata.stream_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading dynamic stream: {e}")
            return False

    def _load_live_stream(self, stream_config: Dict[str, Any], live_config: Dict[str, Any]) -> bool:
        """Load a single live stream configuration."""
        try:
            metadata = StreamMetadata(
                stream_id=stream_config['id'],
                name=stream_config['name'],
                location=stream_config['location'],
                fps=stream_config.get('fps', 15),
                stream_type='live',
                source_path=stream_config['endpoint']
            )
            
            provider = LiveStreamProvider(metadata, live_config)
            stream = CCTVStream(metadata, provider)
            
            if stream.initialize():
                with self.lock:
                    self.streams[metadata.stream_id] = stream
                logger.info(f"Loaded live stream: {metadata.stream_id}")
                return True
            else:
                logger.error(f"Failed to initialize live stream: {metadata.stream_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading live stream: {e}")
            return False
    
    def get_stream(self, stream_id: str) -> Optional[CCTVStream]:
        """
        Get a specific CCTV stream by ID.
        
        Args:
            stream_id: Unique identifier for the stream
            
        Returns:
            Optional[CCTVStream]: Stream object or None if not found
        """
        with self.lock:
            return self.streams.get(stream_id)
    
    def get_all_streams(self) -> Dict[str, CCTVStream]:
        """Get all loaded CCTV streams."""
        with self.lock:
            return self.streams.copy()
    
    def get_active_streams(self) -> Dict[str, CCTVStream]:
        """Get only active CCTV streams."""
        with self.lock:
            return {sid: stream for sid, stream in self.streams.items() 
                   if stream.is_active()}
    
    def get_stream_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all streams.
        
        Returns:
            Dict mapping stream_id to stream statistics
        """
        stats = {}
        with self.lock:
            for stream_id, stream in self.streams.items():
                stats[stream_id] = stream.get_stats()
        return stats
    
    def release_all(self):
        """Release all streams and clean up resources."""
        with self.lock:
            for stream in self.streams.values():
                stream.release()
            self.streams.clear()
        
        self.executor.shutdown(wait=True)
        logger.info("CCTV Manager released all resources")


# Global instance - will be initialized by main application
cctv_manager: Optional[CCTVManager] = None


def initialize_cctv_manager(config: Dict[str, Any]) -> bool:
    """
    Initialize the global CCTV manager instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global cctv_manager
    
    try:
        cctv_manager = CCTVManager(config)
        success = cctv_manager.load_streams()
        
        if success:
            logger.info("CCTV Manager initialized successfully")
        else:
            logger.error("CCTV Manager initialization failed - no streams loaded")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize CCTV Manager: {e}")
        return False


def get_cctv_manager() -> Optional[CCTVManager]:
    """
    Get the global CCTV manager instance.
    
    Returns:
        Optional[CCTVManager]: Manager instance or None if not initialized
    """
    return cctv_manager