"""
PathFinding Service Module for Illegal Parking Detection System

This module implements automated patrol route optimization and backend integration.
It performs Vehicle Routing Problem (VRP) optimization based on violation density analysis
and delivers optimized routes to the Spring backend via REST API.

Key Features:
- Automated patrol route optimization using Google OR-Tools VRP solver
- Real-time violation data analysis with KDE (Kernel Density Estimation)
- OpenStreetMap (OSM) road network integration via OSMnx
- Asynchronous backend API communication for route delivery
- Configurable scheduling with automatic route updates
- Location name mapping from violation data CSV

Architecture:
- PathFindingService: Main service coordinator with scheduling
- VRP Solver: Multi-vehicle route optimization with clustering
- Location Mapper: Real location name extraction from violation data
- Backend Client: Asynchronous REST API communication
"""

import asyncio
import logging
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from backend_api_client import get_backend_client

# PathFinding 설정은 main.py에서 직접 전달

# PathFinding core functions import
from pathfinding_core import (
    run_clustered_vrp,
    load_and_project_graph,
    load_and_project_violations,
    fit_kde,
    map_density_to_nodes,
    select_top_nodes_with_spacing,
    compute_distance_matrix,
    compute_penalties,
    solve_vrp,
    extract_vehicle_routes,
    visualize_clustered_routes
)

logger = logging.getLogger("pathfinding_service")


def load_violation_data():
    """원본 위반 데이터에서 위치정보를 로드"""
    try:
        csv_path = Path(__file__).parent.parent / "Data" / "CCTV기반단속개별건수.csv"
        df = pd.read_csv(csv_path, encoding='cp949')
        
        # 필요한 컬럼만 추출: 위도, 경도, 위치정보
        location_data = df[['위도', '경도', '위치정보']].dropna()
        logger.info(f"위반 데이터 로드 완료: {len(location_data)}개 위치")
        return location_data
    except Exception as e:
        logger.error(f"위반 데이터 로드 실패: {e}")
        return None


def find_nearest_location_name(lat: float, lon: float, violation_data: pd.DataFrame) -> str:
    """주어진 좌표에서 가장 가까운 위치정보 찾기"""
    try:
        # 거리 계산 (단순 유클리드 거리)
        distances = np.sqrt(
            (violation_data['위도'] - lat) ** 2 + 
            (violation_data['경도'] - lon) ** 2
        )
        
        # 가장 가까운 위치 찾기
        nearest_idx = distances.idxmin()
        nearest_location = violation_data.loc[nearest_idx, '위치정보']
        
        # 거리 확인 (너무 먼 경우 기본값 반환)
        min_distance = distances.min()
        if min_distance > 0.01:  # 약 1km 이상 차이나면
            return f"좌표({lat:.4f}, {lon:.4f})"
        
        return str(nearest_location)
    except Exception as e:
        logger.warning(f"위치명 찾기 실패: {e}")
        return f"좌표({lat:.4f}, {lon:.4f})"


