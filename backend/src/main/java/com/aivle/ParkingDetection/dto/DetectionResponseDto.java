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
    private boolean illegal;  // 필드명 변경
    
    // AI INTEGRATION - NEW FIELDS
    private String plateNumber;        // OCR license plate result
    private String reportType;         // Event type from AI processor
    private String cctvId;            // AI processor stream identifier
    private Double latitude;          // GPS coordinates
    private Double longitude;         // GPS coordinates
    private String correlationId;     // AI processor correlation tracking
    private Double violationSeverity; // AI confidence score
}
