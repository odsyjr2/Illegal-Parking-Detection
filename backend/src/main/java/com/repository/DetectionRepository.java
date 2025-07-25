package com.aivle.parkingdetection.repository;

import com.aivle.parkingdetection.entity.Detection;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface DetectionRepository extends JpaRepository<Detection, Long> {
    List<Detection> findByDetectedAtBetween(LocalDateTime from, LocalDateTime to);
}
