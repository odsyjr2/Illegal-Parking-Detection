package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDate;


@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CctvCreateRequestDTO {
    private String location;
    private String ipAddress;
    private boolean active;
    private String description;
    private Double latitude;
    private Double longitude;
    private LocalDate installationDate;  // 설치일 등록용 추가  
    private String streamUrl;   // 프론트에서 보내는 URL
    private String streamName;  // 선택적으로 추가  
}