#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from pathfinding_service import initialize_pathfinding_service

async def test_backend_integration():
    pathfinding_config = {
        'place_name': 'Seocho-gu, Seoul, South Korea',
        'violation_data_path': '../Data/CCTV기반단속개별건수.csv',
        'start_latitude': 37.4835,
        'start_longitude': 127.0322,
        'num_vehicles': 3,
        'coverage_ratio': 0.7,
        'min_nodes': 30,
        'penalty_factor': 5.0,
        'min_spacing': 500.0,
        'time_limit': 60,
        'update_interval_minutes': 1,
    }
    
    print('🚀 PathFinding 서비스 초기화...')
    service = initialize_pathfinding_service(**pathfinding_config)
    
    print('🗺️ 경로 최적화 실행 중...')
    routes, map_file = await service.generate_patrol_routes()
    
    if routes:
        print(f'✅ 성공! {len(routes)}대 차량 경로 생성 완료')
        for vid, route in routes.items():
            print(f'  차량 {vid+1}: {len(route)}개 지점')
        print(f'📍 지도 파일: {map_file}')
    else:
        print('❌ 경로 생성 실패')

if __name__ == "__main__":
    asyncio.run(test_backend_integration())
