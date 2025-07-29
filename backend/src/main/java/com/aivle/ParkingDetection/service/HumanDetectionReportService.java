package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.HumanDetectionReport;
import com.aivle.ParkingDetection.repository.HumanDetectionReportRepository;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Optional;

@Service
public class HumanDetectionReportService {

    private final HumanDetectionReportRepository repository;

    public HumanDetectionReportService(HumanDetectionReportRepository repository) {
        this.repository = repository;
    }

    // 신고 등록
    public HumanDetectionReport createReport(HumanDetectionReport report) {
        report.setStatus("접수"); // 초기 상태 설정
        return repository.save(report);
    }

    // 회원별 신고 조회
    public List<HumanDetectionReport> getReportsByUser(String userID) {
        return repository.findByUserID(userID);
    }

    // 전체 신고 목록 조회
    public List<HumanDetectionReport> getAllReports() {
        return repository.findAll();
    }

    // 신고 상태 업데이트
    public boolean updateStatus(Long id, String newStatus) {
        Optional<HumanDetectionReport> optionalReport = repository.findById(id);
        if (optionalReport.isPresent()) {
            HumanDetectionReport report = optionalReport.get();
            report.setStatus(newStatus);
            repository.save(report);
            return true;
        }
        return false;
    }
}
