package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.ParkingZone;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ParkingZoneRepository extends JpaRepository<ParkingZone, Long> {
    // zoneName이 같은 레코드가 여러 개여도 항상 같은 ZONE을 고르기 위해 가장 작은 id를 선택
    Optional<ParkingZone> findTopByZoneNameOrderByIdAsc(String zoneName);

    Optional<ParkingZone> findByZoneName(String zoneName);

    @Override
    @EntityGraph(attributePaths = "sections")
    List<ParkingZone> findAll();

    @Override
    @EntityGraph(attributePaths = "sections")
    Optional<ParkingZone> findById(Long id);
}
