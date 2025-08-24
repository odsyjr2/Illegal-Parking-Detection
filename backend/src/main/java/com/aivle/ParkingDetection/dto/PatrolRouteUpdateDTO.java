package com.aivle.ParkingDetection.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PatrolRouteUpdateDTO {
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RoutePoint {
        private String 장소;  // "출발지점", "순찰지점 1", "복귀지점"
        private Double 위도;
        private Double 경도;
    }
    
    // AI에서 전송하는 데이터 형식: {"vehicle_1": [...], "vehicle_2": [...]}
    private Map<String, List<RoutePoint>> routes;
}
