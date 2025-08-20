package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.ParkingSection;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ParkingSectionRepository extends JpaRepository<ParkingSection, Long> {
    
    /**
     * 주소 기반 주차구역 검색 (출발지 또는 도착지에 포함된 주소로 검색)
     */
    @Query("SELECT ps FROM ParkingSection ps WHERE ps.origin LIKE %:address% OR ps.destination LIKE %:address%")
    List<ParkingSection> findByOriginContainingOrDestinationContaining(@Param("address") String origin, 
                                                                       @Param("address") String destination);
    
    /**
     * GPS 좌표 기반 주차구역 검색 (GPS 좌표가 설정된 구간만)
     */
    @Query("SELECT ps FROM ParkingSection ps WHERE ps.originLatitude IS NOT NULL AND ps.originLongitude IS NOT NULL " +
           "AND ps.destinationLatitude IS NOT NULL AND ps.destinationLongitude IS NOT NULL")
    List<ParkingSection> findAllWithGpsCoordinates();
}
