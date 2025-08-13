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
    private boolean isIllegal;
    
    // AI INTEGRATION - NEW FIELDS
    private String plateNumber;        // OCR license plate result from AI processor
    private String reportType;         // Event type: "violation_detected", "monitoring", etc.
    private String cctvId;            // AI processor stream identifier
    private Double latitude;          // GPS coordinates from AI processor
    private Double longitude;         // GPS coordinates from AI processor
    private String correlationId;     // AI processor event correlation tracking
    private Double violationSeverity; // AI confidence score (0.0-1.0)
}
