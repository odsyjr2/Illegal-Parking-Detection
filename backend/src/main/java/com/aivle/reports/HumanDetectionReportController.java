package com.aivle.reports;

import org.springframework.http.MediaType;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.io.IOException;



@RestController
@RequestMapping("/api/human-reports")
@CrossOrigin(origins = "*") // 또는 필요한 도메인 지정
public class HumanDetectionReportController {

    private final HumanDetectionReportService service;

    public HumanDetectionReportController(HumanDetectionReportService service) {
        this.service = service;
    }

    // 신고 등록
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<HumanDetectionReport> createReport(
            @RequestParam("file") MultipartFile file,
            @RequestParam("userID") String userID,
            @RequestParam("title") String title,
            @RequestParam("reason") String reason,
            @RequestParam("latitude") Double latitude,
            @RequestParam("longitude") Double longitude,
            @RequestParam("location") String location,
            @RequestParam("region") String region,
            @RequestParam("status") String status
    ) {
        String imagePath = "/uploads/" + file.getOriginalFilename();
        // 파일 저장 로직
        Path path = Paths.get("uploads", file.getOriginalFilename());
        try {
            Files.createDirectories(path.getParent());
            Files.write(path, file.getBytes());
        } catch (IOException e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().build();
        }

        HumanDetectionReport report = new HumanDetectionReport();
        report.setUserID(userID);
        report.setTitle(title);
        report.setReason(reason);
        report.setLatitude(latitude);
        report.setLongitude(longitude);
        report.setLocation(location);
        report.setRegion(region);
        report.setStatus(status);
        report.setImageURL(imagePath);

        HumanDetectionReport saved = service.createReport(report);
        return ResponseEntity.ok(saved);
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
