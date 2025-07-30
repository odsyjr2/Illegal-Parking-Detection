package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.Cctv;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CctvRepository extends JpaRepository<Cctv, Long> {
}
