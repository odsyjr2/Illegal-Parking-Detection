package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Detection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ORIGINAL FIELDS - PRESERVED FOR BACKWARD COMPATIBILITY
    private String imageUrl;
    private String location;
    private LocalDateTime detectedAt;
    private String vehicleType;
    // isIllegal 필드 제거: Detection 테이블에 저장되는 모든 레코드는 불법주정차 확정 사항
    
    // AI INTEGRATION - NEW FIELDS
    private String plateNumber;        // OCR license plate result from AI processor
    private String reportType;         // Event type: "violation_detected", "monitoring", etc.
    private String cctvId;            // AI processor stream identifier
    private Double latitude;          // GPS coordinates from AI processor
    private Double longitude;         // GPS coordinates from AI processor
    private String correlationId;     // AI processor event correlation tracking
    private Double violationSeverity; // AI confidence score (0.0-1.0)
    
    // Phase 2: AI 역지오코딩 연동 - 주소 정보 추가
    @Column(length = 1000)
    private String address;           // 원본 주소 (geopy에서 반환된 전체 주소)
    
    @Column(length = 500)
    private String formattedAddress;  // 한국어 형식으로 포맷된 주소
}
