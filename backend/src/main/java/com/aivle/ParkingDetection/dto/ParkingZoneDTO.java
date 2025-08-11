package com.aivle.ParkingDetection.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.*;

import java.time.LocalTime;

@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class ParkingZoneDTO {
    private Long id;
    private String zoneName;
    private String origin;
    private String destination;
    private Boolean parkingAllowed;

    @JsonFormat(pattern = "HH:mm")
    private LocalTime allowedStart;

    @JsonFormat(pattern = "HH:mm")
    private LocalTime allowedEnd;
}
