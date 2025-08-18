package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDateTime;

/**
 * DTO for syncing stream information from AI system to backend
 * Used when AI discovers streams from Korean ITS API and sends them to backend
 */
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StreamSyncDto {
    private String streamId;         // Stream identifier (its_cctv_001, its_cctv_002, etc.)
    private String streamName;       // Human-readable stream name from Korean ITS API
    private String streamUrl;        // Direct Korean ITS stream URL for frontend streaming
    private String location;         // Location address/description
    private Double latitude;         // GPS latitude coordinate
    private Double longitude;        // GPS longitude coordinate
    private String streamSource;     // Source type ("korean_its_api")
    private boolean active;          // Stream availability status
    private LocalDateTime discoveredAt; // When stream was discovered by AI
}