class PathFindingService:
    """경로 최적화 서비스 클래스"""
    
    def __init__(self, **config):
        """
        PathFinding 서비스 초기화
        
        Args:
            **config: PathFinding 설정 딕셔너리
        """
        # 기본 설정값
        self.place_name = config.get('place_name', "Seocho-gu, Seoul, South Korea")
        self.csv_path = config.get('violation_data_path', "../Data/CCTV기반단속개별건수.csv")
        self.num_vehicles = config.get('num_vehicles', 3)
        self.coverage_ratio = config.get('coverage_ratio', 0.7)
        self.min_nodes = config.get('min_nodes', 50)
        self.penalty_factor = config.get('penalty_factor', 5.0)
        self.min_spacing = config.get('min_spacing', 500.0)
        self.time_limit = config.get('time_limit', 120)
        self.update_interval_minutes = config.get('update_interval_minutes', 1)
        self.start_lat = config.get('start_latitude', 37.4835)
        self.start_lon = config.get('start_longitude', 127.0322)
        
        # 상태 관리
        self.last_update = None
        self.current_routes = {}
        self.is_running = False
        
        # 위반 데이터 로드
        self.violation_data = load_violation_data()
        
        logger.info("PathFinding Service 초기화 완료")
        logger.info(f"  📍 지역: {self.place_name}")
        logger.info(f"  🚗 차량 수: {self.num_vehicles}대")
        logger.info(f"  ⏰ 업데이트 주기: {self.update_interval_minutes}분")
        logger.info(f"  📊 최소 노드: {self.min_nodes}개")
    
    async def generate_patrol_routes(self) -> Tuple[Dict[int, List], str]:
        """
        순찰 경로 생성 (비동기)
        
        Returns:
            Tuple[Dict[int, List], str]: (경로 딕셔너리, 지도 파일 경로)
        """
        try:
            logger.info("🗺️ 순찰 경로 최적화 시작...")
            start_time = time.time()
            
            # PathFinding_Final.py의 run_clustered_vrp 함수 호출
            routes, map_file, G0 = await asyncio.get_event_loop().run_in_executor(
                None,  # ThreadPoolExecutor 사용
                self._run_pathfinding_sync
            )
            
            elapsed_time = time.time() - start_time
            
            if routes and G0 is not None:
                self.current_routes = routes
                self.last_update = datetime.now()
                
                # 결과 로깅
                logger.info(f"✅ 경로 최적화 완료 (소요시간: {elapsed_time:.1f}초)")
                logger.info(f"📊 생성된 경로 정보:")
                
                for vehicle_id, route in routes.items():
                    logger.info(f"  🚗 차량 {vehicle_id + 1}: {len(route)}개 노드")
                    if route:
                        logger.info(f"     경로: {route[:3]}{'...' if len(route) > 3 else ''}")
                
                logger.info(f"🗺️ 지도 파일 저장: {map_file}")
                
                # 백엔드 API로 경로 데이터 전송
                api_success = await self.send_routes_to_backend(G0)
                if api_success:
                    logger.info("📡 백엔드 API 전송 완료")
                else:
                    logger.warning("📡 백엔드 API 전송 실패")
                
                return routes, map_file
            else:
                logger.error("❌ 경로 최적화 실패 - 빈 결과")
                return {}, ""
                
        except Exception as e:
            logger.error(f"❌ 경로 최적화 중 오류 발생: {e}")
            return {}, ""
    
    def _run_pathfinding_sync(self) -> Tuple[Dict[int, List], str, Any]:
        """
        동기식 경로 최적화 실행 (스레드 풀에서 실행)
        """
        try:
            routes, map_file, G0 = run_clustered_vrp(
                place_name=self.place_name,
                csv_path=self.csv_path,
                num_vehicles=self.num_vehicles,
                coverage_ratio=self.coverage_ratio,
                min_nodes=self.min_nodes,
                penalty_factor=self.penalty_factor,
                min_spacing=self.min_spacing,
                time_limit=self.time_limit,
                start_lat=self.start_lat,
                start_lon=self.start_lon
            )
            return routes, map_file, G0
            
        except Exception as e:
            logger.error(f"동기식 경로 최적화 실행 오류: {e}")
            return {}, "", None
    
    async def start_scheduler(self) -> None:
        """
        경로 최적화 스케줄러 시작 (1분마다 테스트용, 나중에 1시간으로 변경)
        """
        logger.info(f"📅 경로 최적화 스케줄러 시작 ({self.update_interval_minutes}분 간격) - 테스트 모드")
        self.is_running = True
        
        # 첫 번째 실행
        await self.generate_patrol_routes()
        
        while self.is_running:
            try:
                # 다음 업데이트까지 대기
                logger.info(f"⏰ 다음 경로 최적화까지 {self.update_interval_minutes}분 대기 중...")
                await asyncio.sleep(self.update_interval_minutes * 60)  # 분을 초로 변환
                
                if self.is_running:
                    logger.info(f"🔄 {self.update_interval_minutes}분 경과 - 경로 재최적화 시작")
                    await self.generate_patrol_routes()
                    
            except asyncio.CancelledError:
                logger.info("📅 경로 최적화 스케줄러 취소됨")
                break
            except Exception as e:
                logger.error(f"❌ 스케줄러 오류: {e}")
                # 오류 발생 시 5분 후 재시도
                await asyncio.sleep(300)
    
    def stop_scheduler(self) -> None:
        """스케줄러 중지"""
        logger.info("🛑 경로 최적화 스케줄러 중지")
        self.is_running = False
    
    def get_current_routes(self) -> Dict[int, List]:
        """현재 경로 반환"""
        return self.current_routes.copy()
    
    def get_route_summary(self) -> Dict[str, Any]:
        """경로 요약 정보 반환"""
        if not self.current_routes:
            return {
                'status': 'no_routes',
                'last_update': None,
                'vehicle_count': 0,
                'total_nodes': 0
            }
        
        total_nodes = sum(len(route) for route in self.current_routes.values())
        
        return {
            'status': 'active',
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'vehicle_count': len(self.current_routes),
            'total_nodes': total_nodes,
            'routes': {
                f'vehicle_{i+1}': {
                    'node_count': len(route),
                    'first_nodes': route[:3] if route else []
                }
                for i, route in self.current_routes.items()
            }
        }
    
    def log_current_routes(self) -> None:
        """현재 경로를 상세하게 로그로 출력"""
        if not self.current_routes:
            logger.warning("📍 현재 활성화된 순찰 경로가 없습니다")
            return
        
        logger.info("=" * 60)
        logger.info("📍 현재 순찰 경로 정보")
        logger.info("=" * 60)
        logger.info(f"🕐 마지막 업데이트: {self.last_update.strftime('%Y-%m-%d %H:%M:%S') if self.last_update else 'N/A'}")
        logger.info(f"🚗 총 차량 수: {len(self.current_routes)}")
        
        total_nodes = 0
        for vehicle_id, route in self.current_routes.items():
            logger.info(f"")
            logger.info(f"🚗 차량 {vehicle_id + 1}:")
            logger.info(f"   📍 총 방문 지점: {len(route)}개")
            
            if route:
                logger.info(f"   🛣️  경로 시작: 노드 {route[0]}")
                if len(route) > 1:
                    logger.info(f"   🏁 경로 종료: 노드 {route[-1]}")
                
                # 중간 경로 표시 (처음 5개만)
                if len(route) > 2:
                    middle_routes = route[1:-1][:5]
                    logger.info(f"   🛤️  중간 경로: {middle_routes}{'...' if len(middle_routes) >= 5 else ''}")
            
            total_nodes += len(route)
        
        logger.info(f"")
        logger.info(f"📊 전체 통계:")
        logger.info(f"   총 순찰 지점: {total_nodes}개")
        logger.info(f"   평균 지점/차량: {total_nodes / len(self.current_routes):.1f}개")
        logger.info("=" * 60)

    async def send_routes_to_backend(self, G0: nx.MultiDiGraph) -> bool:
        """
        현재 경로를 백엔드 API로 전송
        
        Args:
            G0: 원본 OSM 그래프 (WGS84 좌표계)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not self.current_routes:
                logger.warning("전송할 경로가 없습니다")
                return False
            
            # 백엔드로 전송할 데이터 구성
            routes_data = {}
            
            for vehicle_id, route in self.current_routes.items():
                if not route:
                    continue
                    
                # 경로 데이터를 위도/경도로 변환
                route_points = []
                for i, node_id in enumerate(route):
                    try:
                        # OSM 그래프에서 노드의 위도/경도 추출
                        lat = G0.nodes[node_id]['y']
                        lon = G0.nodes[node_id]['x']
                        
                        # 실제 위치정보 찾기
                        if i == 0:
                            place_name = "출발지점"
                        elif i == len(route) - 1:
                            place_name = "복귀지점"  
                        else:
                            # 원본 CSV 데이터에서 가장 가까운 위치정보 찾기
                            if self.violation_data is not None:
                                place_name = find_nearest_location_name(lat, lon, self.violation_data)
                            else:
                                place_name = f"순찰지점 {i}"
                            
                        route_points.append({
                            '장소': place_name,
                            '위도': round(lat, 6),
                            '경도': round(lon, 6)
                        })
                        
                    except KeyError:
                        logger.warning(f"노드 {node_id}의 좌표 정보를 찾을 수 없습니다")
                        continue
                
                # 차량별 경로 데이터 저장
                if route_points:
                    routes_data[f"vehicle_{vehicle_id + 1}"] = route_points
                    logger.info(f"✅ 차량 {vehicle_id + 1} 경로 준비: {len(route_points)}개 지점")
                else:
                    logger.warning(f"차량 {vehicle_id + 1}의 유효한 경로 데이터가 없습니다")
            
            if not routes_data:
                logger.warning("전송할 유효한 경로 데이터가 없습니다")
                return False
            
            # 백엔드 API 클라이언트를 통해 전송 (기존 main.py 방식과 동일한 URL 사용)
            backend_url = "http://localhost:8080"  # 기존 event_reporter와 동일한 URL
            backend_client = get_backend_client(backend_url)
            
            # 연결 테스트
            connection_ok = await backend_client.test_connection()
            if not connection_ok:
                logger.error("백엔드 연결 실패")
                return False
            
            # 경로 데이터 전송
            success = await backend_client.update_patrol_routes(routes_data)
            
            if success:
                logger.info("🚀 백엔드로 순찰 경로 전송 완료")
                logger.info(f"   📊 총 {len(routes_data)}대 차량, {sum(len(r) for r in routes_data.values())}개 지점")
                return True
            else:
                logger.error("백엔드 API 호출 실패")
                return False
            
        except Exception as e:
            logger.error(f"백엔드 API 전송 중 오류: {e}")
            return False


# 전역 PathFinding 서비스 인스턴스
_pathfinding_service: Optional[PathFindingService] = None


def initialize_pathfinding_service(**config) -> PathFindingService:
    """
    PathFinding 서비스 초기화 (전역)
    
    Args:
        **config: PathFinding 설정 딕셔너리
        
    Returns:
        PathFindingService: 초기화된 서비스 인스턴스
    """
    global _pathfinding_service
    _pathfinding_service = PathFindingService(**config)
    return _pathfinding_service


def get_pathfinding_service() -> Optional[PathFindingService]:
    """
    전역 PathFinding 서비스 인스턴스 반환
    
    Returns:
        Optional[PathFindingService]: 서비스 인스턴스 또는 None
    """
    return _pathfinding_service
