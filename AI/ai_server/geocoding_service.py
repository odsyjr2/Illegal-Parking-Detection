"""
VWorld Geocoding Service Module for Location Address Resolution

This module provides geocoding and reverse geocoding functionality using 
Korea's official VWorld Open API from the Ministry of Land, Infrastructure and Transport.

Key Features:
- Reverse geocoding: GPS coordinates → Korean road address
- Forward geocoding: Korean road address → GPS coordinates  
- Integration with VWorld Open API (40,000 requests/day limit)
- Address caching for performance optimization
- Error handling and fallback mechanisms
- Korean road address (도로명주소) specialized processing

Architecture:
- VWorldGeocodingService: Main service class using government API
- Coordinate validation for Korean territory
- Cached responses to reduce API calls
- Fallback to coordinate display on service failure
"""

import logging
import time
import requests
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from functools import lru_cache
import asyncio
import json
from urllib.parse import urlencode

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LocationInfo:
    """Container for location information with address and coordinates."""
    latitude: float
    longitude: float
    address: Optional[str] = None
    formatted_address: Optional[str] = None
    is_geocoded: bool = False
    error_message: Optional[str] = None


@dataclass
class VWorldApiResult:
    """Container for VWorld API response."""
    success: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    road_address: Optional[str] = None
    error_message: Optional[str] = None


