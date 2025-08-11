package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.ParkingZone;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ParkingZoneRepository extends JpaRepository<ParkingZone, Long> {
    // boolean existsByZoneName(String zoneName);
    Optional<ParkingZone> findByZoneName(String zoneName);
}
