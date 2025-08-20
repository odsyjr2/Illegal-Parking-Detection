package com.aivle.ParkingDetection.domain;
import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalTime;

@Entity
@Data
@Table(name = "parking_section")
public class ParkingSection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "zone_id", nullable = false)
    private ParkingZone zone;

    // 도로명 주소 필드
    @Column(name = "origin", nullable = false, length = 100)
    private String origin;

    @Column(name = "destination", nullable = false, length = 100)
    private String destination;

    // GPS 좌표 필드 - 하이브리드 매칭을 위한 추가
    @Column(name = "origin_latitude")
    private Double originLatitude;

    @Column(name = "origin_longitude")
    private Double originLongitude;

    @Column(name = "destination_latitude")
    private Double destinationLatitude;

    @Column(name = "destination_longitude")
    private Double destinationLongitude;

    // 시간 제한 필드
    @Column(name = "time_start", nullable = false)
    private LocalTime timeStart;

    @Column(name = "time_end", nullable = false)
    private LocalTime timeEnd;

    @Column(name = "parking_allowed", nullable = false)
    private boolean parkingAllowed;
    
    /**
     * 출발지 GPS 좌표가 설정되어 있는지 확인
     * 
     * @return GPS 좌표 존재 여부
     */
    public boolean hasOriginCoordinates() {
        return originLatitude != null && originLongitude != null;
    }
    
    /**
     * 도착지 GPS 좌표가 설정되어 있는지 확인
     * 
     * @return GPS 좌표 존재 여부
     */
    public boolean hasDestinationCoordinates() {
        return destinationLatitude != null && destinationLongitude != null;
    }
    
    /**
     * 모든 GPS 좌표가 설정되어 있는지 확인
     * 
     * @return 모든 좌표 존재 여부
     */
    public boolean hasAllCoordinates() {
        return hasOriginCoordinates() && hasDestinationCoordinates();
    }
    
    /**
     * 주어진 GPS 좌표가 이 구간에 포함되는지 확인 (단순한 거리 기반)
     * 
     * @param latitude 확인할 위도
     * @param longitude 확인할 경도
     * @param radiusMeters 허용 반경 (미터)
     * @return 구간 포함 여부
     */
    public boolean containsLocation(double latitude, double longitude, double radiusMeters) {
        if (!hasAllCoordinates()) {
            return false;
        }
        
        // 출발지 또는 도착지와의 거리 확인
        double distanceToOrigin = calculateDistance(latitude, longitude, originLatitude, originLongitude);
        double distanceToDestination = calculateDistance(latitude, longitude, destinationLatitude, destinationLongitude);
        
        return distanceToOrigin <= radiusMeters || distanceToDestination <= radiusMeters;
    }
    
    /**
     * 두 GPS 좌표 간의 거리를 계산 (Haversine formula)
     * 
     * @param lat1 첫 번째 위도
     * @param lon1 첫 번째 경도
     * @param lat2 두 번째 위도
     * @param lon2 두 번째 경도
     * @return 거리 (미터)
     */
    private double calculateDistance(double lat1, double lon1, double lat2, double lon2) {
        final double R = 6371000; // 지구의 반지름 (미터)
        
        double latDistance = Math.toRadians(lat2 - lat1);
        double lonDistance = Math.toRadians(lon2 - lon1);
        
        double a = Math.sin(latDistance / 2) * Math.sin(latDistance / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(lonDistance / 2) * Math.sin(lonDistance / 2);
        
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        
        return R * c; // 거리 (미터)
    }
}