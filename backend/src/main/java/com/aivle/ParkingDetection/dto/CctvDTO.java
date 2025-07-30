package com.aivle.ParkingDetection.dto;

import lombok.*;

@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CctvDTO {
    private Long id;
    private String location;
    private String ipAddress;
    private boolean active;
    private String description;
    private Double latitude;
    private Double longitude;
}
