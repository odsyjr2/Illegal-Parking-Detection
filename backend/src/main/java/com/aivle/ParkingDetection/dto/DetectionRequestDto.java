package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDateTime;

@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DetectionRequestDto {
    private String imageUrl;
    private String location;
    private LocalDateTime detectedAt;
    private String vehicleType;
    private boolean illegal;  // 필드명 변경
}
