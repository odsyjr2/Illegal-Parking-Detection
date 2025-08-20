package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDateTime;

@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DetectionResponseDto {
    // ORIGINAL FIELDS - PRESERVED FOR BACKWARD COMPATIBILITY
    private Long id;
    private String imageUrl;
    private String location;
    private LocalDateTime detectedAt;
    private String vehicleType;
    // illegal 필드 제거: 모든 Detection 레코드는 불법주정차 확정
    
    // AI INTEGRATION - NEW FIELDS
    private String plateNumber;        // OCR license plate result
    private String reportType;         // Event type from AI processor
    private String cctvId;            // AI processor stream identifier
    private Double latitude;          // GPS coordinates
    private Double longitude;         // GPS coordinates
    private String correlationId;     // AI processor correlation tracking
    private Double violationSeverity; // AI confidence score
    
    // Phase 2: AI 역지오코딩 연동 - 주소 정보 추가
    private String address;           // 원본 주소 (geopy에서 반환된 전체 주소)
    private String formattedAddress;  // 한국어 형식으로 포맷된 주소
}
