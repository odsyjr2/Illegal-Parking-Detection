package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.HumanDetectionReport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface HumanDetectionReportRepository extends JpaRepository<HumanDetectionReport, Long> {
    List<HumanDetectionReport> findByUserID(String userID);
}
