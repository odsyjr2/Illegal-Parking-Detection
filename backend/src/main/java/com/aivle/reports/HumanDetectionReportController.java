package com.aivle.reports;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@CrossOrigin(origins = "http://localhost:5173")
@RestController
@RequestMapping("/api/human-reports")
public class HumanDetectionReportController {

    private final HumanDetectionReportService service;

    public HumanDetectionReportController(HumanDetectionReportService service) {
        this.service = service;
    }

    // 신고 등록
    @PostMapping
    public ResponseEntity<HumanDetectionReport> createReport(@RequestBody HumanDetectionReport report) {
        HumanDetectionReport savedReport = service.createReport(report);
        return ResponseEntity.ok(savedReport);
    }

    // 회원별 신고 목록 조회
    @GetMapping("/user/{userID}")
    public ResponseEntity<List<HumanDetectionReport>> getReportsByUser(@PathVariable String userID) {
        List<HumanDetectionReport> reports = service.getReportsByUser(userID);
        return ResponseEntity.ok(reports);
    }

    // 전체 신고 목록 조회
    @GetMapping
    public ResponseEntity<List<HumanDetectionReport>> getAllReports() {
        List<HumanDetectionReport> reports = service.getAllReports();
        return ResponseEntity.ok(reports);
    }

    // 신고 상태 변경
    @PatchMapping("/{id}/status")
    public ResponseEntity<?> updateStatus(@PathVariable Long id, @RequestBody Map<String, String> statusMap) {
        String newStatus = statusMap.get("status");
        boolean updated = service.updateStatus(id, newStatus);

        if (updated) {
            return ResponseEntity.ok().build();
        } else {
            return ResponseEntity.notFound().build();
        }
    }
}
