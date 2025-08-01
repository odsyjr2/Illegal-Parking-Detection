package com.aivle.ParkingDetection.dto;

import lombok.*;
import java.time.LocalDate;


@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CctvUpdateRequestDTO {
    private String location;
    private String ipAddress;
    private boolean active;
    private String description;
    private Double latitude;
    private Double longitude;
    private LocalDate installationDate; // 설치일 수정용 추가
}
