package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.ParkingSection;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ParkingSectionRepository extends JpaRepository<ParkingSection, Long> {
}
