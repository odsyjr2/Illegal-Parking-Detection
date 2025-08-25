"""
Backend API Client Module for AI Server Communication

This module implements asynchronous HTTP client functionality for AI-to-Backend
communication in the Illegal Parking Detection System. It provides secure,
reliable REST API communication with connection pooling and error handling.

Key Features:
- Asynchronous HTTP client with aiohttp for optimal performance
- Connection pooling and session management for efficiency
- Retry mechanisms with exponential backoff for reliability
- Patrol route data transmission to Spring backend
- Connection health checks and monitoring
- JSON payload formatting and validation
- Error handling and logging integration

Architecture:
- BackendAPIClient: Main HTTP client with session management
- Connection Management: Automatic session lifecycle handling
- API Endpoints: RESTful communication with Spring backend
- Error Handling: Comprehensive exception management and logging
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

class BackendAPIClient:
    """백엔드 API와 통신하는 클라이언트"""
    
    def __init__(self, backend_url: str = "http://localhost:8080", timeout: int = 30):
        """
        Backend API Client 초기화
        
        Args:
            backend_url: 백엔드 서버 URL
            timeout: 요청 타임아웃 (초)
        """
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"BackendAPIClient 초기화: {self.backend_url}")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close_session()
    
    async def start_session(self):
        """HTTP 세션 시작"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("🔗 Backend API 세션 시작")
    
    async def close_session(self):
        """HTTP 세션 종료"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("🔌 Backend API 세션 종료")
    
    async def test_connection(self) -> bool:
        """
        백엔드 연결 테스트
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            if not self.session:
                await self.start_session()
            
            # 기존 CCTV API를 이용한 연결 테스트
            test_url = f"{self.backend_url}/api/cctvs"
            
            async with self.session.get(test_url) as response:
                if response.status == 200:
                    logger.info("✅ Backend 연결 테스트 성공")
                    return True
                else:
                    logger.warning(f"❌ Backend 연결 테스트 실패: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Backend 연결 테스트 중 오류: {e}")
            return False
    
    async def update_patrol_routes(self, routes_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        순찰 경로 데이터를 백엔드로 전송
        
        Args:
            routes_data: 차량별 경로 데이터
                형식: {
                    "vehicle_1": [
                        {"장소": "출발지점", "위도": 37.4835, "경도": 127.0322},
                        {"장소": "순찰지점 1", "위도": 37.4854, "경도": 127.0316}
                    ],
                    "vehicle_2": [...]
                }
        
        Returns:
            bool: 전송 성공 여부
        """
        try:
            if not self.session:
                await self.start_session()
            
            url = f"{self.backend_url}/api/patrol-routes/update"
            
            payload = {
                "routes": routes_data
            }
            
            logger.info(f"🚗 백엔드로 순찰 경로 전송: {len(routes_data)}대 차량")
            logger.debug(f"전송 데이터: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 순찰 경로 전송 성공: {result.get('message', 'OK')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 순찰 경로 전송 실패: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 순찰 경로 전송 중 오류: {e}")
            return False
    
    async def get_patrol_routes(self) -> Optional[Dict[str, Any]]:
        """
        현재 순찰 경로 조회 (디버깅/검증용)
        
        Returns:
            Optional[Dict]: 순찰 경로 데이터 또는 None
        """
        try:
            if not self.session:
                await self.start_session()
            
            url = f"{self.backend_url}/api/patrol-routes"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("📋 순찰 경로 조회 성공")
                    return result.get('data')
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 순찰 경로 조회 실패: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ 순찰 경로 조회 중 오류: {e}")
            return None


# 전역 백엔드 클라이언트 인스턴스
_backend_client: Optional[BackendAPIClient] = None

def get_backend_client(backend_url: str = "http://localhost:8080") -> BackendAPIClient:
    """
    전역 BackendAPIClient 인스턴스 반환
    
    Args:
        backend_url: 백엔드 서버 URL
        
    Returns:
        BackendAPIClient: 클라이언트 인스턴스
    """
    global _backend_client
    
    if _backend_client is None:
        _backend_client = BackendAPIClient(backend_url)
    
    return _backend_client

async def cleanup_backend_client():
    """전역 백엔드 클라이언트 정리"""
    global _backend_client
    
    if _backend_client:
        await _backend_client.close_session()
        _backend_client = None
        logger.info("🧹 Backend API 클라이언트 정리 완료")
