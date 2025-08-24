"""
PathFinding Service for Illegal Parking Detection System
경로 최적화 서비스 - 1시간마다 순찰 경로 최적화 실행

Author: AI Development Team
Date: 2024-12-19
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import sys
from pathlib import Path

# PathFinding 설정은 main.py에서 직접 전달

# PathFinding_Final.py의 함수들을 import
try:
    from PathFinding_Final import (
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
except ImportError:
    # 현재 디렉토리에서 직접 import 시도
    from pathlib import Path
    import sys
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.append(str(current_dir))
    
    from PathFinding_Final import (
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
            routes, map_file = await asyncio.get_event_loop().run_in_executor(
                None,  # ThreadPoolExecutor 사용
                self._run_pathfinding_sync
            )
            
            elapsed_time = time.time() - start_time
            
            if routes:
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
                
                return routes, map_file
            else:
                logger.error("❌ 경로 최적화 실패 - 빈 결과")
                return {}, ""
                
        except Exception as e:
            logger.error(f"❌ 경로 최적화 중 오류 발생: {e}")
            return {}, ""
    
    def _run_pathfinding_sync(self) -> Tuple[Dict[int, List], str]:
        """
        동기식 경로 최적화 실행 (스레드 풀에서 실행)
        """
        try:
            routes, map_file = run_clustered_vrp(
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
            return routes, map_file
            
        except Exception as e:
            logger.error(f"동기식 경로 최적화 실행 오류: {e}")
            return {}, ""
    
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