class VWorldGeocodingService:
    """
    Service for converting GPS coordinates to Korean addresses using VWorld Open API.
    
    Provides both geocoding and reverse geocoding functionality with caching and error handling
    to enhance location information in AI violation reports using Korea's official API.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize VWorld geocoding service with configuration.
        
        Args:
            config: Configuration dictionary with VWorld API settings
        """
        self.config = config or {}
        
        # VWorld API configuration
        self.base_url = self.config.get('base_url', 'https://api.vworld.kr/req/address')
        self.api_key = self.config.get('api_key', '')
        self.timeout = self.config.get('timeout', 10.0)
        self.cache_size = self.config.get('cache_size', 1000)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        
        # Request session for connection pooling
        self.session = requests.Session()
        
        if not self.api_key:
            logger.warning("VWorld API key not provided. Service will use fallback mode.")
        else:
            logger.info("VWorld geocoding service initialized with official API")
        
        # Validate API key on initialization
        self._validate_api_key()
    
    def is_available(self) -> bool:
        """Check if VWorld geocoding service is available."""
        return bool(self.api_key)
    
    def _validate_api_key(self) -> bool:
        """
        Validate VWorld API key by making a test request.
        
        Returns:
            bool: True if API key is valid
        """
        if not self.api_key:
            return False
            
        try:
            # Test with Seoul City Hall coordinates
            result = self._reverse_geocode_api(37.566535, 126.977969)
            return result.success
        except Exception as e:
            logger.warning(f"VWorld API key validation failed: {e}")
            return False
    
    def _reverse_geocode_api(self, latitude: float, longitude: float, address_type: str = 'ROAD') -> VWorldApiResult:
        """
        Call VWorld reverse geocoding API.
        
        Args:
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            
        Returns:
            VWorldApiResult: API response result
        """
        params = {
            'service': 'address',
            'request': 'getAddress',
            'version': '2.0',
            'crs': 'epsg:4326',
            'point': f"{longitude},{latitude}",
            'format': 'json',
            'type': address_type,  # 'ROAD' for 도로명주소, 'PARCEL' for 지번주소
            'key': self.api_key
        }
        
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # VWorld API response parsing
            if (data.get('response', {}).get('status') == 'OK' and 
                data.get('response', {}).get('result') and
                len(data['response']['result']) > 0):
                
                result = data['response']['result'][0]
                road_address = result.get('text', '')
                
                return VWorldApiResult(
                    success=True,
                    latitude=latitude,
                    longitude=longitude,
                    road_address=road_address
                )
            else:
                error_msg = data.get('response', {}).get('status', 'Unknown error')
                return VWorldApiResult(
                    success=False,
                    error_message=f"VWorld API error: {error_msg}"
                )
                
        except requests.RequestException as e:
            return VWorldApiResult(
                success=False,
                error_message=f"HTTP request failed: {e}"
            )
        except (ValueError, KeyError) as e:
            return VWorldApiResult(
                success=False,
                error_message=f"Response parsing failed: {e}"
            )

    def _geocode_api(self, road_address: str) -> VWorldApiResult:
        """
        Call VWorld geocoding API.
        
        Args:
            road_address: Korean road address string
            
        Returns:
            VWorldApiResult: API response result
        """
        params = {
            'service': 'address',
            'request': 'getcoord',
            'version': '2.0',
            'crs': 'epsg:4326',
            'address': road_address,
            'format': 'json',
            'type': 'ROAD',  # 도로명 주소만 처리
            'key': self.api_key
        }
        
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # VWorld API response parsing
            if (data.get('response', {}).get('status') == 'OK' and 
                data.get('response', {}).get('result') and
                data['response']['result'].get('point')):
                
                point = data['response']['result']['point']
                longitude = float(point['x'])
                latitude = float(point['y'])
                refined_address = data['response']['result'].get('text', road_address)
                
                return VWorldApiResult(
                    success=True,
                    latitude=latitude,
                    longitude=longitude,
                    road_address=refined_address
                )
            else:
                error_msg = data.get('response', {}).get('status', 'Unknown error')
                return VWorldApiResult(
                    success=False,
                    error_message=f"VWorld geocoding error: {error_msg}"
                )
                
        except requests.RequestException as e:
            return VWorldApiResult(
                success=False,
                error_message=f"HTTP request failed: {e}"
            )
        except (ValueError, KeyError) as e:
            return VWorldApiResult(
                success=False,
                error_message=f"Response parsing failed: {e}"
            )

    @lru_cache(maxsize=1000)
    def reverse_geocode(self, latitude: float, longitude: float) -> LocationInfo:
        """
        Convert GPS coordinates to Korean road address using VWorld API.
        
        Args:
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            
        Returns:
            LocationInfo: Object containing coordinates and address information
        """
        # Validate coordinates
        if not self._validate_coordinates(latitude, longitude):
            error_msg = f"Invalid coordinates: lat={latitude}, lon={longitude}"
            logger.error(error_msg)
            return LocationInfo(
                latitude=latitude,
                longitude=longitude,
                error_message=error_msg
            )
        
        # Check if VWorld service is available
        if not self.is_available():
            return self._fallback_location_info(latitude, longitude, "VWorld API not available")
        
        # Try road address first, then fallback to parcel address
        for address_type in ['ROAD', 'PARCEL']:
            for attempt in range(self.retry_attempts + 1):
                try:
                    logger.debug(f"VWorld {address_type} geocoding attempt {attempt + 1} for coordinates: {latitude}, {longitude}")
                    
                    # Call VWorld reverse geocoding API with specific type
                    api_result = self._reverse_geocode_api(latitude, longitude, address_type)
                    
                    if api_result.success:
                        formatted_address = self._format_korean_address(api_result.road_address)
                        
                        result = LocationInfo(
                            latitude=latitude,
                            longitude=longitude,
                            address=api_result.road_address,
                            formatted_address=formatted_address,
                            is_geocoded=True
                        )
                        
                        logger.debug(f"VWorld geocoding successful ({address_type}): {formatted_address}")
                        return result
                    else:
                        logger.debug(f"VWorld {address_type} API failed (attempt {attempt + 1}): {api_result.error_message}")
                        if attempt < self.retry_attempts:
                            time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            break
                    
                except Exception as e:
                    logger.error(f"Unexpected VWorld API error: {e}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        break
        
        # Return fallback information if geocoding failed
        return self._fallback_location_info(latitude, longitude, "VWorld reverse geocoding failed after retries")
    
    async def reverse_geocode_async(self, latitude: float, longitude: float) -> LocationInfo:
        """
        Async version of reverse geocoding.
        
        Args:
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            
        Returns:
            LocationInfo: Object containing coordinates and address information
        """
        # Run synchronous geocoding in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.reverse_geocode, latitude, longitude)
    
    def _validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate GPS coordinates.
        
        Args:
            latitude: Latitude value to validate
            longitude: Longitude value to validate
            
        Returns:
            bool: True if coordinates are valid
        """
        # Check latitude range
        if not (-90.0 <= latitude <= 90.0):
            return False
        
        # Check longitude range
        if not (-180.0 <= longitude <= 180.0):
            return False
        
        # Check for Korean region (approximate bounds)
        # Korea is roughly between 33-39N latitude and 124-132E longitude
        korea_bounds = {
            'min_lat': 32.0, 'max_lat': 40.0,
            'min_lon': 123.0, 'max_lon': 133.0
        }
        
        if not (korea_bounds['min_lat'] <= latitude <= korea_bounds['max_lat'] and
                korea_bounds['min_lon'] <= longitude <= korea_bounds['max_lon']):
            logger.warning(f"Coordinates outside Korea region: {latitude}, {longitude}")
            # Don't fail validation, just warn
        
        return True
    
    def _format_korean_address(self, raw_address: str) -> str:
        """
        Format VWorld API address into clean Korean format.
        
        Args:
            raw_address: Raw address string from VWorld API (road or parcel)
            
        Returns:
            str: Formatted Korean address
        """
        if not raw_address:
            return ""
        
        # VWorld API returns clean addresses (road or parcel)
        # Just remove extra whitespace
        formatted_address = ' '.join(raw_address.split())
        
        return formatted_address
    
    def _fallback_location_info(self, latitude: float, longitude: float, reason: str) -> LocationInfo:
        """
        Create fallback location info when geocoding fails.
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            reason: Reason for fallback
            
        Returns:
            LocationInfo: Fallback location information
        """
        # Create coordinate-based location description
        formatted_address = f"좌표: {latitude:.6f}, {longitude:.6f}"
        
        return LocationInfo(
            latitude=latitude,
            longitude=longitude,
            formatted_address=formatted_address,
            is_geocoded=False,
            error_message=reason
        )
    
    def geocode(self, road_address: str) -> LocationInfo:
        """
        Convert Korean road address to GPS coordinates using VWorld API.
        
        Args:
            road_address: Korean road address string
            
        Returns:
            LocationInfo: Object containing coordinates and address information
        """
        if not road_address or not road_address.strip():
            return LocationInfo(
                latitude=0.0,
                longitude=0.0,
                error_message="Empty address provided"
            )
        
        # Check if VWorld service is available
        if not self.is_available():
            return LocationInfo(
                latitude=0.0,
                longitude=0.0,
                error_message="VWorld API not available"
            )
        
        # Perform geocoding with retries
        for attempt in range(self.retry_attempts + 1):
            try:
                logger.debug(f"VWorld geocoding attempt {attempt + 1} for address: {road_address}")
                
                # Call VWorld geocoding API
                api_result = self._geocode_api(road_address)
                
                if api_result.success:
                    formatted_address = self._format_korean_address(api_result.road_address)
                    
                    result = LocationInfo(
                        latitude=api_result.latitude,
                        longitude=api_result.longitude,
                        address=api_result.road_address,
                        formatted_address=formatted_address,
                        is_geocoded=True
                    )
                    
                    logger.debug(f"VWorld geocoding successful: {formatted_address} -> ({api_result.latitude}, {api_result.longitude})")
                    return result
                else:
                    logger.warning(f"VWorld geocoding failed (attempt {attempt + 1}): {api_result.error_message}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        break
                    
            except Exception as e:
                logger.error(f"Unexpected VWorld geocoding error: {e}")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break
        
        # Return error result if geocoding failed
        return LocationInfo(
            latitude=0.0,
            longitude=0.0,
            error_message="VWorld geocoding failed after retries"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get VWorld geocoding service statistics."""
        cache_info = self.reverse_geocode.cache_info()
        
        return {
            "vworld_api_available": self.is_available(),
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_max_size": cache_info.maxsize,
            "configuration": {
                "base_url": self.base_url,
                "timeout": self.timeout,
                "retry_attempts": self.retry_attempts,
                "api_key_configured": bool(self.api_key)
            }
        }
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        self.reverse_geocode.cache_clear()
        logger.info("Geocoding cache cleared")


# Global instance for use in other modules
_geocoding_service: Optional[VWorldGeocodingService] = None


def initialize_geocoding_service(config: Dict[str, Any] = None) -> bool:
    """
    Initialize the global VWorld geocoding service instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global _geocoding_service
    
    try:
        _geocoding_service = VWorldGeocodingService(config)
        logger.info("VWorld geocoding service initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize VWorld geocoding service: {e}")
        return False


def get_geocoding_service() -> Optional[VWorldGeocodingService]:
    """
    Get the global VWorld geocoding service instance.
    
    Returns:
        Optional[VWorldGeocodingService]: Service instance or None if not initialized
    """
    return _geocoding_service


# Convenience functions for direct use
def reverse_geocode_coordinates(latitude: float, longitude: float) -> LocationInfo:
    """
    Convenience function for VWorld reverse geocoding.
    
    Args:
        latitude: GPS latitude
        longitude: GPS longitude
        
    Returns:
        LocationInfo: Location information with road address
    """
    service = get_geocoding_service()
    if service:
        return service.reverse_geocode(latitude, longitude)
    else:
        logger.warning("VWorld geocoding service not initialized")
        return LocationInfo(
            latitude=latitude,
            longitude=longitude,
            formatted_address=f"좌표: {latitude:.6f}, {longitude:.6f}",
            error_message="VWorld geocoding service not initialized"
        )


def geocode_road_address(road_address: str) -> LocationInfo:
    """
    Convenience function for VWorld geocoding.
    
    Args:
        road_address: Korean road address
        
    Returns:
        LocationInfo: Location information with coordinates
    """
    service = get_geocoding_service()
    if service:
        return service.geocode(road_address)
    else:
        logger.warning("VWorld geocoding service not initialized")
        return LocationInfo(
            latitude=0.0,
            longitude=0.0,
            error_message="VWorld geocoding service not initialized"
        )


async def reverse_geocode_coordinates_async(latitude: float, longitude: float) -> LocationInfo:
    """
    Async convenience function for VWorld reverse geocoding.
    
    Args:
        latitude: GPS latitude
        longitude: GPS longitude
        
    Returns:
        LocationInfo: Location information with road address
    """
    service = get_geocoding_service()
    if service:
        return await service.reverse_geocode_async(latitude, longitude)
    else:
        logger.warning("VWorld geocoding service not initialized")
        return LocationInfo(
            latitude=latitude,
            longitude=longitude,
            formatted_address=f"좌표: {latitude:.6f}, {longitude:.6f}",
            error_message="VWorld geocoding service not initialized"
        )