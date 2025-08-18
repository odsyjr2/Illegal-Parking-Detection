package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;


@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CctvDTO {
    private Long id;
    private String location;
    
    // Legacy fields (for backward compatibility)
    private String ipAddress;
    private String description;
    
    // Stream-related fields (for Korean ITS API integration)
    private String streamUrl;        // Korean ITS stream URL for frontend streaming
    private String streamId;         // Stream identifier (its_cctv_001, etc.)
    private String streamName;       // Human-readable stream name
    private String streamSource;     // Source type ("korean_its_api", "manual")
    
    private boolean active;
    private Double latitude;
    private Double longitude; 
    
    private LocalDate installationDate;    // 설치일 (legacy - for manual CCTVs)
    private LocalDateTime lastUpdated;     // 마지막 업데이트 시간 (for Korean ITS streams)
}
