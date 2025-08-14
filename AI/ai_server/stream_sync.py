"""
Stream Sync Service for AI-Backend Integration

This module handles synchronization of discovered Korean ITS streams with the backend system.
When the AI discovers streams, it sends the stream information to the backend for storage
and frontend access.

Key Features:
- Sync discovered streams to backend CCTV repository
- Handle stream updates and status changes
- Error handling and retry mechanisms
- Compatible with existing backend CCTV API structure
"""

import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Configure logging
logger = logging.getLogger(__name__)


class StreamSyncService:
    """
    Service for syncing discovered Korean ITS streams to backend system.
    
    This service communicates with the Spring Boot backend to store stream information
    that can be used by both the AI system for monitoring and the frontend for display.
    """
    
    def __init__(self, backend_url: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize stream sync service.
        
        Args:
            backend_url: Base URL of the Spring Boot backend (e.g., "http://localhost:8080")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.backend_url = backend_url.rstrip('/')  # Remove trailing slash
        self.timeout = timeout
        self.max_retries = max_retries
        self.sync_endpoint = f"{self.backend_url}/api/cctvs/sync"
        
        logger.info(f"StreamSyncService initialized with backend URL: {self.backend_url}")
    
    def sync_discovered_streams(self, discovered_streams: List[Dict[str, Any]]) -> bool:
        """
        Send discovered Korean ITS streams to backend for storage.
        
        Args:
            discovered_streams: List of stream dictionaries from Korean ITS API
            
        Returns:
            bool: True if sync successful, False otherwise
            
        Expected stream format from AI discovery:
        {
            'id': 'its_cctv_001',
            'name': 'Main Street Intersection',
            'stream_url': 'http://...',
            'location': {
                'latitude': 37.5665,
                'longitude': 126.9780,
                'address': 'Seoul, South Korea'
            }
        }
        """
        if not discovered_streams:
            logger.warning("No streams to sync")
            return True
        
        try:
            # Convert AI stream format to backend StreamSyncDto format
            sync_data = self._convert_to_sync_format(discovered_streams)
            
            # Send sync request to backend
            success = self._send_sync_request(sync_data)
            
            if success:
                logger.info(f"Successfully synced {len(discovered_streams)} streams to backend")
                return True
            else:
                logger.error("Failed to sync streams to backend")
                return False
                
        except Exception as e:
            logger.error(f"Error during stream sync: {e}")
            return False
    
    def _convert_to_sync_format(self, discovered_streams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert AI discovery format to backend StreamSyncDto format.
        
        Args:
            discovered_streams: Streams from Korean ITS API discovery
            
        Returns:
            List of dictionaries compatible with backend StreamSyncDto
        """
        sync_data = []
        current_time = datetime.now().isoformat()
        
        for stream in discovered_streams:
            location_info = stream.get('location', {})
            
            sync_dto = {
                "streamId": stream.get('id', ''),
                "streamName": stream.get('name', ''),
                "streamUrl": stream.get('stream_url', ''),
                "location": location_info.get('address', '') or f"Lat: {location_info.get('latitude', 0)}, Lng: {location_info.get('longitude', 0)}",
                "latitude": float(location_info.get('latitude', 0.0)),
                "longitude": float(location_info.get('longitude', 0.0)),
                "streamSource": "korean_its_api",
                "active": True,
                "discoveredAt": current_time
            }
            
            sync_data.append(sync_dto)
            
            logger.debug(f"Converted stream {stream.get('id')} to sync format")
        
        return sync_data
    
    def _send_sync_request(self, sync_data: List[Dict[str, Any]]) -> bool:
        """
        Send sync request to backend with retry mechanism.
        
        Args:
            sync_data: List of StreamSyncDto compatible dictionaries
            
        Returns:
            bool: True if request successful, False otherwise
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Sending stream sync request (attempt {attempt + 1}/{self.max_retries})")
                logger.debug(f"Sync endpoint: {self.sync_endpoint}")
                logger.debug(f"Sync data: {json.dumps(sync_data, indent=2)}")
                
                response = requests.post(
                    self.sync_endpoint,
                    json=sync_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=self.timeout
                )
                
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response content: {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"Stream sync successful: {response_data.get('message', 'Unknown response')}")
                    logger.info(f"Synced count: {response_data.get('syncedCount', 'Unknown')}")
                    return True
                else:
                    error_msg = f"Backend returned status {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error to backend: {e}"
                logger.warning(error_msg)
                last_error = error_msg
                
            except requests.exceptions.Timeout as e:
                error_msg = f"Timeout error during sync: {e}"
                logger.warning(error_msg)
                last_error = error_msg
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Request error during sync: {e}"
                logger.warning(error_msg)
                last_error = error_msg
                
            except Exception as e:
                error_msg = f"Unexpected error during sync: {e}"
                logger.warning(error_msg)
                last_error = error_msg
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to sync streams after {self.max_retries} attempts. Last error: {last_error}")
        return False
    
    def test_backend_connection(self) -> bool:
        """
        Test connection to backend to ensure it's reachable.
        
        Returns:
            bool: True if backend is reachable, False otherwise
        """
        try:
            # Test with a simple GET request to the CCTVs endpoint
            test_url = f"{self.backend_url}/api/cctvs"
            response = requests.get(test_url, timeout=self.timeout)
            
            if response.status_code == 200:
                logger.info("Backend connection test successful")
                return True
            else:
                logger.warning(f"Backend returned status {response.status_code} during connection test")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to backend - connection refused")
            return False
            
        except requests.exceptions.Timeout:
            logger.error("Backend connection test timed out")
            return False
            
        except Exception as e:
            logger.error(f"Backend connection test failed: {e}")
            return False
    
    def get_backend_streams(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve currently stored streams from backend.
        
        Returns:
            List of stream dictionaries or None if failed
        """
        try:
            response = requests.get(
                f"{self.backend_url}/api/cctvs/active",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                streams = response.json()
                logger.info(f"Retrieved {len(streams)} active streams from backend")
                return streams
            else:
                logger.warning(f"Failed to get backend streams: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving backend streams: {e}")
            return None


# Example usage function for testing
def test_stream_sync():
    """Test function to verify stream sync functionality"""
    
    # Mock discovered streams data
    mock_streams = [
        {
            'id': 'its_cctv_001',
            'name': 'Test Stream 1',
            'stream_url': 'http://example.com/stream1.m3u8',
            'location': {
                'latitude': 37.5665,
                'longitude': 126.9780,
                'address': 'Seoul, South Korea'
            }
        },
        {
            'id': 'its_cctv_002', 
            'name': 'Test Stream 2',
            'stream_url': 'http://example.com/stream2.m3u8',
            'location': {
                'latitude': 37.5651,
                'longitude': 126.9895,
                'address': 'Gangnam, Seoul'
            }
        }
    ]
    
    # Initialize sync service
    sync_service = StreamSyncService("http://localhost:8080")
    
    # Test backend connection
    if not sync_service.test_backend_connection():
        logger.error("Backend not available for testing")
        return False
    
    # Test stream sync
    success = sync_service.sync_discovered_streams(mock_streams)
    
    if success:
        logger.info("Stream sync test completed successfully")
        
        # Test retrieving synced streams
        backend_streams = sync_service.get_backend_streams()
        if backend_streams:
            logger.info(f"Backend now has {len(backend_streams)} active streams")
            for stream in backend_streams:
                logger.info(f"  - {stream.get('streamId', 'N/A')}: {stream.get('streamName', 'N/A')}")
        
        return True
    else:
        logger.error("Stream sync test failed")
        return False


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    test_stream_sync()