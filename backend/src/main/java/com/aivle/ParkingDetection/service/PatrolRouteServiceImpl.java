package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.PatrolRouteDTO;
import com.aivle.ParkingDetection.dto.PatrolRouteUpdateDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import java.util.List;

@Slf4j
@Service
public class PatrolRouteServiceImpl implements PatrolRouteService {

    // 메모리에 최신 순찰 경로 저장 (나중에 Redis나 DB로 변경 가능)
    private volatile PatrolRouteDTO currentRoutes = null;
    private final Object routesLock = new Object();

    @Override
    public boolean updatePatrolRoutes(PatrolRouteUpdateDTO updateDTO) {
        try {
            synchronized (routesLock) {
                if (updateDTO == null || updateDTO.getRoutes() == null || updateDTO.getRoutes().isEmpty()) {
                    log.warn("경로 업데이트 요청이 비어있습니다");
                    return false;
                }
                
                // DTO 변환 (타입 안전성을 위해 명시적 캐스팅)
                PatrolRouteDTO routeDTO = new PatrolRouteDTO();
                @SuppressWarnings("unchecked")
                Map<String, java.util.List<PatrolRouteDTO.RoutePoint>> convertedRoutes = 
                    (Map<String, java.util.List<PatrolRouteDTO.RoutePoint>>) (Map<?, ?>) updateDTO.getRoutes();
                routeDTO.setRoutes(convertedRoutes);
                routeDTO.setUpdatedAt(LocalDateTime.now());
                routeDTO.setTotalVehicles(updateDTO.getRoutes().size());
                routeDTO.setStatus("ACTIVE");
                
                // 메모리에 저장
                this.currentRoutes = routeDTO;
                
                int totalPoints = updateDTO.getRoutes().values().stream()
                    .mapToInt(java.util.List::size).sum();
                
                log.info("✅ 순찰 경로 업데이트 완료 - {} 대 차량, {} 개 경로", 
                        routeDTO.getTotalVehicles(), totalPoints);
                
                return true;
            }
        } catch (Exception e) {
            log.error("순찰 경로 업데이트 중 오류 발생", e);
            return false;
        }
    }

    @Override
    public PatrolRouteDTO getCurrentPatrolRoutes() {
        synchronized (routesLock) {
            if (currentRoutes == null) {
                log.info("저장된 순찰 경로가 없습니다");
                
                // 빈 데이터 반환
                PatrolRouteDTO emptyDTO = new PatrolRouteDTO();
                emptyDTO.setRoutes(new ConcurrentHashMap<>());
                emptyDTO.setUpdatedAt(null);
                emptyDTO.setTotalVehicles(0);
                emptyDTO.setStatus("NO_DATA");
                
                return emptyDTO;
            }
            
            log.info("📋 순찰 경로 조회 - {} 대 차량 (업데이트: {})", 
                    currentRoutes.getTotalVehicles(), 
                    currentRoutes.getUpdatedAt());
            
            return currentRoutes;
        }
    }

    @Override
    public void clearPatrolRoutes() {
        synchronized (routesLock) {
            this.currentRoutes = null;
            log.info("🗑️ 순찰 경로 데이터 초기화 완료");
        }
    }
}
