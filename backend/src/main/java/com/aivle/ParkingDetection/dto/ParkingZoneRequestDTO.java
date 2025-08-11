package com.aivle.ParkingDetection.dto;

import java.time.LocalTime;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL) // ✅ 안 온 필드는 역직렬화 대상에서 제외
public class ParkingZoneRequestDTO {
    private String zoneName;
    private String origin;
    private String destination;
    private Boolean parkingAllowed;
    private LocalTime allowedStart;
    private LocalTime allowedEnd;
}
