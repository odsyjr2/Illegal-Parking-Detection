package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Cctv {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String location;         // 위치 (주소/위치명)
    
    // Legacy fields (commented out for backward compatibility, but keeping for existing data)
    // private String ipAddress;        // CCTV IP 주소 - legacy
    // private String description;      // 설명 - legacy
    
    // Stream-related fields (extending for Korean ITS API integration)
    private String streamUrl;        // Korean ITS stream URL for live streaming
    private String streamId;         // Stream identifier (its_cctv_001, its_cctv_002, etc.)
    private String streamName;       // Human-readable stream name from Korean ITS API
    private String streamSource;     // Source type ("korean_its_api", "manual", etc.)
    
    private boolean active;          // 작동 여부
    private Double latitude;         // 위도
    private Double longitude;        // 경도

    private LocalDate installationDate;    // 설치일 (legacy - for manual CCTVs)
    private LocalDateTime lastUpdated;     // 마지막 업데이트 시간 (for Korean ITS streams)
    
    // Compatibility fields to maintain existing functionality
    @Transient
    public String getIpAddress() {
        return this.streamUrl;  // For backward compatibility
    }
    
    @Transient 
    public void setIpAddress(String ipAddress) {
        this.streamUrl = ipAddress;  // For backward compatibility
    }
    
    @Transient
    public String getDescription() {
        return this.streamName != null ? this.streamName : this.streamId;  // For backward compatibility
    }
    
    @Transient
    public void setDescription(String description) {
        if (this.streamName == null) {
            this.streamName = description;  // For backward compatibility
        }
    }
}
