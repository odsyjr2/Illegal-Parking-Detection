package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.PatrolRouteDTO;
import com.aivle.ParkingDetection.dto.PatrolRouteUpdateDTO;

public interface PatrolRouteService {
    
    /**
     * AI에서 계산된 순찰 경로 업데이트
     * @param updateDTO 경로 업데이트 데이터
     * @return 성공 여부
     */
    boolean updatePatrolRoutes(PatrolRouteUpdateDTO updateDTO);
    
    /**
     * 현재 순찰 경로 조회 (프론트엔드용)
     * @return 현재 순찰 경로 데이터
     */
    PatrolRouteDTO getCurrentPatrolRoutes();
    
    /**
     * 순찰 경로 초기화
     */
    void clearPatrolRoutes();
}
