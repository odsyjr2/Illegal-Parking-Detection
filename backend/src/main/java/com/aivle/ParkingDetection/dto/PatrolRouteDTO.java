package com.aivle.ParkingDetection.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PatrolRouteDTO {
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RoutePoint {
        private String 장소;  // "출발지점", "순찰지점 1", "복귀지점"
        private Double 위도;
        private Double 경도;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class VehicleRoute {
        private Integer vehicleId;
        private List<RoutePoint> route;
        private Integer totalPoints;
    }
    
    private Map<String, List<RoutePoint>> routes;  // "vehicle_1": [...], "vehicle_2": [...]
    private LocalDateTime updatedAt;
    private Integer totalVehicles;
    private String status;
}
